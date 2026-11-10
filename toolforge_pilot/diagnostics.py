"""Opt-in detailed local diagnostics with secret redaction."""
import json
import re
import time
from pathlib import Path

def redact(text,secrets=()):
    text=str(text)
    for secret in secrets:
        if secret and secret!='lm-studio':text=text.replace(secret,'[REDACTED]')
    text=re.sub(r'(?i)(Bearer\s+)[^\s"\']+',r'\1[REDACTED]',text)
    text=re.sub(r'(?i)((?:api[_-]?key|password|secret|token)["\']?\s*[:=]\s*["\']?)[^\s,"\'}]+',r'\1[REDACTED]',text)
    return text

def record(root,event,data,secrets=()):
    folder=Path(root)/'.toolforge'/'diagnostics';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'errors.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'at':time.time(),'event':event,'detail':redact(json.dumps(data,ensure_ascii=False,default=str),secrets)},ensure_ascii=False)+'\n')
