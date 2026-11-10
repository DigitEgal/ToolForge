"""Emergency fallback uses an instance-specific local stop file, never kills arbitrary Python processes."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parent

def main():
    path=ROOT/'runtime'/'server.json'
    if not path.is_file():print('Keine laufende ToolForge-Instanz registriert.');return
    info=json.loads(path.read_text(encoding='utf-8'))
    try:
        req=Request('http://127.0.0.1:8000/api/shutdown',data=b'{}',headers={'Content-Type':'application/json','X-ToolForge-Request':'1'})
        with urlopen(req,timeout=3) as response:print(response.read().decode())
    except Exception:
        (ROOT/'runtime'/('stop-'+info['instance'])).touch()
        print('Stoppanforderung an den ToolForge-Wächter geschrieben. Laufende Jobs werden abgebrochen.')
if __name__=='__main__':main()
