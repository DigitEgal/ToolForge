"""Optional Docker boundary for project Python/check/workflow commands; never for the controller."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from toolforge_pilot.core import run_process,contained

def project_tag(root):return hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:12]
def validate(settings):
    network=settings.get('sandbox_network','')
    if not isinstance(network,str) or (network and not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,30}',network)):raise ValueError('Sandbox-Netzwerk: leer oder bis 31 Kleinbuchstaben/Ziffern/-/_.')

def command(root,argv,cwd,settings,name):
    validate(settings)
    docker=shutil.which('docker')
    if not docker:raise ValueError('Docker fehlt. Docker Desktop mit Linux-Containern starten oder Sandbox deaktivieren.')
    root=Path(root).resolve();cwd=Path(cwd).resolve()
    if not cwd.is_relative_to(root):raise ValueError('Sandbox-Arbeitsverzeichnis liegt außerhalb des Projekts.')
    mapped=[]
    for i,arg in enumerate(argv):
        if i==0 and ('python' in Path(arg).name.lower()):mapped.append('python');continue
        value=str(arg)
        if value==str(root) or value.startswith(str(root)+os.sep):value='/workspace'+value[len(str(root)):].replace('\\','/')
        if i==0 and (value.startswith('/') or ':/' in value):raise ValueError('Sandbox benötigt einen im Container installierten Befehl.')
        mapped.append(value)
    network='toolforge-'+settings['sandbox_network'] if settings.get('sandbox_network') else 'none'
    args=[docker,'run','--rm','--name',name,'--label','toolforge=true','--network',network,
          '--network-alias','tf-'+project_tag(root)] if network!='none' else [docker,'run','--rm','--name',name,'--label','toolforge=true','--network','none']
    args+=['--cap-drop','ALL','--security-opt','no-new-privileges','--memory','4g','--cpus','2','--pids-limit','256',
           '--read-only','--tmpfs','/tmp:rw,size=512m','-e','PYTHONDONTWRITEBYTECODE=1','-e','HOME=/tmp',
           '--mount','type=bind,source='+str(root)+',target=/workspace','-w','/workspace/'+cwd.relative_to(root).as_posix()]
    if os.name!='nt':args+=['--user',str(os.getuid())+':'+str(os.getgid())]
    return args+['toolforge-project:'+project_tag(root),*mapped]

def run(root,argv,cwd,timeout,stop,log,settings):
    if not settings.get('sandbox'):return run_process(argv,cwd,timeout,stop,log)
    name='toolforge-job-'+uuid.uuid4().hex
    args=command(root,argv,cwd,settings,name)
    log('Sandbox-Alias: tf-'+project_tag(root)+'; Netzwerk: '+(settings.get('sandbox_network') or 'keines')+'\n')
    try:return run_process(args,cwd,timeout,stop,log)
    finally:
        # Killing docker CLI alone does not guarantee that its container stops.
        subprocess.run([args[0],'rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)

def build(root,python,stop,log,settings):
    validate(settings);docker=shutil.which('docker')
    if not docker:raise ValueError('Docker ist nicht installiert.')
    folder=contained(root,'.toolforge/docker');folder.mkdir(parents=True,exist_ok=True)
    if not (folder/'Dockerfile').exists():(folder/'Dockerfile').write_text('FROM python:3.12-slim\nRUN pip install --no-cache-dir pytest ruff mypy\nWORKDIR /workspace\n',encoding='utf-8')
    result=run_process([docker,'build','-t','toolforge-project:'+project_tag(root),str(folder)],root,1200,stop,log)
    if result['code'] or result['reason']:return result
    if settings.get('sandbox_network'):
        network='toolforge-'+settings['sandbox_network']
        exists=subprocess.run([docker,'network','inspect',network],capture_output=True,timeout=20)
        if exists.returncode:
            result=run_process([docker,'network','create','--internal','--label','toolforge=true',network],root,30,stop,log)
    return result
