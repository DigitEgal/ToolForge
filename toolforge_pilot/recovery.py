"""Bounded diagnosis and opt-in DuckDuckGo search (no API key)."""
import json
import re
import time
from pathlib import Path
from .diagnostics import redact

def choose_strategy(reason,output):
    lower=output.lower()
    if any(x in lower for x in ('unauthorized','connection refused','no module named','cannot find package','no windows console','timeout')):return 'Umgebung oder Verbindung korrigieren'
    if reason in ('GUARD_CONTEXT','GUARD_OUTPUT'):return 'split'
    if reason=='GUARD_SCOPE':return 'Dateiumfang und Auftrag präzisieren'
    if 'edit format' in lower:return 'Edit-Format wechseln'
    return 'Fehlerursache prüfen und gezielt reparieren'

def safe_query(text):
    # Never send whole project logs/source: only recognized error class and public module name.
    match=re.search(r'(?:Failed building wheel for|Could not build wheels? for) ([A-Za-z0-9._-]+)',text)
    if match:return (match.group(1)+' Python wheel installation failed official documentation')[:120]
    match=re.search(r'No module named [\'"]?([A-Za-z_][\w.]*)',text)
    if match:return 'Python ModuleNotFoundError '+match.group(1)[:80]
    match=re.search(r'\b([A-Za-z]*(?:Error|Exception))\b',text)
    return ('Python '+match.group(1)+' troubleshooting official documentation') if match else 'Python application error troubleshooting official documentation'

def web_research(root,error,policy,task_id='manual',query=None):
    if not policy.get('web_search'):return ''
    query=(query or safe_query(error))[:300]
    entry={'at':time.time(),'task':task_id,'query':query,'provider':'duckduckgo','results':[],'error':''}
    try:
        from ddgs import DDGS
        rows=list(DDGS(timeout=12).text(query,max_results=4,backend='duckduckgo'))
        entry['results']=[{'title':str(r.get('title',''))[:200],'url':str(r.get('href',''))[:1500],'snippet':str(r.get('body',''))[:700]} for r in rows[:4]]
        return json.dumps(entry['results'],ensure_ascii=False)
    except Exception as exc:
        entry['error']=redact(exc);return ''
    finally:
        folder=Path(root)/'.toolforge';folder.mkdir(exist_ok=True)
        with (folder/'websearch.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
