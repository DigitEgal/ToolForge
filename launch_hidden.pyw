from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
python=ROOT/'.venv'/'Scripts'/'python.exe'
if not python.exists():python=Path(sys.executable).with_name('python.exe')
folder=ROOT/'runtime';folder.mkdir(exist_ok=True)
with (folder/'startup.log').open('a',encoding='utf-8') as log:
    subprocess.Popen([str(python),str(ROOT/'start_toolforge.py')],cwd=ROOT,stdout=log,stderr=log,creationflags=0x08000000)
