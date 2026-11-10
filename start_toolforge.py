"""Local web entry point; no dependency installation during normal startup."""
from pathlib import Path
import json
import socket
import sys
import threading
import time
import traceback
import uuid
import os
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8000'

def is_toolforge():
    try:
        with urlopen(URL + '/api/workbench', timeout=1) as response:
            return json.load(response).get('name') == 'ToolForge'
    except Exception:
        return False

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
    def open_when_ready():
        for _ in range(100):
            if is_toolforge(): webbrowser.open(URL);return
            time.sleep(.1)
    threading.Thread(target=open_when_ready, daemon=True).start()
    print('ToolForge Pilot 0.8 | ' + URL + '\nBeenden über die UI oder Stop_ToolForge.cmd.')
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
        if info.exists() and json.loads(info.read_text()).get('instance')==instance:info.unlink()
        (runtime/('stop-'+instance)).unlink(missing_ok=True)

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: pass
    except Exception:
        traceback.print_exc();sys.exit(1)
