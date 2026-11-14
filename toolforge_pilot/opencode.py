"""OpenCode free-model access without an extra account.

The locally installed OpenCode service exposes its free model catalog and a
one-shot text endpoint behind HTTP Basic auth. ToolForge uses that service for
preflight samples, planning, assistance and a local OpenAI-compatible bridge
for Aider. No credentials leave this machine.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
DEFAULT_MODEL = 'deepseek-v4.1-flash-free'
# Seed preference, not a benchmark claim. Unknown/new free models are appended
# in catalog order, so future models remain usable without a ToolForge update.
FAMILY_ORDER = (
    ('deepseek', 100), ('glm', 90), ('minimax', 80), ('qwen', 70),
    ('mimo', 60), ('longcat', 50), ('flint', 45), ('nemotron', 40),
    ('inkling', 35), ('iceman', 30), ('beam', 25), ('pickle', 20),
)


class OpenCodeError(RuntimeError):
    def __init__(self, message, status=None, reason='', retry_after_ms=None, model='', tried=None,
                 shared_quota=False):
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.retry_after_ms = retry_after_ms
        self.model = model
        self.tried = list(tried or [])
        # All free model names share one daily OpenCode quota. Callers must not
        # interpret a switch to another *-free model as a quota reset.
        self.shared_quota = bool(shared_quota or reason in ('rate_limit', 'rate_limited'))


class OpenCodeUnavailable(OpenCodeError):
    pass


def _service_paths():
    paths = []
    override = os.environ.get('TOOLFORGE_OPENCODE_SERVICE_FILE')
    if override:
        paths.append(Path(override).expanduser())
    state = os.environ.get('XDG_STATE_HOME')
    if state:
        paths.append(Path(state) / 'opencode' / 'service.json')
    paths.append(Path.home() / '.local' / 'state' / 'opencode' / 'service.json')
    local = os.environ.get('LOCALAPPDATA')
    if local:
        paths.append(Path(local) / 'opencode' / 'service.json')
    return list(dict.fromkeys(paths))


def service_info():
    """Return {url, password} from environment or OpenCode's local service file."""
    url = os.environ.get('TOOLFORGE_OPENCODE_URL')
    password = os.environ.get('TOOLFORGE_OPENCODE_PASSWORD')
    if url and password:
        return _validated(url, password)
    for path in _service_paths():
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get('url') and data.get('password'):
            return _validated(str(data['url']), str(data['password']))
    raise OpenCodeUnavailable('OpenCode-Dienst nicht gefunden. OpenCode installieren und einmal starten '
                             '(oder unter Einstellungen „OpenCode starten“ wählen).')


def _validated(url, password):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in LOCAL_HOSTS:
        raise OpenCodeUnavailable('OpenCode-Dienst muss lokal über HTTP erreichbar sein.')
    return {'url': url.rstrip('/'), 'password': password}


