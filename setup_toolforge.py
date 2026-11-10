"""Repeatable setup: controller and Aider have separate dependency environments."""
from pathlib import Path
import json
import os
import subprocess
import sys
import venv
ROOT=Path(__file__).resolve().parent

def python_at(folder):return folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
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
    (ROOT/'setup-runtime.json').write_text(json.dumps({'aider_python':str(python_at(aider))},indent=2),encoding='utf-8')
    print('ToolForge Pilot V1.1: Einrichtung und Aider-Prüfung abgeschlossen. Jetzt Start_ToolForge.cmd öffnen.')
if __name__=='__main__':main()
