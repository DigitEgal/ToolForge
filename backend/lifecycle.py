"""Reviewable cleanup of recorded project-local dependencies; shared/global packages retained."""
import json
import os
from pathlib import Path
import shutil
import threading
import time
from toolforge_pilot.core import contained, data_root, atomic_json, run_process, project_path
from toolforge_pilot.installations import validate_requirement, prepare_check


def preview(project, projects):
    folder = Path(project['folder_path']).resolve() if project.get('folder_path') else None
    shared = []
    if folder:
        for row in projects:
            if row['id']==project['id'] or not row.get('folder_path'): continue
            other=Path(row['folder_path']).resolve()
            settings=other/'.toolforge/settings.json'
            try: interpreter=Path(json.loads(settings.read_text()).get('python','')).resolve()
            except (OSError,ValueError): interpreter=None
            if other.is_relative_to(folder) or folder.is_relative_to(other) or (interpreter and interpreter.is_relative_to(folder)):
                shared.append(row['name'])
    records=[]
    if folder:
        file=contained(folder,'.toolforge/installations.json')
        if file.exists(): records=json.loads(file.read_text(encoding='utf-8'))
    items=[];seen=set()
    for record in records:
        if not record.get('success') or record.get('action')=='uninstall': continue
        try: item=validate_requirement(record)
        except ValueError: continue
        token=(item['manager'],item['name'])
        if token in seen:continue
        seen.add(token)
        reason=''; global_candidate=False
        if shared:reason='Arbeitsordner oder Umgebung wird auch von anderen Projekten verwendet: '+', '.join(shared)
        elif item['manager']=='choco':
            references=[]
            for other_project in projects:
                if other_project['id']==project['id'] or not other_project.get('folder_path'):continue
                other=Path(other_project['folder_path'])/'.toolforge'
                try:
                    other_records=json.loads((other/'installations.json').read_text()) if (other/'installations.json').exists() else []
                    plan=json.loads((other/'active-plan.json').read_text()) if (other/'active-plan.json').exists() else {}
                except (OSError,ValueError):
                    references.append(other_project['name']+' (Bestand nicht lesbar)');continue
                required=[r for task in plan.get('tasks',[]) for r in task.get('requirements',[])]
                if any(r.get('manager')=='choco' and r.get('name','').lower()==item['name'].lower() for r in other_records+required):references.append(other_project['name'])
            global_candidate=not references
            reason=('Von anderen Projekten benötigt: '+', '.join(references)) if references else 'Globales Paket: Deinstallation nur mit zusätzlicher Bestätigung zur externen Nutzung.'
        elif item['manager']=='pip':
            python=folder/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            if not (folder/'.venv').resolve().is_relative_to(folder):reason='Python-Umgebung verweist nach außerhalb des Projekts; bleibt erhalten.'
            elif not python.is_file():reason='Projektumgebung fehlt; keine globale Deinstallation.'
            elif Path(record.get('environment','')).absolute()!=python.absolute():reason='Installation ist dieser Projektumgebung nicht eindeutig zugeordnet.'
        elif item['manager'] in ('npm','npx'):
            if not (folder/'package.json').is_file():reason='Keine lokale package.json; keine Bereinigung über übergeordnete npm-Projekte.'
            elif not (folder/'node_modules').resolve().is_relative_to(folder):reason='node_modules verweist nach außerhalb des Projekts; bleibt erhalten.'
        items.append({**item,'eligible':not reason,'reason':reason,'global_candidate':global_candidate})
    return {'project':project['name'],'folder':str(folder) if folder else None,'shared_with':shared,'packages':items,
            'folder_removal_allowed':bool(folder and folder.is_dir() and not shared and folder != Path.home() and folder.parent != folder)}


def remove(project, projects, cleanup=False, remove_folder=False, include_global=False):
    report=preview(project,projects)
    folder=Path(report['folder']) if report['folder'] else None
    if remove_folder and not report['folder_removal_allowed']:raise ValueError('Arbeitsordner ist geteilt oder geschützt und darf nicht entfernt werden.')
    results=[]
    if cleanup and folder:
        for item in report['packages']:
            if not item['eligible'] and not (include_global and item.get('global_candidate')):
                results.append({**item,'status':'retained'});continue
            manager=item['manager'];name=item['name']
            if manager=='pip':
                python=folder/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
                argv=[str(python),'-m','pip','uninstall','--yes',name]
            elif manager=='choco':
                choco=shutil.which('choco')
                if not choco:raise ValueError('Chocolatey nicht gefunden; Projekt bleibt erhalten.')
                argv=[choco,'uninstall',name,'--yes','--no-progress']
            else:
                npm=shutil.which('npm')
                if not npm:raise ValueError('npm fehlt; Projekt wurde nicht gelöscht.')
                argv=prepare_check([npm,'uninstall','--prefix',str(folder),'--no-audit','--no-fund','--ignore-scripts',name])
            result=run_process(argv,folder,180,threading.Event())
            row={**item,'status':'removed' if result['code']==0 and not result['reason'] else 'failed','output':result['output'][-3000:]}
            results.append(row)
            audit=folder/'.toolforge/uninstallations.json'
            existing=json.loads(audit.read_text()) if audit.exists() else []
            atomic_json(audit,existing+[row])
            if row['status']=='failed':raise ValueError('Paketbereinigung fehlgeschlagen: '+name+'. Projekt bleibt erhalten; Details im Deinstallationsjournal.')
    report['results']=results
    if results and folder:
        readme=contained(folder,'README.md')
        text=readme.read_text(encoding='utf-8') if readme.exists() else '# Projekt\n'
        text+='\n## Paketbereinigung durch ToolForge\n\n'+'\n'.join('- '+r['manager']+': '+r['name']+' — '+r['status'] for r in results)+'\n'
        readme.write_text(text,encoding='utf-8')
    if folder and folder.exists():
        atomic_json(folder/'.toolforge/deletion-report.json',report)
    if remove_folder and folder:
        project_path(folder)
        trash=data_root()/'trash';trash.mkdir(parents=True,exist_ok=True)
        destination=trash/(project['id']+'-'+str(time.time_ns()))
        shutil.move(str(folder),str(destination));report['recoverable_folder']=str(destination)
    audit=data_root()/'deletions';audit.mkdir(parents=True,exist_ok=True)
    atomic_json(audit/(project['id']+'.json'),report)
    return report