def start_service(timeout=60):
    """Start OpenCode's background service if the CLI is installed."""
    executable = shutil.which('opencode')
    if not executable:
        raise OpenCodeUnavailable('OpenCode ist nicht installiert. Setup_ToolForge.cmd installiert es optional über npm.')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        result = subprocess.run([executable, 'service', 'start'], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OpenCodeUnavailable('OpenCode-Dienst konnte nicht gestartet werden: ' + str(exc)) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()[-800:]
        raise OpenCodeUnavailable('OpenCode-Dienst konnte nicht gestartet werden: ' + (detail or 'unbekannter Fehler'))
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            return service_info()
        except OpenCodeUnavailable:
            time.sleep(0.4)
    raise OpenCodeUnavailable('OpenCode wurde gestartet, meldet seinen lokalen Dienst aber nicht.')


def _free(row):
    if not isinstance(row, dict) or row.get('providerID') != 'opencode':
        return False
    if row.get('type', 'chat') != 'chat' or row.get('enabled') is False or row.get('status', 'active') != 'active':
        return False
    costs = row.get('cost') or []
    if not costs:
        return True
    for cost in costs:
        if not isinstance(cost, dict):
            return False
        if (cost.get('input') or 0) != 0 or (cost.get('output') or 0) != 0:
            return False
    return True


def _model(row):
    limit = row.get('limit') or {}
    variants = [v.get('id') for v in row.get('variants', []) if isinstance(v, dict) and v.get('id')]
    return {'id': str(row['id']), 'name': str(row.get('name') or row['id']),
            'provider': 'opencode', 'family': str(row.get('family') or ''),
            'context': int(limit.get('context') or 200000),
            'output': int(limit.get('output') or 32000),
            'released': int((row.get('time') or {}).get('released') or 0),
            'variants': variants, 'free': True}


def sort_models(rows):
    """Prefer known strong coding families; keep catalog order as tie-breaker."""
    def score(row):
        text = (row.get('id', '') + ' ' + row.get('family', '')).lower()
        return max((weight for key, weight in FAMILY_ORDER if key in text), default=0)
    return sorted(rows, key=lambda row: (-score(row), -int(row.get('released') or 0), row.get('id', '')))


def default_order(rows):
    return [row['id'] for row in sort_models(rows)]


def _error_from_body(body, status, model):
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        data = {}
    message = data.get('message') if isinstance(data, dict) else ''
    reason = str(data.get('reason') or '') if isinstance(data, dict) else ''
    retry = data.get('retryAfterMs') if isinstance(data, dict) else None
    shared = reason in ('rate_limit', 'rate_limited')
    if status == 401:
        hint = 'OpenCode lehnt den lokalen Zugriff ab. Dienst neu starten.'
    elif shared:
        hint = ('Tageslimit der kostenlosen Modelle erschöpft. Alle freien Modelle teilen diese Quote; '
                'ein Wechsel auf ein anderes Free-Modell hilft nicht. Bitte auf Lokal bzw. eine bezahlte '
                'API ausweichen oder den Reset abwarten.')
    elif status == 404:
        hint = 'Modell ist im OpenCode-Katalog nicht mehr vorhanden.'
    else:
        hint = 'OpenCode-Anfrage fehlgeschlagen.'
    detail = str(message or body or '').strip()[:800]
    return OpenCodeError(f'{hint} {detail}'.strip(), status=status, reason=reason,
                         retry_after_ms=retry if type(retry) is int else None, model=model,
                         shared_quota=shared)


class Client:
    def __init__(self, url, password, timeout=900):
        self.url = url.rstrip('/')
        parsed = urllib.parse.urlsplit(self.url)
        if parsed.hostname not in LOCAL_HOSTS:
            raise OpenCodeUnavailable('OpenCode-Zugriff ist nur lokal erlaubt.')
        self.password = password
        self.timeout = timeout
        self._models = None
        self._models_at = 0.0

    def _request(self, path, data=None, timeout=None, method=None):
        token = base64.b64encode(('opencode:' + self.password).encode('utf-8')).decode('ascii')
        request = urllib.request.Request(
            self.url + path, data=None if data is None else json.dumps(data).encode('utf-8'),
            method=method, headers={'Content-Type': 'application/json', 'Authorization': 'Basic ' + token})
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            body = exc.read(65537).decode('utf-8', 'replace')
            raise _error_from_body(body, exc.code, str((data or {}).get('model', '') if isinstance(data, dict) else '')) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise OpenCodeError('OpenCode-Anfrage hat das Zeitlimit überschritten.', status=503,
                                    reason='timeout') from exc
            raise OpenCodeUnavailable('OpenCode-Dienst nicht erreichbar: ' + str(exc.reason)) from exc
        except TimeoutError as exc:
            raise OpenCodeError('OpenCode-Anfrage hat das Zeitlimit überschritten.', status=503,
                                reason='timeout') from exc
        except OSError as exc:
            raise OpenCodeUnavailable('OpenCode-Dienst nicht erreichbar: ' + str(exc)) from exc
        if len(raw) > 4 * 1024 * 1024:
            raise OpenCodeError('OpenCode-Antwort zu groß.')
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise OpenCodeError('OpenCode lieferte keine gültige JSON-Antwort.') from exc

    def info(self):
        return self._request('/api/info', timeout=15)

    def models(self, refresh=False):
        if not refresh and self._models is not None and time.monotonic() - self._models_at < 60:
            return self._models
        data = self._request('/api/model', timeout=30)
        rows = data.get('data') if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise OpenCodeError('OpenCode-Modellkatalog ist unlesbar.')
        values = sort_models([_model(row) for row in rows if _free(row)])
        self._models = values
        self._models_at = time.monotonic()
        return values

    def model_ids(self):
        return [row['id'] for row in self.models()]

    def pick_default(self):
        rows = self.models()
        if not rows:
            raise OpenCodeUnavailable('OpenCode bietet aktuell keine kostenlosen Chat-Modelle an.')
        return rows[0]['id']

    def status(self, start=False):
        try:
            info = self.info()
            rows = self.models(refresh=True)
            return {'available': True, 'url': self.url, 'version': str(info.get('version') or ''),
                    'models': rows, 'order': default_order(rows), 'error': ''}
        except OpenCodeError as exc:
            if start:
                try:
                    start_service()
                    client = client_from_service()
                    return client.status(False)
                except OpenCodeError as start_exc:
                    return {'available': False, 'url': self.url, 'version': '', 'models': [],
                            'order': [], 'error': str(start_exc)}
            return {'available': False, 'url': self.url, 'version': '', 'models': [],
                    'order': [], 'error': str(exc)}

    def generate_one(self, prompt, model, timeout=None):
        if not isinstance(prompt, str) or not prompt.strip():
            raise OpenCodeError('Leerer OpenCode-Auftrag.')
        start = time.monotonic()
        data = self._request('/api/experimental/generate/text',
                             {'prompt': prompt, 'model': {'id': model, 'providerID': 'opencode'}},
                             timeout=timeout or self.timeout)
        payload = data.get('data') if isinstance(data, dict) else None
        text = payload.get('text') if isinstance(payload, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise OpenCodeError('OpenCode lieferte eine leere Antwort.', model=model)
        return {'text': text, 'model': model, 'raw': data,
                'seconds': round(time.monotonic() - start, 3)}

    def chain(self, primary, order=None, fallback=True, skip=None, limit=40):
        rows = self.models()
        available = [row['id'] for row in rows]
        if not available:
            raise OpenCodeUnavailable('OpenCode bietet aktuell keine kostenlosen Chat-Modelle an.')
        if not primary or primary not in available:
            primary = available[0]
        chain = [primary]
        if fallback:
            preferred = [name for name in (order or []) if name in available]
            # A configured order doubles as the allow-list of eligible models.
            chain += preferred if preferred else available
        skip = set(skip or ())
        result = [name for name in dict.fromkeys(chain) if name not in skip]
        if not result:
            raise OpenCodeError('Alle vorgesehenen kostenlosen Modelle sind bis zum Reset als erschöpft markiert.',
                                reason='rate_limit')
        return result[:max(1, int(limit))]

    def generate(self, prompt, model=None, order=None, fallback=True, skip=None, timeout=None, on_switch=None):
        chain = self.chain(model or self.pick_default(), order, fallback, skip)
        failures = []
        for index, name in enumerate(chain):
            try:
                result = self.generate_one(prompt, name, timeout)
                result['tried'] = [row['model'] for row in failures]
                return result
            except OpenCodeError as exc:
                exc.model = exc.model or name
                failures.append({'model': name, 'status': exc.status, 'reason': exc.reason,
                                 'retry_after_ms': exc.retry_after_ms, 'error': str(exc)})
                if exc.shared_quota:
                    # A different -free name uses the same quota. Continuing would
                    # waste time and produce misleading "model switch" messages.
                    raise OpenCodeError(str(exc), status=429, reason='rate_limit',
                                        retry_after_ms=exc.retry_after_ms, model=name,
                                        tried=[row['model'] for row in failures],
                                        shared_quota=True) from exc
                retryable = exc.status in (404, 429, 503)
                if not retryable:
                    raise OpenCodeError(str(exc), status=exc.status, reason=exc.reason,
                                        retry_after_ms=exc.retry_after_ms, model=name,
                                        tried=[row['model'] for row in failures]) from exc
                if index + 1 < len(chain) and on_switch:
                    on_switch(name, chain[index + 1], exc)
        retry = min((row['retry_after_ms'] for row in failures if type(row.get('retry_after_ms')) is int),
                    default=None)
        detail = '; '.join(f"{row['model']}: {row['error']}" for row in failures[-3:])
        raise OpenCodeError('Kein kostenloses OpenCode-Modell konnte antworten. ' + detail,
                            status=429 if retry else 502, reason='rate_limit' if retry else 'all_models_failed',
                            retry_after_ms=retry, tried=[row['model'] for row in failures])


def client(url=None, password=None, timeout=900):
    if url and password:
        info = _validated(url, password)
    else:
        info = service_info()
    return Client(info['url'], info['password'], timeout=timeout)


def client_from_service(*args, **kwargs):
    return client(*args, **kwargs)


def open_console(directory=None):
    """Open the interactive OpenCode terminal for inspecting sessions.

    The terminal is only started on explicit user request. It does not slow
    down normal ToolForge requests because no service call or model request is
    made here.
    """
    executable = shutil.which('opencode')
    if not executable:
        raise OpenCodeUnavailable('OpenCode ist nicht installiert. Setup_ToolForge.cmd installiert es optional über npm.')
    workdir = Path(directory).expanduser() if directory else Path.home()
    if not workdir.is_dir():
        workdir = Path.home()
    try:
        if os.name == 'nt':
            comspec = os.environ.get('COMSPEC', 'cmd.exe')
            # `start` creates a visible console even when ToolForge itself runs
            # without a console window. /k keeps the window open for sessions.
            subprocess.Popen([comspec, '/d', '/c', 'start', 'ToolForge OpenCode',
                              comspec, '/k', executable], cwd=str(workdir), close_fds=True)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-a', 'Terminal', executable], cwd=str(workdir))
        else:
            terminal = shutil.which('x-terminal-emulator') or shutil.which('gnome-terminal')
            if terminal:
                subprocess.Popen([terminal, '-e', executable], cwd=str(workdir))
            else:
                subprocess.Popen([executable], cwd=str(workdir))
    except OSError as exc:
        raise OpenCodeUnavailable('OpenCode-Konsole konnte nicht geöffnet werden: ' + str(exc)) from exc
    return {'started': True, 'command': executable, 'directory': str(workdir)}


class OpenCodeStudio:
    """LM-Studio-like facade so preflight and assistance can use free models."""

    def __init__(self, opencode_client, fallback=True, order=None, cancel=None, timeout=900):
        self.client = opencode_client
        self.fallback = fallback
        self.order = list(order or [])
        self.cancel = cancel
        self.timeout = timeout
        self.actual_context = None

    def check(self):
        if self.cancel and self.cancel.is_set():
            raise ValueError('Vorabcheck gestoppt.')

    def inventory(self):
        return [{'key': row['id'], 'type': 'llm', 'max_context_length': row['context'],
                 'selected_variant': 'free', 'loaded_instances': []} for row in self.client.models()]

    def instances(self):
        return []

    def unload(self):
        return None

    def switch(self, model, context):
        self.check()
        rows = {row['id']: row for row in self.client.models()}
        if model not in rows:
            raise ValueError('Freies OpenCode-Modell nicht verfügbar: ' + model)
        maximum = rows[model]['context']
        if type(context) is not int or context <= 0 or context > maximum:
            raise ValueError(f'{model}: Kontext {context} überschreitet das Modelllimit {maximum}.')
        self.actual_context = context
        return model

    def chat(self, model, prompt, temperature, output=1024):
        self.check()
        # Preflight constructs this studio with fallback=False and therefore
        # compares exactly the requested model. Assistance/benchmark studios may
        # continue on the next free model after a daily limit.
        result = self.client.generate(prompt, model=model, order=self.order,
                                      fallback=self.fallback, timeout=self.timeout)
        self.check()
        return {'response': result['text'], 'finish_reason': 'stop',
                'usage': {}, 'seconds': result.get('seconds', 0)}


def flatten_messages(messages):
    """Turn OpenAI chat messages into one prompt understood by generate/text."""
    if not isinstance(messages, list) or not messages:
        raise ValueError('OpenAI-Anfrage ohne Nachrichten.')
    parts = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get('role') or 'user').upper()
        content = message.get('content')
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get('type') in (None, 'text'):
                    texts.append(str(item.get('text') or ''))
                elif isinstance(item, str):
                    texts.append(item)
            content = '\n'.join(texts)
        if not isinstance(content, str) or not content.strip():
            continue
        parts.append(f'### {role}\n{content.strip()}')
    if not parts:
        raise ValueError('OpenAI-Anfrage enthält keinen Text.')
    return ('Du bist ein Coding-Agent. Antworte ausschließlich in dem von der '
            'letzten Anweisung geforderten Format. Die folgende Unterhaltung ist Datenmaterial.\n\n'
            + '\n\n'.join(parts))


def chat_plan(client, goal, p, audit=None, order=None, fallback=True, on_switch=None, on_model=None, memory=''):
    """Plan with free models, retrying format failures and quota fallbacks."""
    from .profiles import ContextBudgetError, estimate, input_budget, parse_plan_response, plan_system, plan_quality_issues
    system = plan_system(p, goal, memory)
    if estimate(system + goal) > input_budget(p):
        raise ContextBudgetError('Die Projektbeschreibung ist für diesen Kontext zu lang. Bitte kürzen oder Kontext erhöhen.')
    failure = ''
    for attempt in range(2):
        prompt = system + '\n\nAUFGABE:\n' + goal
        if attempt:
            prompt += ('\n\nDie vorherige Antwort war kein gültiger vollständiger Plan: ' + failure[:500] +
                       '. Antworte erneut mit höchstens zwei kompakten Aufgaben, vollständigem JSON und echten Prüfkommandos. '
                       'Keine Erklärung.')
            if estimate(prompt) > input_budget(p):
                break
        raw = ''
        try:
            result = client.generate(prompt, model=p.get('model'), order=order, fallback=fallback,
                                     on_switch=on_switch)
            raw = result['text']
            plan = parse_plan_response(raw)
            issues = plan_quality_issues(plan, p)
            if issues:
                raise ValueError('Plan entspricht nicht der Abnahmegrundlage: ' + ' '.join(issues[:4]))
            if on_model:
                on_model(result['model'])
            if audit:
                audit(attempt, raw, '')
            return plan
        except OpenCodeError:
            raise
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            failure = str(exc)
            if audit:
                audit(attempt, raw, failure)
    raise ValueError('Kein gültiger Aufgabenplan nach zwei Versuchen: ' + failure +
                     ' Modell/Ausgabelimit prüfen oder Ziel eingrenzen. Vorhandener Plan bleibt erhalten.')


def completion(client, payload, model=None, order=None, fallback=True, skip=None, on_switch=None):
    """Create an OpenAI-compatible completion through the OpenCode service."""
    prompt = flatten_messages(payload.get('messages'))
    primary = str(model or payload.get('model') or '').strip()
    primary = primary.split('/')[-1] if primary.startswith(('openai/', 'opencode/')) else primary
    result = client.generate(prompt, model=primary or None, order=order, fallback=fallback,
                             skip=skip, on_switch=on_switch,
                             timeout=int(payload.get('timeout') or 900))
    text = result['text']
    return {'id': 'chatcmpl-' + os.urandom(8).hex(), 'object': 'chat.completion',
            'created': int(time.time()), 'model': result['model'],
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': text},
                         'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': max(1, len(prompt) // 4),
                      'completion_tokens': max(1, len(text) // 4),
                      'total_tokens': max(2, (len(prompt) + len(text)) // 4)},
            'x_toolforge': {'fallbacks': result.get('tried', [])}}
