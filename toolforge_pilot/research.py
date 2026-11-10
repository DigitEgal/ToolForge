"""Research with domain allowlists, opened-source evidence, cache and task mapping."""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import re
import socket
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .diagnostics import redact

CACHE_TTL = 7 * 24 * 3600
MAX_RESULTS = 8
MAX_SOURCE_BYTES = 300_000


def domains(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        rows = re.split(r'[\s,;]+', value)
    elif isinstance(value, list):
        rows = value
    else:
        raise ValueError('Domainfilter muss Text oder eine Liste sein.')
    clean = []
    for row in rows:
        row = str(row).strip().lower().removeprefix('https://').removeprefix('http://').split('/')[0]
        row = row.split(':')[0].strip('.')
        if not row:
            continue
        if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', row):
            raise ValueError('Ungültige Filterdomain: ' + row)
        if row not in clean:
            clean.append(row)
    return clean[:30]


def allowed(url: str, allow: list[str]) -> bool:
    try:
        host = (urlsplit(url).hostname or '').lower()
    except ValueError:
        return False
    if not host or host in ('localhost', 'localhost.localdomain') or host.endswith('.local'):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        # Literal addresses bypass DNS-based private-range checks; only named hosts are allowed.
        return False
    if not allow:
        return True
    return any(host == domain or host.endswith('.' + domain) for domain in allow)


def _public_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Quelle benötigt http(s).')
    host = parsed.hostname
    for family, _, _, _, address in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == 'https' else 80)):
        ip = ipaddress.ip_address(address[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError('Private Quellen werden nicht geöffnet.')
    return url


def _plain(html_text: str) -> str:
    html_text = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', html_text)
    html_text = re.sub(r'(?s)<[^>]+>', ' ', html_text)
    return re.sub(r'\s+', ' ', html.unescape(html_text)).strip()


def evidence(url: str, terms: list[str], allow: list[str]) -> list[dict]:
    if not allowed(url, allow):
        return []
    try:
        safe_url = _public_url(url)
        request = Request(safe_url, headers={'User-Agent': 'ToolForge-Research/1.1'})
        with urlopen(request, timeout=12) as response:
            raw = response.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            raw = raw[:MAX_SOURCE_BYTES]
        content_type = response.headers.get('Content-Type', '') if 'response' in locals() else ''
        if 'pdf' in content_type.lower():
            return [{'text': 'PDF-Quelle nicht automatisch extrahiert.', 'score': 0}]
        text = _plain(raw.decode('utf-8', errors='replace'))
    except Exception as exc:
        return [{'text': 'Quelle nicht lesbar: ' + redact(exc), 'score': 0}]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    wanted = [term.lower() for term in terms if len(term) >= 3]
    scored = []
    for sentence in sentences:
        lowered = sentence.lower()
        score = sum(1 for term in wanted if term in lowered)
        if score:
            scored.append({'text': sentence.strip()[:1200], 'score': score})
    scored.sort(key=lambda row: row['score'], reverse=True)
    return scored[:3] or [{'text': text[:1000], 'score': 0}]


def cache_path(project: Path) -> Path:
    return Path(project) / '.toolforge' / 'research-cache.json'


def load_cache(project: Path) -> dict:
    try:
        value = json.loads(cache_path(project).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(project: Path, cache: dict) -> None:
    now = time.time()
    cache = {key: row for key, row in cache.items() if now - row.get('at', 0) <= CACHE_TTL}
    path = cache_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


def cache_rows(project: Path) -> list[dict]:
    cache = load_cache(project)
    return sorted(cache.values(), key=lambda row: row.get('at', 0), reverse=True)


def _journal(project: Path, entry: dict) -> None:
    folder = Path(project) / '.toolforge'
    folder.mkdir(exist_ok=True)
    with (folder / 'websearch.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + '\n')


def search(project: Path, query: str, policy: dict | None = None, task_id: str = 'manual',
           error: str = '', allow: list[str] | None = None, force: bool = False) -> dict:
    policy = policy or {}
    query = str(query).strip()
    if not query or len(query) > 300:
        raise ValueError('Suchbegriff: 1 bis 300 Zeichen.')
    allow = domains(allow if allow is not None else policy.get('research_domains'))
    key = hashlib.sha256((query.lower() + '|' + '|'.join(allow)).encode()).hexdigest()[:32]
    cache = load_cache(project)
    if not force and key in cache:
        cached = dict(cache[key])
        cached['cached'] = True
        cached['cached_at'] = cached.get('at')
        _journal(project, {**cached, 'cache_hit': True, 'task': task_id})
        return cached
    entry = {'id': uuid.uuid4().hex, 'at': time.time(), 'task': task_id, 'query': query,
             'domains': allow, 'provider': 'duckduckgo', 'results': [], 'error': '',
             'error_hash': hashlib.sha256(str(error).encode()).hexdigest()[:16] if error else '',
             'cache_key': key}
    terms = [part for part in re.split(r'\W+', query) if len(part) >= 3][:8]
    try:
        from ddgs import DDGS
        rows = list(DDGS(timeout=12).text(query, max_results=MAX_RESULTS, backend='duckduckgo'))
        for row in rows:
            href = str(row.get('href', ''))
            if not allowed(href, allow):
                continue
            entry['results'].append({
                'title': str(row.get('title', ''))[:200], 'url': href[:1500],
                'host': urlsplit(href).hostname or '',
                'snippet': str(row.get('body', ''))[:700],
            })
            if len(entry['results']) >= 4:
                break
        for row in entry['results'][:3]:
            row['evidence'] = evidence(row['url'], terms, allow)
    except Exception as exc:
        entry['error'] = redact(exc)
    cache[key] = entry
    save_cache(project, cache)
    _journal(project, entry)
    return entry


def web_research_json(root: Path, error: str, policy: dict, task_id: str = 'manual',
                      query: str | None = None) -> str:
    from .recovery import safe_query
    try:
        entry = search(Path(root), query or safe_query(error), policy, task_id, error)
    except (ValueError, OSError):
        return ''
    if not entry.get('results'):
        return ''
    return json.dumps(entry['results'], ensure_ascii=False)
