"""Project editor, explicit jobs, Git operations and workflow execution."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from toolforge_pilot.core import contained, safe_relative, atomic_json, run_process, SKIP_DIRS, valid_project_name
from toolforge_pilot.installations import InstallManager

class Workspace:
    def __init__(self, session):
        self.session=session; self.root=session.store.project
        self.job={'status':'idle','output':'','result':None}

    def path(self, name):
        relative=safe_relative(name)
        for part in relative.parts: valid_project_name(part)
        if any(part in SKIP_DIRS for part in relative.parts) or any(part.startswith(('.env','.aider')) for part in relative.parts):
            raise ValueError('Interne Umgebungen, Geheimnisse und Steuerdateien sind im Editor gesperrt.')
        path=contained(self.root,name)
        if path.exists() and not path.is_file():raise ValueError('Bitte eine Datei auswählen.')
        return path

    def tree(self):
        rows=[]
        for parent,dirs,files in os.walk(self.root):
            dirs[:]=sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(parent)/d).is_symlink())
            for name in sorted(files):
                file=Path(parent)/name
                if name.startswith(('.env','.aider')) or file.is_symlink():continue
                rows.append({'path':file.relative_to(self.root).as_posix(),'size':file.stat().st_size})
                if len(rows)>=2000:return {'files':rows,'truncated':True}
        return {'files':rows,'truncated':False}

    def read(self,name):
        path=self.path(name)
        if path.stat().st_size>1000000:raise ValueError('Editorlimit: 1 MB pro Datei.')
        raw=path.read_bytes()
        if b'\0' in raw:raise ValueError('Binärdatei kann nicht im Texteditor geöffnet werden.')
        try:text=raw.decode('utf-8')
        except UnicodeError:raise ValueError('Der Editor benötigt UTF-8. Datei zuerst konvertieren.')
        return {'path':name,'text':text,'revision':hashlib.sha256(raw).hexdigest()}

    def save(self,name,text,revision):
        if not isinstance(text,str) or len(text.encode('utf-8'))>1000000:raise ValueError('Ungültiger Text oder Editorlimit überschritten.')
        with self.session.guard:
            if self.session.busy:raise ValueError('Vor dem Speichern laufende Jobs pausieren oder stoppen.')
            path=self.path(name)
            old=path.read_bytes() if path.exists() else None
            current=hashlib.sha256(old).hexdigest() if old is not None else None
            if current!=revision:raise ValueError('Speicherkonflikt: Datei wurde inzwischen geändert. Neu laden und Änderungen vergleichen; nichts wurde überschrieben.')
            if old is not None:
                backup=self.session.store.log_root.parent/'editor-backups'/str(time.time_ns())/safe_relative(name)
                backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old)
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
            try:
                tmp.write_bytes(text.encode('utf-8'))
                if path.exists():shutil.copymode(path,tmp)
                os.replace(tmp,path)
            finally:tmp.unlink(missing_ok=True)
            self.session.scan=self.session.scan_project()
        return self.read(name)

    @property
    def python(self):
        env=self.root/'.venv'
        if not env.resolve().is_relative_to(self.root):raise ValueError('Projektumgebung zeigt nach außerhalb des Projekts.')
        candidate=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        return str(candidate) if candidate.exists() else self.session.settings['python']

    def state(self):
        return {**self.job,'busy':self.session.busy,'python':self.python,'environment_exists':(self.root/'.venv').is_dir()}

    def start(self,data):
        kind=data.get('kind');timeout=int(data.get('timeout',180))
        if not 5<=timeout<=3600:raise ValueError('Zeitlimit: 5 bis 3600 Sekunden.')
        args=data.get('args',[])
        if not isinstance(args,list) or not all(isinstance(x,str) for x in args):raise ValueError('Argumente müssen eine JSON-Liste von Strings sein.')
        if kind=='python':
            file=self.path(str(data.get('path','')))
            if file.suffix!='.py' or not file.is_file():raise ValueError('Vorhandene Python-Datei auswählen.')
            argv=[self.python,'-u',str(file),*args]
        elif kind in ('pytest','ruff','mypy'):
            argv={'pytest':[self.python,'-m','pytest','-q'], 'ruff':[self.python,'-m','ruff','check','.'], 'mypy':[self.python,'-m','mypy','.']}[kind]
        elif kind=='venv':
            if (self.root/'.venv').exists():raise ValueError('Die Projektumgebung existiert bereits.')
            argv=[self.session.settings['python'],'-m','venv',str(self.root/'.venv')]
        elif kind in ('install_checks','workflow','ai_prepare','acceptance','sandbox_build'):argv=None
        else:raise ValueError('Unbekannter Auftrag.')
        if kind=='workflow':
            from backend.workflows import validate_workflow
            workflow=validate_workflow(data.get('workflow'))
        def work():
            self.session.remaining_budget=0
            self.job={'status':'running','kind':kind,'output':'','result':None}
            folder=self.session.store.log_root/('workbench-'+uuid.uuid4().hex);folder.mkdir()
            def log(text):
                self.job['output']=(self.job['output']+text)[-100000:]
                with (folder/'output.log').open('a',encoding='utf-8') as f:f.write(text)
            try:
                if kind=='sandbox_build':
                    from backend.sandbox import build
                    result=build(self.root,self.python,self.session.cancel,log,self.session.settings)
                elif kind=='install_checks':
                    manager=InstallManager(self.root,self.session.settings['python'],{**self.session.settings,'allow_pip':True},self.session.cancel,log)
                    for package in ('pytest','ruff','mypy'):
                        if self.session.cancel.is_set():break
                        manager.install({'manager':'pip','name':package},force=True)
                    if self.session.store.state:
                        self.session.store.state['installations']=manager.records
                        self.session.store.save()
                    result={'code':0,'reason':'STOP' if self.session.cancel.is_set() else '','output':'Prüfwerkzeuge verarbeitet.'}
                elif kind=='acceptance':
                    from backend.workflows import acceptance
                    result=acceptance(self.root,self.python,self.session.cancel,log)
                elif kind=='ai_prepare':
                    result=self.prepare_ai(data,self.session.cancel)
                elif kind=='workflow':
                    from backend.workflows import execute
                    result=execute(self.root,workflow,self.python,self.session.cancel,log,self.session.settings)
                else:
                    from backend.sandbox import run as sandbox_run
                    result=sandbox_run(self.root,argv,self.root,timeout,self.session.cancel,log,self.session.settings) if kind!='venv' else run_process(argv,self.root,timeout,self.session.cancel,log)
                self.job.update(status='stopped' if result.get('reason')=='STOP' else 'done' if result['code']==0 and not result.get('reason') else 'failed',result=result)
                atomic_json(folder/'result.json',result)
                self.session.phase='Auftrag: '+self.job['status']
            except Exception as exc:
                if self.session.settings.get('debug_logging'):
                    import traceback
                    from toolforge_pilot.diagnostics import record
                    record(self.root,'workspace_exception',traceback.format_exc(),[self.session.api_key])
                log(str(exc));self.job.update(status='failed',result={'code':1,'reason':str(exc)})
                self.session.phase='Auftrag fehlgeschlagen: '+str(exc)
        self.session.background(work,model_lock=kind=='ai_prepare')
        return self.state()

    def git(self,args):
        binary=shutil.which('git')
        if not binary:raise ValueError('Git ist nicht installiert oder nicht in PATH.')
        result=subprocess.run([binary,'--no-pager','-C',str(self.root),*args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        if result.returncode:raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Git-Aufruf fehlgeschlagen.')
        return result.stdout

    def require_repo(self):
        if Path(self.git(['rev-parse','--show-toplevel']).strip()).resolve()!=self.root:raise ValueError('Das Git-Repository muss genau im ausgewählten Projektordner liegen.')

    def git_status(self):
        if not (self.root/'.git').exists():return {'initialized':False,'status':'','diff':'','history':''}
        self.require_repo()
        history=self.git(['log','-15','--date=iso','--format=%h | %ad | %s']) if self.git(['rev-list','--all','--count']).strip()!='0' else ''
        return {'initialized':True,'status':self.git(['status','--short']),'diff':self.git(['diff','HEAD']) if history else self.git(['diff','--cached']), 'history':history}

    def git_action(self,data):
        with self.session.guard:
            if self.session.busy:raise ValueError('Vor Git-Änderungen laufenden Auftrag beenden.')
            action=data.get('action')
            if action=='init':
                if (self.root/'.git').exists():raise ValueError('Repository existiert bereits.')
                self.git(['init'])
                ignore=self.root/'.gitignore'
                old=ignore.read_text(encoding='utf-8') if ignore.exists() else ''
                ignore.write_text(old+'\n.venv/\n.toolforge/\n.pilot/\n.env*\nnode_modules/\n__pycache__/\n',encoding='utf-8')
            elif action=='commit':
                self.require_repo()
                message=str(data.get('message','')).strip();files=data.get('files',[])
                if not message or len(message)>1000 or not isinstance(files,list) or not files:raise ValueError('Commit-Nachricht und explizite Dateiauswahl erforderlich.')
                for name in files:self.path(name)
                # Do not commit unrelated already-staged work; --only scopes the commit to selected paths.
                for key in ('name','email'):
                    value=str(data.get(key,''))
                    if value:self.git(['config','--local','user.'+key,value])
                self.git(['add','--',*files])
                self.git(['commit','--only','-m',message,'--',*files])
            else:raise ValueError('Unbekannte Git-Aktion.')
        return self.git_status()

    def workflows(self):
        path=self.session.store.log_root.parent/'workflow.json'
        from backend.workflows import example
        return json.loads(path.read_text()) if path.exists() else example()

    def save_workflow(self,data):
        from backend.workflows import validate_workflow
        value=validate_workflow(data)
        with self.session.guard:
            if self.session.busy:raise ValueError('Workflow erst nach laufendem Auftrag ändern.')
            atomic_json(self.session.store.log_root.parent/'workflow.json',value)
        return value

    def prepare_ai(self,data,stop):
        import ast
        import difflib
        import urllib.request
        from toolforge_pilot.profiles import profile,estimate,input_budget
        name=str(data.get('path',''));original=self.read(name)
        instruction=str(data.get('instruction','')).strip()
        if not instruction:raise ValueError('Bitte eine konkrete Änderung beschreiben.')
        settings=self.session.settings;p=profile(settings)
        if not settings['model']:raise ValueError('Zuerst unter Einstellungen ein Modell auswählen.')
        prompt='Bearbeite ausschließlich diese Datei gemäß Auftrag. Erhalte übriges Verhalten. Antworte nur als JSON mit text (vollständiger neuer Dateiinhalt) und summary.\nDatei: '+name+'\nAuftrag: '+instruction+'\nDateiinhalt:\n'+original['text']
        if estimate(prompt)>input_budget(p):raise ValueError('Datei und Auftrag überschreiten den Modellkontext. Auftrag/Datei eingrenzen.')
        payload={'model':settings['model'],'messages':[{'role':'user','content':prompt}],'temperature':p['temperature'],'max_tokens':p['output_tokens'],'stream':False}
        request=urllib.request.Request(settings['base'].rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.session.api_key})
        with urllib.request.urlopen(request,timeout=120) as response:raw=response.read(2000001)
        if len(raw)>2000000:raise ValueError('Modellantwort zu groß.')
        choice=json.loads(raw)['choices'][0]
        if choice.get('finish_reason')=='length':raise ValueError('Änderungsvorschlag abgeschnitten. Datei unverändert; Ausgabelimit oder Auftrag anpassen.')
        text=choice['message']['content'].strip()
        if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0]
        proposal=json.loads(text)
        if not isinstance(proposal,dict) or not isinstance(proposal.get('text'),str):raise ValueError('Modell lieferte keinen gültigen Änderungsvorschlag.')
        if len(proposal['text'].encode())>1000000:raise ValueError('Editorlimit überschritten.')
        if name.endswith('.py'):ast.parse(proposal['text'])
        if stop.is_set():return {'code':1,'reason':'STOP'}
        ident=uuid.uuid4().hex
        proposal={'id':ident,'path':name,'revision':original['revision'],'text':proposal['text'],'summary':str(proposal.get('summary',''))[:2000],
                  'diff':''.join(difflib.unified_diff(original['text'].splitlines(True),proposal['text'].splitlines(True),fromfile=name+' (vorher)',tofile=name+' (Vorschlag)'))}
        atomic_json(self.session.store.log_root.parent/'proposals'/(ident+'.json'),proposal)
        return {'code':0,'reason':'','proposal':proposal}

    def apply_ai(self,ident):
        import re
        if not re.fullmatch('[a-f0-9]{32}',ident):raise ValueError('Ungültiger Vorschlag.')
        path=self.session.store.log_root.parent/'proposals'/(ident+'.json')
        proposal=json.loads(path.read_text(encoding='utf-8'))
        saved=self.save(proposal['path'],proposal['text'],proposal['revision'])
        proposal['applied_revision']=saved['revision'];atomic_json(path,proposal)
        return saved
