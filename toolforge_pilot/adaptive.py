"""Bounded streaming guard and adaptive task decomposition; no model-defined test gates."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from .core import contained, validate_plan
from .profiles import estimate, input_budget, ContextBudgetError


class OutputGuard:
    def __init__(self, output_tokens, allowed_files=None):
        self.limit = max(8192, int(output_tokens) * 8 + 4096)
        self.allowed = set(allowed_files) if allowed_files is not None else None
        self.text = ''; self.bytes = 0; self.reason = ''

    def __call__(self, chunk):
        if self.reason: return self.reason
        self.bytes += len(chunk.encode('utf-8'))
        self.text = (self.text + chunk)[-65536:]
        plain = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', self.text)
        lower = plain.lower()
        if any(x in lower for x in ('has hit a token limit', 'context_length_exceeded', 'maximum context length', 'exceeded the context window')):
            self.reason = 'GUARD_CONTEXT'
        else:
            # Only completed lines: arbitrary stream chunk boundaries must not create duplicates.
            lines = plain.split('\n')[:-1]
            filenames = [x.strip(' `\r') for x in lines if re.fullmatch(r'[ `]*[\w@./\\-]+\.(?:py|tsx?|jsx?|css|scss|json|md|html|ya?ml)[ `\r]*', x)]
            repeated = Counter(filenames)
            if any(n >= 3 for n in repeated.values()): self.reason = 'GUARD_REPEAT'
            # Repeated multi-line blocks catch loops without file headings, but not repeated braces.
            meaningful = [x.strip() for x in lines if len(x.strip()) >= 12]
            blocks = Counter('\n'.join(meaningful[i:i+8]) for i in range(max(0, len(meaningful)-7)))
            if any(n >= 3 for n in blocks.values()): self.reason = 'GUARD_REPEAT'
            if not self.reason and self.allowed is not None and any(f.replace('\\','/') not in self.allowed for f in filenames):
                self.reason = 'GUARD_SCOPE'
        if not self.reason and self.bytes > self.limit: self.reason = 'GUARD_OUTPUT'
        return self.reason


def file_steps(task):
    files = list(dict.fromkeys(task.get('context_candidates', []) + task['files']))
    return [{'file': f, 'instruction': 'Implementiere ausschließlich den Anteil in ' + f + '. ' + task['instruction'][:1200]} for f in files]


def request_steps(base, key, model, task, error, p):
    files = list(dict.fromkeys(task.get('context_candidates', []) + task['files']))
    if not files: raise ValueError('Keine deklarierten Dateien für die Teilplanung.')
    system = ('Zerlege genau eine blockierte Entwicklungsaufgabe in 2 bis 4 kleine sequenzielle Schritte. '
              'Jeder Schritt bearbeitet genau eine der erlaubten Dateien. Keine Wiederholung der Gesamtaufgabe. '
              'Bei nur einer Datei: getrennte kleine Verhaltensänderungen in dieser Datei. '
              'Keine Implementierung, keine Tests ändern, keine neuen Anforderungen. Nur JSON: '
              '{"steps":[{"file":"erlaubter Pfad","instruction":"konkrete kleine Änderung, höchstens 600 Zeichen"}]}.')
    task_data = {'task': task['instruction'][:2400], 'acceptance': task['acceptance'],
                 'allowed_files': files, 'failure': error[-800:]}
    user = json.dumps(task_data, ensure_ascii=False)
    if estimate(system+user) > input_budget(p): raise ContextBudgetError('Teilplanung überschreitet den geladenen Kontext.')
    payload = {'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],
               'temperature':min(p['temperature'],0.2),'max_tokens':min(p['output_tokens'],1200),'stream':False}
    req = urllib.request.Request(base.rstrip('/')+'/chat/completions', data=json.dumps(payload).encode(),
          headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    with urllib.request.urlopen(req,timeout=60) as response:
        raw=response.read(65537)
    if len(raw)>65536: raise ValueError('Teilplanantwort zu groß.')
    choice=json.loads(raw)['choices'][0]
    if choice.get('finish_reason')=='length': raise ValueError('Teilplanung abgeschnitten.')
    text=choice['message']['content'].strip()
    if text.startswith('```'): text=text.split('\n',1)[1].rsplit('```',1)[0]
    steps=json.loads(text)['steps']
    if not isinstance(steps,list) or not 2<=len(steps)<=4: raise ValueError('Teilplan benötigt 2 bis 4 Schritte.')
    seen=set()
    for step in steps:
        if not isinstance(step,dict) or step.get('file') not in files: raise ValueError('Teilplanung verlässt den Dateiumfang.')
        instruction=step.get('instruction')
        if not isinstance(instruction,str) or not 10<=len(instruction.strip())<=600: raise ValueError('Teilauftrag ist nicht kompakt.')
        token=(step['file'],instruction.strip())
        if token in seen: raise ValueError('Teilplanung wiederholt Schritte.')
        seen.add(token)
    return steps


def split_task(plan, task_id, steps, reason):
    """Keep original id and acceptance as integration gate; dependents remain valid."""
    result=copy.deepcopy(plan)
    index=next(i for i,t in enumerate(result['tasks']) if t['id']==task_id)
    parent=result['tasks'][index]
    root=parent.get('adaptive_root',parent['id'])
    history=result.setdefault('replanning',[])
    if sum(x['root']==root for x in history)>=2: raise ValueError('Zwei Neuplanungen dieses Auftrags ausgeschöpft.')
    if not steps or len(steps)>12: raise ValueError('Keine begrenzte Teilplanung möglich.')
    revision=result['version']+1; previous=list(parent['depends_on']); children=[]
    allowed=set(parent.get('context_candidates',[])+parent['files'])
    for i, step in enumerate(steps):
        name=step['file']
        if name not in allowed: raise ValueError('Unzulässige Datei in Teilplanung.')
        ident=parent['id'][:32]+f'_r{revision}_{i+1}'
        code='from pathlib import Path; import ast; p=Path('+repr(name)+'); assert p.is_file() and p.stat().st_size>0'
        if name.endswith('.py'): code+='; ast.parse(p.read_text(encoding="utf-8-sig"))'
        child={'id':ident,'title':f'Teilschritt {i+1}: {name}',
               'instruction':step['instruction'], 'files':[name], 'depends_on':previous,
               'acceptance':[f'{name} vorhanden und syntaktisch prüfbar; Gesamtfunktion wird anschließend separat geprüft.'],
               'checks':[{'argv':['{python}','-c',code],'cwd':'.','timeout':30}],
               'weight':parent.get('weight',1)*.1/len(steps),'estimate':[1,2],'max_repairs':2,
               'adaptive_root':root,'adaptive_part':True,'context_part':True,
               'requirements':copy.deepcopy(parent.get('requirements',[]))}
        children.append(child);previous=[ident]
    parent['depends_on']=previous
    parent['weight']=parent.get('weight',1)*.9
    parent['adaptive_root']=root;parent['context_gate']=True
    parent['context_candidates']=list(dict.fromkeys(parent.get('context_candidates',[])+parent['files']))
    parent['files']=[]
    # Intentionally do not mutate original instruction, checks or acceptance.
    result['tasks'][index:index]=children
    result['version']=revision
    history.append({'root':root,'task':task_id,'version':revision,'reason':reason,'children':[t['id'] for t in children]})
    return validate_plan(result)


def handoff(project, tasks, states):
    """Compact factual handoff: verified files and hashes, never repeated generated code."""
    result=[]
    for task in tasks:
        if states[task['id']]['status']!='VERIFIED': continue
        for name in task['files']:
            file=contained(project,name)
            if file.is_file():
                result.append({'task':task['id'],'file':name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()[:16]})
    return result[-6:]
