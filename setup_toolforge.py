"""Repeatable setup: controller and Aider have separate dependency environments."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import venv
ROOT=Path(__file__).resolve().parent

def python_at(folder):return folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
def opencode_setup():
    """Optional free-model provider: install OpenCode via npm and start its local service."""
    status={'installed':False,'version':'','service':'not started','error':''}
    exe=shutil.which('opencode')
    npm=shutil.which('npm')
    if not exe and npm:
        print('OpenCode Free ist optional. Installiere @opencode/cli über npm …')
        try:
            result=subprocess.run([npm,'install','-g','@opencode/cli'],capture_output=True,text=True,
                                  encoding='utf-8',errors='replace',timeout=300)
            if result.returncode!=0:
                status['error']=str(result.stderr or result.stdout or 'npm-Installation fehlgeschlagen.').strip()[-800:]
            else:
                exe=shutil.which('opencode')
                if not exe:
                    prefix=subprocess.run([npm,'prefix','-g'],capture_output=True,text=True,
                                          encoding='utf-8',errors='replace',timeout=30)
                    if prefix.returncode==0:
                        candidate=Path(prefix.stdout.strip())/('opencode.cmd' if os.name=='nt' else 'bin/opencode')
                        if candidate.is_file():exe=str(candidate)
        except (OSError,subprocess.TimeoutExpired) as exc:
            status['error']='npm-Installation nicht möglich: '+str(exc)
    if not exe:
        if not npm and not status['error']:
            status['error']='Node.js/npm nicht gefunden. OpenCode Free bleibt optional; Anleitung: https://opencode.ai'
        print('OpenCode Free: '+ (status['error'] or 'nicht installiert (optional).'))
        return status
    status['installed']=True
    try:
        version=subprocess.run([exe,'--version'],capture_output=True,text=True,encoding='utf-8',
                               errors='replace',timeout=30)
        if version.returncode==0:status['version']=(version.stdout or '').strip()
    except (OSError,subprocess.TimeoutExpired):
        pass
    try:
        service=subprocess.run([exe,'service','start'],capture_output=True,text=True,encoding='utf-8',
                               errors='replace',timeout=90,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        status['service']='started' if service.returncode==0 else 'not started'
        if service.returncode!=0:
            status['error']=str(service.stderr or service.stdout or '').strip()[-800:]
    except (OSError,subprocess.TimeoutExpired) as exc:
        status['error']='Dienststart nicht bestätigt: '+str(exc)
    print('OpenCode Free: '+(('Version '+status['version']+' bereit; Dienst '+status['service'])
                              if status['installed'] else 'optional nicht verfügbar')+'.')
    return status
def main():
    if sys.version_info<(3,11):raise SystemExit('Python 3.11 oder neuer erforderlich.')
    env=ROOT/'.venv'
    if not python_at(env).exists():venv.EnvBuilder(with_pip=True).create(env)
    python=python_at(env)
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements.txt'),'uv'],check=True)
    aider=ROOT/'.aider-venv'
    if not python_at(aider).exists():
        subprocess.run([str(python),'-m','uv','venv','--python','3.12','--seed',str(aider)],check=True)
    subprocess.run([str(python),'-m','uv','pip','install','--python',str(python_at(aider)),'-r',str(ROOT/'requirements-aider.txt')],check=True)
    subprocess.run([str(python_at(aider)),'-m','aider','--version'],check=True)
    from toolforge_pilot.core import AiderAdapter
    AiderAdapter(str(python_at(aider)),'http://localhost:1234/v1','lm-studio','setup-probe').probe()
    provider=opencode_setup()
    (ROOT/'setup-runtime.json').write_text(json.dumps({'aider_python':str(python_at(aider)),'opencode':provider},indent=2),encoding='utf-8')
    print('ToolForge Pilot V1.4: Einrichtung und Aider-Prüfung abgeschlossen. Jetzt Start_ToolForge.cmd öffnen.')
    print('LM Studio oder OpenCode Free unter Einstellungen als Modellquelle wählen.')
if __name__=='__main__':main()
