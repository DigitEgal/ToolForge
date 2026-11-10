"""Local web entry point; no dependency installation during normal startup."""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8000'


def browser_candidates():
    """Chromium browsers that support a dedicated --app window on Windows."""
    if os.name != 'nt':
        return []
    folders = [os.environ.get('PROGRAMFILES'), os.environ.get('PROGRAMFILES(X86)'),
               os.environ.get('LOCALAPPDATA')]
    relatives = (r'Google\Chrome\Application\chrome.exe', r'Microsoft\Edge\Application\msedge.exe')
    return [str(Path(folder) / relative) for folder in folders if folder
            for relative in relatives if (Path(folder) / relative).is_file()]


def open_ui(track):
    """Open a tracked app window so ToolForge can close it again on shutdown."""
    if os.environ.get('TOOLFORGE_NO_BROWSER') or track.get('stop') and track['stop'].is_set():
        return
    profile = ROOT / 'runtime' / 'browser-profile'
    for executable in browser_candidates():
        try:
            profile.mkdir(parents=True, exist_ok=True)
            track['process'] = subprocess.Popen(
                [executable, '--app=' + URL, '--user-data-dir=' + str(profile), '--no-first-run',
                 '--no-default-browser-check', '--window-size=1440,960'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            continue
    # Unknown default browser: the UI then shows a closing hint instead.
    webbrowser.open(URL)

def is_toolforge():
    try:
        with urlopen(URL + '/api/workbench', timeout=1) as response:
            return json.load(response).get('name') == 'ToolForge'
    except Exception:
        return False

def close_ui(track):
    track['stop'].set()
    process = track.get('process')
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            try: process.kill()
            except Exception: pass

def main():
    if sys.version_info < (3, 11): raise RuntimeError('Python 3.11 oder neuer erforderlich.')
    try:
        import uvicorn
        from backend.main import app
    except ImportError as exc:
        raise RuntimeError('Abhängigkeiten fehlen. Einmal Setup_ToolForge.cmd ausführen. Details: ' + str(exc)) from exc
    if not (ROOT / 'frontend/dist/index.html').is_file():
        raise RuntimeError('Frontend-Build fehlt. Im Ordner frontend: npm ci und npm run build.')
    with socket.socket() as probe:
        occupied = probe.connect_ex(('127.0.0.1', 8000)) == 0
    if occupied:
        if is_toolforge():
            print('ToolForge läuft bereits. Browser wird geöffnet.');webbrowser.open(URL);return
        raise RuntimeError('Port 8000 ist durch eine andere Anwendung belegt. Diese beenden und erneut starten.')
    track = {'process': None, 'stop': threading.Event()}
    def open_when_ready():
        for _ in range(100):
            if track['stop'].is_set(): return
            if is_toolforge(): open_ui(track);return
            time.sleep(.1)
    threading.Thread(target=open_when_ready, daemon=True).start()
    print('ToolForge Pilot V1.0 | ' + URL + '\nBeenden über die UI oder Stop_ToolForge.cmd.')
    runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
    instance=uuid.uuid4().hex
    info=runtime/'server.json'
    info.write_text(json.dumps({'instance':instance,'pid':os.getpid()}),encoding='utf-8')
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8000,log_level='warning',access_log=False))
    def stop():
        for session in list(app.state.pilot.sessions.values()):
            session.cancel.set()
            if session.engine:session.engine.stop.set()
        server.should_exit=True
    app.state.shutdown=stop
    def watch():
        while not server.should_exit:
            if (runtime/('stop-'+instance)).exists():stop();return
            time.sleep(.5)
    threading.Thread(target=watch,daemon=True).start()
    try:server.run()
    finally:
        close_ui(track)
        if info.exists() and json.loads(info.read_text()).get('instance')==instance:info.unlink()
        (runtime/('stop-'+instance)).unlink(missing_ok=True)

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: pass
    except Exception:
        traceback.print_exc();sys.exit(1)
