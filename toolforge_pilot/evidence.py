"""Task-scoped validation evidence and dependent invalidation."""
import hashlib
from pathlib import Path
from .core import contained, fingerprint

def inputs(root, task, tasks):
    by_id={t['id']:t for t in tasks}; names=set(); visited=set()
    def visit(t):
        if t['id'] in visited:return
        visited.add(t['id']);names.update(t['files']);names.update(t.get('context_candidates',[]))
        for check in t['checks']:
            for arg in check['argv'][1:]:
                if '{' in arg or arg.startswith('-'):continue
                try:
                    p=contained(root,str(Path(check.get('cwd','.'))/arg))
                    if p.is_file():names.add(p.relative_to(root).as_posix())
                    elif p.is_dir() and p!=Path(root):
                        for child in p.rglob('*'):
                            if child.is_file() and not child.is_symlink() and not any(x.startswith('.') or x=='__pycache__' for x in child.relative_to(p).parts):names.add(child.relative_to(root).as_posix())
                except (ValueError,OSError):pass
        for dep in t['depends_on']:visit(by_id[dep])
    visit(task)
    for name in ('pyproject.toml','requirements.txt','requirements-dev.txt','package.json','package-lock.json','tsconfig.json','pytest.ini','conftest.py','setup.cfg'):
        if (Path(root)/name).is_file():names.add(name)
    hashes={}
    for name in sorted(names):
        path=contained(root,name);hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {'contract':{k:task.get(k,[]) for k in ('instruction','files','depends_on','checks','acceptance','requirements')},'files':hashes,'global':fingerprint(root) if not names else None}

def mark_verified(store,task):
    store.state['tasks'][task['id']].update(status='VERIFIED',ever_verified=True,evidence=inputs(store.project,task,store.state['plan']['tasks']),error='',question=None)

def invalidate(store,reason='Geänderte Eingaben'):
    s=store.state;changed=set()
    for task in s['plan']['tasks']:
        row=s['tasks'][task['id']]
        if row['status']=='VERIFIED' and row.get('evidence')!=inputs(store.project,task,s['plan']['tasks']):
            row.update(status='RECHECK',ever_verified=True,invalidation_reason=reason);changed.add(task['id'])
    more=True
    while more:
        more=False
        for task in s['plan']['tasks']:
            row=s['tasks'][task['id']]
            if row['status']=='VERIFIED' and changed.intersection(task['depends_on']):
                row.update(status='RECHECK',ever_verified=True,invalidation_reason='Abhängigkeit geändert');changed.add(task['id']);more=True
    if changed:store.event('invalidate',{'tasks':sorted(changed),'reason':reason})
    return changed
