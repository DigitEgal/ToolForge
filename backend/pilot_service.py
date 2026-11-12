"""In-process bridge between the browser workbench and the verified Pilot engine."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.parse
from toolforge_pilot.core import APP_ROOT, Store, Engine, AiderAdapter, atomic_json, data_root, fingerprint, project_path, progress, validate_plan
from toolforge_pilot.profiles import profile, discover_models, adapt_plan, chat_plan, effective_edit
from toolforge_pilot import opencode, project_index, benchmarks, planning, task_graph, scenarios, environments, operations, routing
from toolforge_pilot.simulation import DemoAdapter
from toolforge_pilot.preflight import Studio, MODEL_LOCK, evaluate, suggest, signature, context_compatible
from backend.events import EventHub

AIDER_PYTHON = APP_ROOT / '.aider-venv' / ('Scripts/python.exe' if os.name=='nt' else 'bin/python')
DEFAULTS = {'aider_python': str(AIDER_PYTHON) if AIDER_PYTHON.is_file() else sys.executable, 'python': sys.executable, 'base': 'http://localhost:1234/v1', 'model': '', 'context_tokens': 20000,
            'output_tokens': 2048, 'temperature': 0.2, 'top_p': 0.95, 'edit': 'auto', 'budget': 20, 'timeout': 900,
            'provider': 'lmstudio', 'opencode_fallback': True, 'opencode_order': [], 'small_model_mode': True,
            'source_mode': 'local', 'preference': 'balanced', 'local_model': '', 'free_model': '',
            'api_base': 'https://api.openai.com/v1', 'api_model': '',
            'sandbox':False,'sandbox_network':'','sandbox_memory':'4g','sandbox_cpus':2,'sandbox_pids':256,'sandbox_ports':'',
            'web_search':False, 'research_domains':'', 'debug_logging':False, 'allow_pip': False, 'allow_choco': False, 'allow_npm': False, 'simulation': False}


from backend.assistance import AssistanceMixin

class Session(AssistanceMixin):
    def __init__(self, folder, project_id=None):
        self.store = Store(project_path(folder))
        self.project_id = project_id or ''
        self.guard = threading.Lock()
        self.worker = None
        self.running = False
        self.maintenance = False
        self.remaining_budget = 0
        self.engine = None
        self.cancel = threading.Event()
        self.pause_request = threading.Event()
        self.error = ''
        self.phase = 'Bereit'
        self.logs = ''
        self.pending_answers = {}
        self.answer_lock = threading.Lock()
        self.hub = None
        self.ident = str(self.store.project)
        self.benchmark = None
        self.research_result = None
        self.acceptance = scenarios.last(self.store.project)
        self.settings_path = self.store.log_root.parent / 'settings.json'
        self.settings = dict(DEFAULTS)
        if self.settings_path.is_file():
            settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
            self.settings.update({k: v for k, v in settings.items() if k in DEFAULTS})
        # Migrate V1.2/V1.3-pre settings: one active model was shared by every
        # source. Combined presets need a stable model per source.
        source_mode = self.settings.get('source_mode')
        if source_mode not in routing.SOURCE_MODES:
            source_mode = 'free' if self.settings.get('provider') == 'opencode' else 'local'
            self.settings['source_mode'] = source_mode
        if self.settings.get('preference') not in routing.PREFERENCE_LABELS:
            self.settings['preference'] = 'balanced'
        provider = self.settings.get('provider')
        if provider not in ('lmstudio', 'opencode', 'api'):
            provider = routing.source_provider(routing.mode_sources(source_mode)[0])
            self.settings['provider'] = provider
        if routing.provider_source(provider) not in routing.mode_sources(source_mode):
            self.settings['provider'] = routing.source_provider(routing.mode_sources(source_mode)[0])
        model = str(self.settings.get('model') or '')
        if not self.settings.get('local_model') and self.settings['provider'] != 'opencode':
            self.settings['local_model'] = model
        if not self.settings.get('free_model') and self.settings['provider'] == 'opencode':
            self.settings['free_model'] = model
        if not isinstance(self.settings.get('opencode_order'), list):
            self.settings['opencode_order'] = []
        self.remote_key = ''
        self.blocked_sources = {}
        # Normalize the active model from its source-specific field.
        active_source = routing.provider_source(self.settings['provider'])
        source_model = self.source_model(active_source)
        if source_model:
            self.settings['model'] = source_model
        self.opencode_last_model = ''
        self.opencode_retry = {}
        self.plan_source = ''
        self.api_key = 'lm-studio'
        self.preflight_path = self.store.log_root.parent / 'preflight.json'
        self.preflight = None
        if self.preflight_path.is_file():
            self.preflight = json.loads(self.preflight_path.read_text(encoding='utf-8'))
            if self.preflight.get('status') == 'running':
                self.preflight.update(status='error', error='Vorheriger Vorabcheck wurde unterbrochen.')
        self.init_assistance()
        # Full incremental index: symbols, imports and dependencies; only changed files are re-read.
        try:
            self.index = project_index.refresh(self.store.project)
        except (OSError, ValueError):
            self.index = project_index.load(self.store.project) or {'files': {}, 'summary': {}}
        operations.rotate_diagnostics(self.store.project)
        # Existing project files are inspected, never inferred to be successful code.
        self.scan = self.scan_project()
        pending_file = self.store.log_root.parent / 'pending-answers.json'
        if pending_file.exists(): self.pending_answers = json.loads(pending_file.read_text(encoding='utf-8'))

    @property
    def busy(self):
        return self.running or self.maintenance

    def scan_project(self):
        index = getattr(self, 'index', None) or project_index.load(self.store.project)
        if index:
            files = sorted(index.get('files', {}))
            file_count = len(files)
            truncated = bool(index.get('summary', {}).get('truncated'))
        else:
            from toolforge_pilot.core import SKIP_DIRS
            files = []
            for parent, dirs, names in os.walk(self.store.project):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (Path(parent) / d).is_symlink()]
                for name in names:
                    if name.startswith(('.env', '.aider')): continue
                    file = Path(parent) / name
                    if file.is_symlink(): continue
                    files.append(str(file.relative_to(self.store.project)))
            files = sorted(files); file_count = len(files); truncated = False
        docs = {}
        for name in ('README.md', 'PROGRESS.md', 'TOOLFORGE_ROADMAP.md'):
            file = self.store.project / name
            if file.is_file() and not file.is_symlink():
                docs[name] = file.read_text(encoding='utf-8', errors='replace')[:5000]
        return {'files': files, 'file_count': file_count, 'truncated': truncated, 'documents': docs,
                'git_present': (self.store.project / '.git').exists(), 'has_environment': (self.store.project / '.venv').is_dir()}

    def snapshot(self):
        # Store.state is only mutated by a worker, and serializable snapshots are short operations.
        state = json.loads(json.dumps(self.store.state)) if self.store.state else None
        graph = task_graph.build(self.store.project, self.store.state)
        return {'folder': str(self.store.project), 'busy': self.busy, 'phase': self.phase, 'error': self.error,
                'assistance':self.assistance, 'pause_requested':self.pause_request.is_set(), 'preflight': self.preflight, 'pending_answers': list(self.pending_answers), 'settings': self.settings, 'state': state, 'progress': progress(state) if state else None,
                'logs': self.logs[-60000:], 'log_folder': str(self.store.log_root), 'scan': self.scan,
                'index': project_index.status(self.store.project), 'graph': graph,
                'scenarios': self.acceptance or scenarios.last(self.store.project),
                'benchmark': self.benchmark,
                'research': self.research_result,
                'opencode': {'last_model': self.opencode_last_model,
                             'blocked_models': sorted(name for name, until in self.opencode_retry.items() if until > time.time()),
                             'blocked_sources': {name: until for name, until in self.blocked_sources.items()
                                                 if until > time.time()},
                             'order': self.effective_sources(include_blocked=True)},
                'sources': {'mode': self.settings.get('source_mode', 'local'),
                            'preference': self.settings.get('preference', 'balanced'),
                            'labels': routing.SOURCE_LABELS,
                            'modes': routing.MODE_LABELS,
                            'preferences': routing.PREFERENCE_LABELS,
                            'effective': list(self.effective_sources()),
                            'remote_key_set': bool(self.remote_key)},
                'operations': operations.operations_status(self.store.project),
                'environment': {'lock_file': str(APP_ROOT / 'runtime' / 'environment-lock.json'),
                                'presets': environments.list_presets()}}

    def provider(self):
        return self.settings.get('provider', 'lmstudio')

    def active_source(self):
        return routing.provider_source(self.provider())

    def source_mode(self):
        return self.settings.get('source_mode', 'local')

    def preference(self):
        return self.settings.get('preference', 'balanced')

    def effective_sources(self, include_blocked=False):
        blocked = None if include_blocked else self.blocked_sources
        return list(routing.source_order(self.source_mode(), self.preference(), blocked))

    def source_blocked(self, source):
        until = self.blocked_sources.get(source)
        if until and until <= time.time():
            self.blocked_sources.pop(source, None)
            until = None
        return bool(until)

    def block_source(self, source, retry_after_ms=None, reason=''):
        retry = retry_after_ms if type(retry_after_ms) is int and retry_after_ms > 0 else 60 * 60 * 1000
        self.blocked_sources[source] = time.time() + max(60, retry / 1000)
        minutes = max(1, int(retry / 60000) + 1)
        self.emit('log', f'{routing.source_title(source)} ist vorübergehend gesperrt (ca. {minutes} Minuten). '
                         f'{reason}\n'.strip() + '\n')

    def blocked_sources_message(self):
        parts = []
        for source, until in self.blocked_sources.items():
            if until > time.time():
                minutes = max(1, int((until - time.time()) / 60) + 1)
                parts.append(f'{routing.source_title(source)} noch ca. {minutes} Minuten')
        return '; '.join(parts)

    def source_model(self, source=None):
        source = source or self.active_source()
        if source == 'free':
            value = self.settings.get('free_model') or ''
        elif source == 'api':
            value = self.settings.get('api_model') or ''
        else:
            value = self.settings.get('local_model') or ''
        # Settings migrated at runtime (or edited by other components) may only
        # carry the active model. Keep that model usable for its own source.
        if not value and source == self.active_source():
            value = self.settings.get('model') or ''
        return str(value)

    def activate_source(self, source, model=''):
        provider = routing.source_provider(source)
        self.settings['provider'] = provider
        if model:
            if source == 'free':
                self.settings['free_model'] = model
            elif source == 'api':
                self.settings['api_model'] = model
            else:
                self.settings['local_model'] = model
            self.settings['model'] = model
        else:
            self.settings['model'] = self.source_model(source)
        atomic_json(self.settings_path, self.settings)

    def provider_signature(self):
        # Active provider/model is intentionally not part of this signature:
        # fallback may switch it. Accepted settings and goal are checked
        # separately, while a changed preset/config invalidates the report.
        return json.dumps({'mode': self.source_mode(), 'preference': self.preference(),
                           'local': self.settings.get('base', ''),
                           'api': self.settings.get('api_base', ''),
                           'local_model': self.settings.get('local_model', ''),
                           'free_model': self.settings.get('free_model', ''),
                           'api_model': self.settings.get('api_model', ''),
                           'free_order': self.settings.get('opencode_order', [])},
                          sort_keys=True, ensure_ascii=False)

    def profile_key(self, candidate=None):
        candidate = candidate or self.settings
        provider = candidate.get('provider', 'lmstudio')
        model = str(candidate.get('model', ''))
        if provider == 'opencode':
            return 'opencode|' + model
        if provider == 'api':
            return 'api|' + str(candidate.get('api_base', '')).rstrip('/') + '|' + model
        return str(candidate.get('base', '')).rstrip('/') + '|' + model

    def opencode_client(self):
        try:
            return opencode.client(timeout=int(self.settings.get('timeout', 900)))
        except opencode.OpenCodeUnavailable as exc:
            raise ValueError(str(exc)) from exc

    def api_studio(self, preflight=False):
        return routing.APIStudio(self.settings.get('api_base', ''), self.remote_key,
                                 int(self.settings.get('timeout', 900)), self.cancel,
                                 fallback_model=self.settings.get('api_model', ''))

    def local_studio(self, preflight=False):
        return Studio(self.settings['base'], self.api_key, int(self.settings['timeout']), self.cancel)

    def preflight_studio(self):
        order = self.effective_sources(include_blocked=True)
        if not order:
            raise ValueError('Keine Modellquelle im gewählten Profil.')
        prefix = len(order) > 1
        return routing.RoutingStudio(
            order,
            local_factory=lambda: self.local_studio(True),
            free_factory=lambda: opencode.OpenCodeStudio(
                self.opencode_client(), fallback=False,
                order=self.settings.get('opencode_order') or [], cancel=self.cancel,
                timeout=int(self.settings['timeout'])),
            api_factory=lambda: self.api_studio(True),
            blocked=self.blocked_sources, prefix=prefix, cancel=self.cancel)

    def configure(self, settings):
        if self.busy: raise ValueError('Während eines Laufs erst pausieren oder stoppen.')
        clean = {k: v for k, v in settings.items() if k in DEFAULTS}
        old = self.settings
        candidate = {**old, **clean}
        mode = candidate.get('source_mode')
        if mode not in routing.SOURCE_MODES:
            raise ValueError('Modellquellen-Vorauswahl ist ungültig.')
        preference = candidate.get('preference')
        if preference not in routing.PREFERENCE_LABELS:
            raise ValueError('Reihenfolge-Vorauswahl ist ungültig.')
        mode_changed = mode != old.get('source_mode')
        preference_changed = preference != old.get('preference')
        provider = candidate.get('provider')
        if mode_changed or preference_changed:
            provider = routing.source_provider(routing.source_order(mode, preference)[0])
        if provider not in ('lmstudio', 'opencode', 'api'):
            raise ValueError('Modellquelle: LM Studio, OpenCode Free oder API.')
        if routing.provider_source(provider) not in routing.mode_sources(mode):
            raise ValueError('Die aktive Quelle gehört nicht zur gewählten Vorauswahl.')
        candidate['provider'] = provider
        order = candidate.get('opencode_order') or []
        if not isinstance(order, list) or len(order) > 40 or any(
                not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9._:/@-]{1,160}', name) for name in order):
            raise ValueError('Fallback-Reihenfolge: höchstens 40 gültige Modell-IDs.')
        candidate['opencode_order'] = list(dict.fromkeys(name.strip() for name in order if name.strip()))
        api_base = str(candidate.get('api_base') or '').strip().rstrip('/')
        parsed = urllib.parse.urlsplit(api_base)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            raise ValueError('API-Basis muss eine vollständige HTTP(S)-Adresse sein.')
        candidate['api_base'] = api_base
        for key in ('local_model', 'free_model', 'api_model', 'api_base', 'base'):
            if not isinstance(candidate.get(key), str):
                raise ValueError('Modell- und Adressfelder müssen Textwerte sein.')
        # Keep the model that belongs to the active source. A pure preset change
        # must not overwrite a previously saved free/local/API model.
        if not mode_changed:
            requested_model = str(clean.get('model', old.get('model', '')) or '').strip()
            active_source = routing.provider_source(provider)
            if requested_model or 'model' in clean:
                if active_source == 'free': candidate['free_model'] = requested_model
                elif active_source == 'api': candidate['api_model'] = requested_model
                else: candidate['local_model'] = requested_model
        candidate['model'] = self.source_model_for(candidate, routing.provider_source(provider),
                                                   fallback=not mode_changed)
        p = profile(candidate)
        candidate.update(context_tokens=p['context_tokens'], output_tokens=p['output_tokens'], temperature=p['temperature'])
        try:
            top_p = float(candidate.get('top_p', .95))
        except (TypeError, ValueError):
            raise ValueError('Top-p muss eine Zahl zwischen 0 und 1 sein.')
        if not 0 < top_p <= 1: raise ValueError('Top-p muss zwischen 0 und 1 liegen.')
        candidate['top_p'] = top_p
        if candidate['edit'] not in ('auto', 'whole', 'diff'): raise ValueError('Ungültiges Edit-Format.')
        if not 1 <= int(candidate['budget']) <= 500: raise ValueError('Budget: 1 bis 500.')
        if not 30 <= int(candidate['timeout']) <= 86400: raise ValueError('Timeout: 30 bis 86400 Sekunden.')
        for key in ('allow_pip', 'allow_choco', 'allow_npm', 'simulation','web_search','debug_logging','sandbox',
                    'opencode_fallback','small_model_mode'):
            if type(candidate[key]) != bool: raise ValueError('Freigaben müssen boolesche Werte sein.')
        domains = candidate.get('research_domains', '')
        if not isinstance(domains, str) or len(domains) > 500:
            raise ValueError('Domainfilter: Text bis 500 Zeichen.')
        from toolforge_pilot.research import domains as clean_domains
        clean_domains(domains)
        from backend.sandbox import validate as validate_sandbox
        if isinstance(candidate.get('sandbox_ports'), list) and not all(isinstance(x, str) for x in candidate['sandbox_ports']):
            raise ValueError('Portfreigaben müssen Textwerte enthalten.')
        validate_sandbox(candidate)
        self.settings = candidate
        if 'api_key' in settings: self.api_key = str(settings['api_key']) or 'lm-studio'
        if 'remote_api_key' in settings: self.remote_key = str(settings['remote_api_key'])
        atomic_json(self.settings_path, candidate)
        # Each model has its own persistent context + temperature profile.
        profiles_file = data_root() / 'model-profiles.json'
        try: profiles = json.loads(profiles_file.read_text(encoding='utf-8'))
        except FileNotFoundError: profiles = {}
        if candidate['model']:
            profiles[self.profile_key(candidate)] = p
            atomic_json(profiles_file, profiles)
        return self.snapshot()

    @staticmethod
    def source_model_for(candidate, source, fallback=True):
        if source == 'free':
            return str(candidate.get('free_model') or (candidate.get('model') if fallback else '') or '')
        if source == 'api':
            return str(candidate.get('api_model') or (candidate.get('model') if fallback else '') or '')
        return str(candidate.get('local_model') or (candidate.get('model') if fallback else '') or '')

    def source_profile(self, source, model, rows=None):
        """Build the execution profile for one concrete source/model."""
        p = profile(self.settings)
        row = next((item for item in (rows or []) if item.get('id') == model), None)
        if row:
            limit = row.get('loaded_context') or row.get('max_context')
            if type(limit) is int and limit > 0:
                p['context_tokens'] = min(p['context_tokens'], limit)
            p['small_model'] = row.get('small_model') is True
        p['model'] = model
        p['source'] = source
        p['output_tokens'] = min(p['output_tokens'], max(256, p['context_tokens'] // 4))
        return p

    def resolve_source(self, source, model=''):
        """Resolve the model for a source and validate it against its catalog."""
        if source not in routing.SOURCE_LABELS:
            raise ValueError('Unbekannte Modellquelle.')
        model = str(model or self.source_model(source) or '')
        discovery_error = None
        try:
            rows = [row for row in self.models(source) if row.get('type') != 'embedding']
        except (ValueError, OSError) as exc:
            rows = []
            discovery_error = exc
        available = {row['id']: row for row in rows}
        if not available:
            if not model:
                if discovery_error:
                    raise ValueError(routing.source_title(source) + ': ' + str(discovery_error)) from discovery_error
                raise ValueError(routing.source_title(source) + ': keine Modelle verfügbar.')
            # Some OpenAI-compatible servers do not expose a usable catalog.
            # Keep a manually configured model usable with the saved profile.
            return {'source': source, 'model': model, 'rows': [],
                    'profile': self.source_profile(source, model, [])}
        if not model:
            loaded = [row for row in available.values() if row.get('loaded_context')]
            model = (loaded[0] if loaded else next(iter(available.values())))['id']
        if model not in available:
            # A configured model may be newer than the cached catalog (or the
            # server may hide it). The actual request remains authoritative;
            # preflight still validates candidates against the live inventory.
            return {'source': source, 'model': model, 'rows': list(available.values()),
                    'profile': self.source_profile(source, model, list(available.values()))}
        return {'source': source, 'model': model, 'rows': list(available.values()),
                'profile': self.source_profile(source, model, list(available.values()))}

    def plan_with_sources(self, goal, audit=None):
        """Create a plan through the allowed sources in preference order.

        Free-to-free model names share one quota, so the router never treats a
        switch between them as a reset. It only falls back to local or paid API
        sources that the selected preset explicitly allows.
        """
        errors = []
        for source in self.effective_sources():
            if self.cancel.is_set():
                raise ValueError('Planung gestoppt.')
            used = {'model': ''}
            try:
                prepared = self.resolve_source(source)
                used['model'] = prepared['model']
                p = prepared['profile']
                self.phase = f'Plan wird über {routing.source_title(source)} erzeugt …'
                self.emit('log', f'Planung über {routing.source_title(source)} · {prepared["model"]}.\n')
                if source == 'free':
                    def switched(old, new, exc):
                        if exc.retry_after_ms:
                            self.opencode_retry[old] = time.time() + exc.retry_after_ms / 1000
                        self.emit('log', f'OpenCode: {old} nicht verfügbar; weiter mit {new}.\n')
                    plan = opencode.chat_plan(
                        self.opencode_client(), goal, p, audit,
                        order=self.settings.get('opencode_order') or [],
                        fallback=bool(self.settings.get('opencode_fallback', True)),
                        on_switch=switched,
                        on_model=lambda name: (used.__setitem__('model', name),
                                               setattr(self, 'opencode_last_model', name)))
                else:
                    base, key = ((self.settings['api_base'], self.remote_key) if source == 'api'
                                 else (self.settings['base'], self.api_key))
                    plan = chat_plan(base, key, prepared['model'], goal, p, audit)
                self.activate_source(source, used['model'])
                self.settings.update(context_tokens=p['context_tokens'], output_tokens=p['output_tokens'],
                                     temperature=p['temperature'])
                atomic_json(self.settings_path, self.settings)
                self.plan_source = source
                return plan
            except opencode.OpenCodeError as exc:
                errors.append(f'{routing.source_title(source)}: {exc}')
                if getattr(exc, 'shared_quota', False) or exc.reason == 'rate_limit':
                    self.block_source(source, exc.retry_after_ms, str(exc))
            except (ValueError, OSError) as exc:
                errors.append(f'{routing.source_title(source)}: {exc}')
        detail = ' | '.join(errors[-3:]) or 'keine Quelle ausgewählt'
        raise ValueError('Planung fehlgeschlagen. ' + detail +
                         ' Bitte Lokal oder eine bezahlte API in der Modellquellen-Vorauswahl freigeben.')

    def models(self, source=None):
        try: saved = json.loads((data_root() / 'model-profiles.json').read_text(encoding='utf-8'))
        except FileNotFoundError: saved = {}
        source = source or self.active_source()
        if source not in routing.SOURCE_LABELS:
            raise ValueError('Unbekannte Modellquelle.')
        if source == 'free':
            rows = self.opencode_client().models(refresh=True)
            values = [{'id': row['id'], 'loaded_context': row['context'], 'max_context': row['context'],
                       'source': 'free', 'source_label': routing.source_title('free'), 'type': 'chat',
                       'name': row['name'], 'family': row['family'], 'variants': row['variants'],
                       'free': True, 'small_model': False, 'size_bytes': None,
                       'quantization': None, 'selected_variant': ''} for row in rows]
            key = self.profile_key()
            for item in values:
                item['saved_profile'] = saved.get('opencode|' + item['id'])
                if not item['saved_profile'] and key.endswith('|' + item['id']):
                    item['saved_profile'] = saved.get(key)
            return values
        if source == 'api':
            rows = self.api_studio().inventory(refresh=True)
            values = [{'id': row['key'], 'loaded_context': None,
                       'max_context': row.get('max_context_length'), 'source': 'api',
                       'source_label': routing.source_title('api'), 'type': 'chat',
                       'name': row.get('name') or row['key'], 'free': False, 'small_model': False,
                       'size_bytes': None, 'quantization': row.get('quantization'),
                       'selected_variant': row.get('selected_variant', '')} for row in rows]
            base_key = 'api|' + self.settings.get('api_base', '').rstrip('/') + '|'
            for item in values:
                item['saved_profile'] = saved.get(base_key + item['id'])
            return values
        values = discover_models(self.settings['base'], self.api_key)
        for item in values:
            item['source'] = 'local'
            item['source_label'] = routing.source_title('local')
            item['saved_profile'] = saved.get(self.settings['base'].rstrip('/') + '|' + item['id'])
        return values

    def opencode_status(self, data=None):
        start = bool((data or {}).get('start'))
        try:
            client = self.opencode_client()
        except ValueError as exc:
            return {'available': False, 'models': [], 'order': [], 'error': str(exc)}
        return client.status(start=start)

    def bridge_base(self):
        base = (os.environ.get('TOOLFORGE_BRIDGE_BASE') or 'http://127.0.0.1:8000').rstrip('/')
        ident = urllib.parse.quote(self.project_id or 'unknown', safe='')
        return base + '/api/projects/' + ident + '/opencode/v1'

    def bridge_models(self):
        """List models from every source the active preset allows."""
        data = []
        seen = set()
        errors = []
        for source in self.effective_sources(include_blocked=True):
            try:
                rows = self.models(source)
            except (ValueError, OSError) as exc:
                errors.append(f'{routing.source_title(source)}: {exc}')
                continue
            for row in rows:
                if row.get('type') == 'embedding' or row['id'] in seen:
                    continue
                seen.add(row['id'])
                data.append({'id': row['id'], 'object': 'model', 'created': 0,
                             'owned_by': routing.source_provider(source),
                             'x_toolforge_source': source})
        if not data:
            raise ValueError('Keine Modellquelle verfügbar. ' + ' '.join(errors))
        return {'object': 'list', 'data': data}

    def bridge_chat(self, payload):
        if not isinstance(payload, dict):
            raise ValueError('Ungültige OpenAI-Anfrage.')
        now = time.time()
        self.opencode_retry = {name: until for name, until in self.opencode_retry.items() if until > now}
        self.blocked_sources = {name: until for name, until in self.blocked_sources.items() if until > now}
        errors = []
        sources = list(self.effective_sources())
        if not sources:
            detail = self.blocked_sources_message()
            raise opencode.OpenCodeError('Keine Modellquelle verfügbar. ' + detail, status=429,
                                         reason='rate_limit')
        # Keep the accepted/active source first, then fall back within the
        # preset order. The preset, not the model name, decides whether a
        # fallback to local or paid API is allowed.
        active = self.active_source()
        if active in sources:
            sources.remove(active)
            sources.insert(0, active)
        for source in sources:
            try:
                if source == 'free':
                    client = self.opencode_client()
                    skip = set(self.opencode_retry)
                    def switched(old, new, exc):
                        if exc.retry_after_ms:
                            self.opencode_retry[old] = time.time() + exc.retry_after_ms / 1000
                        self.emit('log', f'OpenCode: {old} nicht verfügbar; weiter mit {new}.\n')
                    result = opencode.completion(client, payload,
                                                 order=self.settings.get('opencode_order') or [],
                                                 fallback=bool(self.settings.get('opencode_fallback', True)),
                                                 skip=skip, on_switch=switched)
                    self.opencode_last_model = result.get('model', '')
                elif source == 'api':
                    result = self.completion_via_source(payload, 'api')
                else:
                    result = self.completion_via_source(payload, 'local')
                if source != self.active_source():
                    self.emit('log', f'Modellquelle gewechselt: {routing.source_title(source)} übernimmt den laufenden Auftrag.\n')
                    self.activate_source(source, self.source_model(source))
                self.opencode_last_model = str(result.get('model') or self.source_model(source))
                self.publish('snapshot', {'phase': self.phase, 'busy': self.busy})
                return result
            except opencode.OpenCodeError as exc:
                errors.append(f'{routing.source_title(source)}: {exc}')
                if getattr(exc, 'shared_quota', False) or exc.reason == 'rate_limit':
                    self.block_source(source, exc.retry_after_ms, str(exc))
            except (ValueError, OSError) as exc:
                errors.append(f'{routing.source_title(source)}: {exc}')
        raise opencode.OpenCodeError('Keine Ausweichquelle konnte die Anfrage beantworten. ' + '; '.join(errors[-3:]),
                                     status=502, reason='all_sources_failed')

    def completion_via_source(self, payload, source):
        model = self.source_model(source)
        if not model:
            if source == 'api':
                rows = self.api_studio().inventory(refresh=True)
                if not rows:
                    raise ValueError('Kein API-Modell konfiguriert.')
                model = rows[0]['key']
            else:
                raise ValueError('Kein lokales Modell ausgewählt.')
        body = json.loads(json.dumps(payload))
        body['model'] = model
        body['stream'] = False
        base, key = ((self.settings['api_base'], self.remote_key) if source == 'api'
                     else (self.settings['base'], self.api_key))
        result = routing.post_completion(base, key, body, int(self.settings.get('timeout', 900)))
        if not isinstance(result, dict) or not result.get('choices'):
            raise ValueError('Ausweichquelle lieferte keine gültige Chat-Antwort.')
        result.setdefault('model', model)
        return result

    def preview_plan(self, plan):
        plan = validate_plan(plan)
        return planning.diff_plans(self.store.state['plan'] if self.store.state else None, plan, self.store.state)

    def apply_plan(self, plan, confirm=False):
        if self.busy: raise ValueError('Plan erst nach dem laufenden Vorgang ändern.')
        plan = validate_plan(plan)
        preview = planning.diff_plans(self.store.state['plan'] if self.store.state else None, plan, self.store.state)
        if preview['requires_confirmation'] and not confirm:
            raise ValueError('Die Änderung betrifft bereits geprüfte Teile oder entfernt Prüfungen. '
                             'Zuerst die Plan-Vorschau prüfen und die Übernahme ausdrücklich bestätigen.')
        backup = planning.backup_plan(self.store.project, self.store.state, 'Planübernahme')
        with self.answer_lock:
            self.pending_answers.clear()
            atomic_json(self.store.log_root.parent / 'pending-answers.json', {})
        self.store.set_plan(plan,preserve=True)
        self.store.state['last_plan_backup'] = str(backup) if backup else None
        self.store.save(); self.error = ''; self.phase = 'Plan gespeichert und aktiv.'
        self.publish('plan')
        return self.snapshot()

    def publish(self, event, data=None):
        hub = getattr(self, 'hub', None)
        if hub:
            hub.publish_session(self.ident, event, data or {'phase': self.phase, 'busy': self.busy})
        service = getattr(self, 'service', None)
        if service:
            service.publish_questions()

    def emit(self, kind, value):
        if kind == 'log':
            for key in (self.api_key, self.remote_key):
                if key and key != 'lm-studio': value = value.replace(key, '[REDACTED]')
            self.logs = (self.logs + value)[-100000:]
        elif kind == 'state': self.phase = value.get('message', '')
        self.publish(kind if kind in ('log', 'state') else 'snapshot', {'phase': self.phase})

    def background(self, function, model_lock=True):
        with self.guard:
            if self.busy: raise ValueError('Es läuft bereits ein Vorgang.')
            self.error = ''
            self.cancel.clear(); self.pause_request.clear()
            self.running = True
            lock_needed = model_lock and 'local' in self.effective_sources(include_blocked=True)
            def run():
                operation = function
                while True:
                    acquired = MODEL_LOCK.acquire(blocking=False) if lock_needed else False
                    try:
                        if lock_needed and not acquired: raise ValueError('Ein anderes Projekt nutzt gerade den Modellserver. Später erneut starten.')
                        operation()
                    except Exception as exc:
                        if self.settings.get('debug_logging'):
                            import traceback
                            from toolforge_pilot.diagnostics import record
                            record(self.store.project,'session_exception',traceback.format_exc(),[self.api_key, self.remote_key])
                        self.error = str(exc); self.phase = 'Vorgang angehalten: ' + str(exc)
                        self.emit('log', '\nFEHLER: ' + str(exc) + '\n')
                    finally:
                        if acquired: MODEL_LOCK.release()
                        self.scan = self.scan_project()
                    with self.guard:
                        with self.answer_lock: pending = bool(self.pending_answers)
                        if pending and self.engine and self.store.state['status']=='WAITING' and self.remaining_budget>0 and not self.cancel.is_set() and not self.pause_request.is_set():
                            def resume():
                                self.engine.run(self.remaining_budget)
                                self.remaining_budget -= self.store.state.get('session_used',0)
                            operation = resume
                        else:
                            self.running = False
                            break
                self.publish('snapshot', {'phase': self.phase, 'busy': False})
            self.worker = threading.Thread(target=run, daemon=True); self.worker.start()
        return self.snapshot()

    def studio(self, preflight=False):
        if self.provider() == 'opencode':
            return opencode.OpenCodeStudio(
                self.opencode_client(),
                fallback=False if preflight else bool(self.settings.get('opencode_fallback', True)),
                order=self.settings.get('opencode_order') or [], cancel=self.cancel,
                timeout=int(self.settings['timeout']))
        if self.provider() == 'api':
            return self.api_studio(preflight)
        return self.local_studio(preflight)

    def preflight_options(self, kind='coding'):
        studio = self.preflight_studio()
        result = suggest(studio.inventory(), kind)
        result['sources'] = studio.alternatives()
        result['blocked'] = {source: until for source, until in self.blocked_sources.items()
                             if until > time.time()}
        result['blocked_message'] = self.blocked_sources_message()
        result['prefix'] = studio.prefix
        return result

    def run_preflight(self, data):
        goal = str(data.get('goal', '')).strip()
        candidates = data.get('candidates', [])
        if not isinstance(candidates, list) or not all(isinstance(x, str) for x in candidates):
            raise ValueError('Kandidaten müssen eine Liste von Modellschlüsseln sein.')
        studio = self.preflight_studio()
        try:
            available = {row['key'] for row in studio.inventory()}
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        judge = str(data.get('judge', ''))
        if judge not in available:
            if studio.is_blocked(judge):
                raise ValueError('Das Auswertungsmodell ist vorübergehend nicht verfügbar. ' + self.blocked_sources_message())
            raise ValueError('Auswertungsmodell ist nicht verfügbar: ' + judge)
        kept = []
        removed = []
        for candidate in candidates:
            if candidate in available:
                kept.append(candidate)
            elif studio.is_blocked(candidate):
                removed.append(candidate)
            else:
                raise ValueError('Kandidat ist nicht verfügbar: ' + candidate)
        if not kept:
            raise ValueError('Alle Kandidaten sind vorübergehend nicht verfügbar. ' + self.blocked_sources_message())
        prefix = studio.prefix

        def save(report):
            report['base'] = self.provider_signature()
            report['provider'] = self.provider()
            report['source_mode'] = self.source_mode()
            report['preference'] = self.preference()
            report['sources'] = list(self.effective_sources(include_blocked=True))
            report['source_prefix'] = prefix
            report['skipped_sources'] = list(dict.fromkeys(removed + list(report.get('skipped_sources', []))))
            self.preflight = json.loads(json.dumps(report))
            atomic_json(self.preflight_path, report)
            history = self.store.log_root.parent / 'preflight-history'
            history.mkdir(exist_ok=True)
            atomic_json(history / (run_id + '.json'), report)

        def phase(text):
            self.phase = text
            self.emit('log', text + '\n')

        run_id = str(time.time_ns())

        def work():
            self.remaining_budget = 0
            save({'status':'running','accepted':False,'goal':goal,'samples':[],
                  'note':'Vergleich wird vorbereitet.'})
            try:
                evaluate(self.preflight_studio(), goal, kept, judge,
                         data.get('context_tokens', 20000), str(data.get('kind', 'coding')),
                         data.get('two_temperatures', True) is True, phase, save)
            except Exception as exc:
                self.preflight.update(status='error', error=str(exc), accepted=False)
                save(self.preflight)
                raise
            self.phase = 'Vorabcheck fertig. Arbeitsproben prüfen und Empfehlung übernehmen.'
        return self.background(work)

    def _adopt_alternative(self, report, source=None, model=None):
        alternatives = report.get('alternatives') or []
        if not alternatives:
            return False
        prefix = bool(report.get('source_prefix'))
        for row in alternatives:
            alt_source, alt_model = routing.split_key(row.get('model', ''), prefix)
            alt_source = alt_source or row.get('source') or self.active_source()
            if source and alt_source != source:
                continue
            if model and alt_model != model and row.get('model') != model:
                continue
            self.activate_source(alt_source, alt_model)
            self.settings.update(temperature=row['temperature'],
                                 context_tokens=row['context_tokens'],
                                 output_tokens=min(2048, max(256, row['context_tokens'] // 4)))
            report['accepted_settings'] = {
                'provider': routing.source_provider(alt_source), 'source': alt_source,
                'model': alt_model, 'temperature': row['temperature'],
                'context_tokens': row['context_tokens'],
                'output_tokens': min(2048, max(256, row['context_tokens'] // 4))}
            report['accepted'] = True
            report['base'] = self.provider_signature()
            atomic_json(self.preflight_path, report)
            atomic_json(self.settings_path, self.settings)
            self.emit('log', f'Ausweichquelle aus dem Vorabcheck übernommen: {routing.source_title(alt_source)} · {alt_model}.\n')
            return True
        return False

    def accept_preflight(self, goal):
        report = self.preflight
        if not report or report.get('status') != 'ready': raise ValueError('Keine gültige Empfehlung vorhanden.')
        if report['goal_signature'] != signature(goal): raise ValueError('Aufgabe geändert. Vorabcheck erneut ausführen.')
        if report['base'] != self.provider_signature(): raise ValueError('Modellquelle geändert. Vorabcheck erneut ausführen.')
        recommendation = dict(report['recommendation'])
        prefix = bool(report.get('source_prefix'))
        source, raw_model = routing.split_key(recommendation.get('model', ''), prefix)
        source = source or recommendation.get('source') or self.active_source()

        def work():
            self.phase = 'Empfohlenes Modell und Kontext laden …'
            studio = self.preflight_studio()
            try:
                studio.switch(recommendation['model'], recommendation['context_tokens'])
                actual = getattr(studio, 'actual_context', None)
                if type(actual) is not int: actual = recommendation['context_tokens']
                self.activate_source(source, raw_model)
                values = {'provider': routing.source_provider(source), 'source': source,
                          'model': raw_model, 'temperature': recommendation['temperature'],
                          'context_tokens': actual,
                          'output_tokens': min(recommendation['output_tokens'], max(256, actual // 4))}
                self.settings.update(values)
                atomic_json(self.settings_path, self.settings)
                report['recommendation']['context_tokens'] = actual
                report['recommendation']['source'] = source
                report['accepted_settings'] = values
                report['accepted'] = True
                # Acceptance can select a previously empty per-source model.
                # Keep the configuration signature in sync so a later check
                # validates the accepted profile instead of the pre-accept one.
                report['base'] = self.provider_signature()
                atomic_json(self.preflight_path, report)
                self.phase = f'Empfehlung übernommen: {routing.source_title(source)} · {raw_model}. Geprüfter Kontext: {actual} Tokens.'
            except Exception:
                report['accepted'] = False
                atomic_json(self.preflight_path, report)
                studio.unload()
                raise
        return self.background(work)

    def check_preflight(self, goal=None):
        report = self.preflight
        if not report: return  # Existing projects retain their manual workflow.
        if not report.get('accepted') or report.get('status') != 'ready':
            raise ValueError('Vorabcheck abschließen und Empfehlung übernehmen.')
        if goal is not None and signature(goal) != report['goal_signature']:
            raise ValueError('Aufgabe geändert. Vorabcheck erneut ausführen.')
        if self.provider_signature() != report['base']:
            raise ValueError('Modellquelle geändert. Vorabcheck erneut ausführen.')
        expected = dict(report['accepted_settings'])
        source = expected.get('source') or routing.provider_source(expected.get('provider', self.provider()))
        model = expected.get('model') or self.source_model(source)
        if self.active_source() != source:
            # A fallback source may already have been measured in the same
            # preflight. Adopt its best valid sample instead of forcing a full rerun.
            if not self._adopt_alternative(report, self.active_source(), self.source_model() or None):
                raise ValueError('Aktive Modellquelle weicht von der Empfehlung ab. Empfehlung erneut übernehmen oder '
                                 'Vorabcheck mit passender Vorauswahl wiederholen.')
            expected = dict(report['accepted_settings'])
            source = expected.get('source')
            model = expected['model']
        if self.source_model() != model:
            if not self._adopt_alternative(report, source, self.source_model() or None):
                raise ValueError('Einstellungen weichen von der Empfehlung ab. Empfehlung erneut übernehmen oder '
                                 'Vorabcheck wiederholen.')
            expected = dict(report['accepted_settings'])
            source = expected.get('source')
            model = expected['model']
        for key, value in expected.items():
            if key in ('source', 'provider'):
                continue
            if self.settings.get(key) != value:
                raise ValueError('Einstellungen weichen von der Empfehlung ab. Empfehlung erneut übernehmen oder '
                                 'Vorabcheck wiederholen.')
        if source == 'free':
            if self.source_blocked('free'):
                if not self._adopt_alternative(report, 'local') and not self._adopt_alternative(report, 'api'):
                    raise ValueError('Das Free-Tageslimit ist erschöpft. Vorabcheck mit „Free & Lokal“ oder '
                                     '„Free & API“ wiederholen bzw. auf Lokal/API wechseln.')
                expected = report['accepted_settings']; source = expected['source']; model = expected['model']
            rows = {row['id']: row for row in self.opencode_client().models(refresh=True)}
            if model not in rows:
                raise ValueError('Freies OpenCode-Modell nicht mehr verfügbar. Vorabcheck wiederholen.')
            if expected['context_tokens'] > rows[model]['context']:
                raise ValueError('Kontext überschreitet das Modelllimit. Vorabcheck wiederholen.')
            return
        if source == 'api':
            try:
                self.api_studio().switch(model, expected['context_tokens'])
            except ValueError as exc:
                raise ValueError('API-Modell/Kontext nicht bestätigt: ' + str(exc)) from exc
            return
        instances = self.studio().instances()
        if (len(instances) != 1 or instances[0]['id'] != model
                or not context_compatible(expected['context_tokens'], instances[0].get('config',{}).get('context_length'))):
            raise ValueError('Geladenes Modell/Kontext geändert. Empfehlung erneut übernehmen.')

    def generate(self, goal):
        if not goal.strip(): raise ValueError('Bitte ein Projektziel eingeben.')
        def work():
            self.remaining_budget = 0
            self.check_preflight(goal)
            self.phase = 'Plan wird aus der Beschreibung erzeugt …'
            folder = self.store.log_root.parent / 'planning'; folder.mkdir(exist_ok=True)
            def audit(attempt, raw, error):
                atomic_json(folder / (str(time.time_ns()) + '.json'), {'attempt':attempt+1,'response':raw,'error':error})
                self.phase = ('Planantwort wird korrigiert: ' + error) if error else 'Plan validiert; speichern …'
            plan = self.plan_with_sources(goal, audit)
            planning.backup_plan(self.store.project, self.store.state, 'Vor Planerzeugung')
            with self.answer_lock:
                self.pending_answers.clear()
                atomic_json(self.store.log_root.parent / 'pending-answers.json', {})
            self.store.set_plan(plan)
            self.phase = 'Plan erstellt, versioniert und aktiv. Bitte prüfen; Start erfolgt erst auf Knopfdruck.'
        return self.background(work)

    def start(self, answer=''):
        if not self.store.state: raise ValueError('Zuerst einen Aufgabenplan erstellen oder laden.')
        def work():
            self.apply_pending_improvements()
            self.phase = 'Projektstand und Modellprofil vergleichen …'
            s = dict(self.settings)
            if s['simulation']:
                plan = json.loads((APP_ROOT / 'examples' / 'demo_plan.json').read_text(encoding='utf-8'))
                if self.store.state['plan'] != plan: raise ValueError('Simulation benötigt den unveränderten Beispielplan.')
                adapter = DemoAdapter()
            else:
                self.check_preflight()
                s = dict(self.settings)
                source = self.active_source()
                prepared = self.resolve_source(source)
                model = prepared['model']
                p = prepared['profile']
                p['provider'] = routing.source_provider(source)
                adapted, changed = adapt_plan(self.store.state['plan'], self.store.project, p, completed={k for k,v in self.store.state['tasks'].items() if v['status']=='VERIFIED'})
                if changed:
                    self.store.set_plan(adapted, preserve=True)
                    self.emit('log', 'Modellspezifische Planversion gespeichert: ' + self.store.state['plan_file'] + '\n')
                p['top_p'] = float(s.get('top_p', .95))
                edit = effective_edit(s['edit'], p, bool(s.get('small_model_mode')))
                if edit != s['edit']:
                    self.emit('log', 'Kleines Modell: ganze Dateien werden bevorzugt (Edit-Format whole).\n')
                multi_source = len(self.effective_sources(include_blocked=True)) > 1
                if source == 'free' or multi_source:
                    base, key = self.bridge_base(), 'public'
                    if source == 'free':
                        self.emit('log', 'OpenCode Free: Aider nutzt die lokale Brücke. Bei erschöpfter gemeinsamer '
                                          'Free-Quote wird nur auf Lokal/API ausgewichen, nicht auf ein anderes Free-Modell.\n')
                    else:
                        self.emit('log', 'Mehrquellen-Betrieb: Aider nutzt die lokale Brücke für den Ausweichbetrieb.\n')
                elif source == 'api':
                    base, key = s['api_base'], self.remote_key
                    self.emit('log', 'Bezahlte API: Aider spricht die konfigurierte OpenAI-kompatible API direkt an.\n')
                else:
                    base, key = s['base'], self.api_key
                self.emit('log', f'Aktive Modellquelle: {routing.source_title(source)} · {model} · '
                                  f'{p["context_tokens"]} Tokens.\n')
                adapter = AiderAdapter(s['aider_python'], base, key, model, edit, int(s['timeout']), p)
                self.phase = 'Aider-CLI prüfen …'
                self.emit('log', adapter.probe() + '\n')
            if self.cancel.is_set(): self.phase = 'Vor dem Agentenstart gestoppt.'; return
            self.engine = Engine(self.store, adapter, s['python'], self.emit, s)
            if self.pause_request.is_set(): self.engine.pause.set()
            if answer.strip(): self.engine.answer(answer)
            self.engine.apply_answers = self.apply_answers
            self.engine.before_cycle = self.before_cycle
            self.store.state['mode'] = 'simulation' if s['simulation'] else 'aider'
            remaining = int(s['budget'])
            self.remaining_budget = remaining
            while remaining > 0:
                self.engine.run(remaining)
                remaining -= self.store.state.get('session_used', 0)
                self.remaining_budget = remaining
                with self.answer_lock: more = bool(self.pending_answers)
                if not more or self.cancel.is_set() or self.pause_request.is_set() or self.store.state['status'] in ('ERROR','DONE','BUDGET'): break
        return self.background(work)

    def submit_answer(self, task_id, answer):
        if not answer.strip(): raise ValueError('Bitte eine Antwort eingeben.')
        if not self.store.state or task_id not in self.store.state['tasks'] or not self.store.state['tasks'][task_id].get('question'):
            raise ValueError('Keine offene Rückfrage zu dieser Aufgabe.')
        with self.guard:
            with self.answer_lock:
                self.pending_answers[task_id] = answer
                atomic_json(self.store.log_root.parent / 'pending-answers.json', self.pending_answers)
            was_busy = self.busy
        if not was_busy: return self.start()
        return self.snapshot()

    def apply_answers(self):
        with self.answer_lock:
            for ident, text in list(self.pending_answers.items()):
                if ident in self.store.state['tasks'] and self.store.state['tasks'][ident].get('question'):
                    self.engine.answer(text, ident)
                del self.pending_answers[ident]
            atomic_json(self.store.log_root.parent / 'pending-answers.json', self.pending_answers)

    def runtime_options(self, data):
        if not data or set(data)-{'web_search','debug_logging'} or any(type(v)!=bool for v in data.values()):
            raise ValueError('Nur boolesche Recherche-/Diagnoseoptionen sind während eines Laufs änderbar.')
        with self.guard:
            self.settings.update(data)
            atomic_json(self.settings_path,self.settings)
        return self.snapshot()

    def before_cycle(self):
        if self.engine:
            for key in ('web_search','debug_logging'):
                self.engine.policy[key]=self.settings[key]
        self.apply_pending_improvements()

    def cancel_pause(self):
        self.pause_request.clear()
        if self.engine:self.engine.pause.clear()
        if self.running:self.phase='Pause zurückgenommen; Lauf wird fortgesetzt.'
        return self.snapshot()

    def stop(self, immediate=False):
        if self.busy:
            (self.cancel if immediate else self.pause_request).set()
            if self.engine: (self.engine.stop if immediate else self.engine.pause).set()
            self.phase = 'Stoppen angefordert.' if immediate else 'Pause nach dem Durchlauf angefordert.'
        else: raise ValueError('Kein laufender Agentenauftrag. Modellabfragen enden nach ihrem Timeout.')
        return self.snapshot()

    def open_opencode_console(self):
        """Open an interactive OpenCode terminal for this project on demand."""
        return opencode.open_console(self.store.project)

    def open_logs(self):
        path = str(self.store.log_root)
        if os.name == 'nt': os.startfile(path)
        elif sys.platform == 'darwin': subprocess.Popen(['open', path])
        else: subprocess.Popen(['xdg-open', path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {'path': path}

    # --- V1.1: incremental analysis, benchmarks, acceptance, research, operations ---

    def refresh_index(self, force=False):
        self.index = project_index.refresh(self.store.project, force is True)
        self.scan = self.scan_project()
        self.publish('index', {'summary': self.index.get('summary', {})})
        return project_index.status(self.store.project)

    def analysis_context(self, data=None):
        data = data or {}
        budget = data.get('max_chars', 40000)
        if type(budget) != int or not 4000 <= budget <= 400_000:
            raise ValueError('Analyseumfang: 4.000 bis 400.000 Zeichen.')
        paths = data.get('paths', [])
        if not isinstance(paths, list) or not all(isinstance(name, str) for name in paths):
            raise ValueError('Pfade müssen eine Liste relativer Dateinamen sein.')
        result = project_index.context(self.store.project, budget, paths)
        self.assistance['coverage'] = result['coverage']
        self.save_assistance()
        return result

    def run_benchmark(self, data):
        data = data or {}
        model = str(data.get('model') or self.settings.get('model') or '')
        if not model:
            raise ValueError('Bitte ein installiertes Modell für die Messreihe wählen.')
        contexts = data.get('contexts', [self.settings.get('context_tokens', 20000)])
        if isinstance(contexts, int):
            contexts = [contexts]
        if not isinstance(contexts, list) or not all(type(value) == int for value in contexts):
            raise ValueError('Kontextgrößen müssen Zahlen sein.')
        repeats = data.get('repeats', 2)
        if type(repeats) != int:
            raise ValueError('Wiederholungen müssen eine ganze Zahl sein.')
        kind = str(data.get('kind', 'coding'))
        judge = str(data.get('judge', ''))
        goal = str(data.get('goal', '')).strip() or 'Repräsentative Arbeitsprobe für ' + kind
        force = data.get('force') is True
        two = data.get('two_temperatures') is True

        def save(report):
            self.benchmark = json.loads(json.dumps(report))
            atomic_json(self.store.log_root.parent / 'benchmark.json', report)

        def work():
            self.remaining_budget = 0
            self.phase = 'Empirische Messreihe wird vorbereitet …'
            benchmarks.measure(self.studio(preflight=True), goal, model, judge, kind, contexts, repeats, two,
                               lambda text: self.emit('log', text + '\n'), save, force)
            self.phase = 'Messreihe fertig. Gemessene Empfehlung prüfen und bewusst übernehmen.'
        return self.background(work)

    def benchmark_cache(self):
        return {'hardware': benchmarks.hardware_info(),
                'fingerprint': benchmarks.hardware_fingerprint(),
                'rows': benchmarks.cache_rows(),
                'current': self.benchmark,
                'caveat': benchmarks.recommendation_caveat(self.benchmark or {})}

    def research(self, data):
        data = data or {}
        from toolforge_pilot.research import search
        query = str(data.get('query', '')).strip()
        if not query:
            raise ValueError('Bitte einen Suchbegriff eingeben.')
        task_id = str(data.get('task_id') or 'manual')
        error = str(data.get('error', ''))
        domains = data.get('domains', self.settings.get('research_domains', ''))
        force = data.get('force') is True

        def work():
            self.remaining_budget = 0
            self.phase = 'Recherche mit Quellenprüfung läuft …'
            entry = search(self.store.project, query, self.settings, task_id, error, domains, force)
            self.research_result = entry
            self.phase = ('Recherche fertig: ' + str(len(entry.get('results', []))) + ' geprüfte Quellen.'
                          if not entry.get('error') else 'Recherche fehlgeschlagen: ' + entry['error'])
        return self.background(work, model_lock=False)

    def research_cache(self):
        from toolforge_pilot.research import cache_rows
        return {'current': self.research_result, 'rows': cache_rows(self.store.project),
                'domains': self.settings.get('research_domains', '')}

    def run_acceptance(self, data=None):
        data = data or {}
        if data.get('kind') not in (None, '', 'declared'):
            raise ValueError('Anwendungsabnahme nutzt die im Plan deklarierten Szenarien.')

        def work():
            self.remaining_budget = 0
            self.phase = 'Anwendungsabnahme mit echten CLI-/HTTP-/Browser-Szenarien läuft …'
            report = scenarios.run(self.store.project, self.settings['python'], self.cancel,
                                   lambda text: self.emit('log', text), self.store.state)
            self.acceptance = report
            self.phase = ('Anwendungsabnahme bestanden.' if report['passed']
                          else 'Anwendungsabnahme nicht bestanden; Szenarienprotokoll prüfen.')
        return self.background(work, model_lock=False)

    def review_acceptance(self, data):
        report = scenarios.mark_reviewed(self.store.project, str((data or {}).get('note', '')))
        self.acceptance = report
        self.phase = 'Teständerungen der Anwendungsabnahme gesondert geprüft.'
        self.publish('acceptance')
        return report

    def rotate_logs(self):
        result = operations.rotate_diagnostics(self.store.project)
        self.publish('operations', result)
        return result

    def restore_backup(self, data):
        if self.busy:
            raise ValueError('Sicherung erst nach dem laufenden Vorgang wiederherstellen.')
        backup = planning.load_backup(self.store.project, str((data or {}).get('file', '')))
        current = planning.backup_plan(self.store.project, self.store.state, 'Vor Wiederherstellung')
        plan = backup['plan']
        self.store.set_plan(plan)
        restored = {}
        for task in plan['tasks']:
            row = backup.get('tasks', {}).get(task['id'], {})
            status = row.get('status') if row.get('status') in ('OPEN', 'RECHECK', 'VERIFIED', 'WAITING') else 'OPEN'
            restored[task['id']] = {'status': status, 'attempts': int(row.get('attempts', 0) or 0),
                                    'failures': int(row.get('failures', 0) or 0), 'answer': str(row.get('answer', '')),
                                    'error': str(row.get('error', '')), 'question': row.get('question')}
        self.store.state['tasks'] = restored
        self.store.state['status'] = 'READY'
        self.store.state['message'] = 'Plan aus Sicherung wiederhergestellt; Prüfnachweise werden beim Fortsetzen erneut verifiziert.'
        self.store.state['last_plan_backup'] = str(current) if current else None
        self.store.save()
        self.scan = self.scan_project()
        self.publish('plan')
        return {'restored': True, 'file': str((data or {}).get('file', '')), 'reason': backup.get('reason', ''),
                'plan_version': plan.get('version'), 'previous_backup': str(current) if current else None}

    def export_preset(self, data):
        data = data or {}
        lock = environments.lock_report(self.settings.get('aider_python'))
        payload = environments.export_preset(self.settings, self.store.state, lock, str(data.get('name', 'preset')))
        self.publish('environment')
        return {'preset': payload, 'file': payload['name'] + '.json'}

    def import_preset(self, data):
        data = data or {}
        payload = data.get('preset')
        if payload is None:
            name = str(data.get('file', ''))
            if not name or not all(part not in name for part in ('/', '\\')) or not name.endswith('.json'):
                raise ValueError('Preset-Dateiname fehlt oder ist ungültig.')
            path = data_root() / 'presets' / name
            if not path.is_file():
                raise ValueError('Preset nicht gefunden.')
            payload = json.loads(path.read_text(encoding='utf-8'))
        result = environments.import_preset(payload)
        applied = data.get('apply', True) is True
        if applied:
            self.configure({key: value for key, value in result['settings'].items() if key in DEFAULTS})
            self.phase = 'Preset importiert und Einstellungen übernommen.'
        return {'imported': result, 'applied': applied, 'snapshot': self.snapshot() if applied else None}

    def environment_lock(self):
        lock = environments.lock_report(self.settings.get('aider_python'))
        self.publish('environment')
        return lock

    def sandbox_status(self):
        from backend import sandbox
        return sandbox.status(self.store.project, self.settings)

    def sandbox_build(self):
        from backend import sandbox

        def work():
            self.remaining_budget = 0
            self.phase = 'Projekt-Image wird gebaut; Docker-Digest wird protokolliert …'
            result = sandbox.build(self.store.project, self.settings['python'], self.cancel,
                                   lambda text: self.emit('log', text), self.settings)
            if result.get('code') or result.get('reason'):
                raise ValueError('Image-Build fehlgeschlagen: ' + str(result.get('reason') or result.get('output', ''))[-1500:])
            self.phase = 'Projekt-Image gebaut; Digest im Docker-Lock gespeichert.'
        return self.background(work, model_lock=False)

    def sandbox_remove_image(self):
        from backend import sandbox

        def work():
            self.remaining_budget = 0
            result = sandbox.remove_image(self.store.project, self.cancel,
                                          lambda text: self.emit('log', text))
            if result.get('code') or result.get('reason'):
                raise ValueError('Image konnte nicht entfernt werden: ' + str(result.get('output', ''))[-1000:])
            self.phase = 'Projekt-Image entfernt.'
        return self.background(work, model_lock=False)

    def sandbox_network(self, data):
        from backend import sandbox
        action = str((data or {}).get('action', 'ensure'))
        name = str((data or {}).get('name') or self.settings.get('sandbox_network', ''))
        if not name:
            raise ValueError('Kein Sandbox-Netzwerk angegeben.')

        def work():
            self.remaining_budget = 0
            if action == 'remove':
                result = sandbox.remove_network(self.store.project, name, self.cancel,
                                                lambda text: self.emit('log', text))
                self.phase = 'Sandbox-Netzwerk entfernt.'
            elif action == 'ensure':
                result = sandbox.ensure_network(self.store.project, name, self.cancel,
                                                lambda text: self.emit('log', text))
                self.phase = 'Sandbox-Netzwerk bereit.'
            else:
                raise ValueError('Netzwerkaktion: ensure oder remove.')
            if result.get('code') or result.get('reason'):
                raise ValueError('Netzwerkaktion fehlgeschlagen: ' + str(result.get('output', ''))[-1000:])
        return self.background(work, model_lock=False)

    def sandbox_package(self, data):
        from backend import sandbox
        data = data or {}
        manager = str(data.get('manager', 'pip'))
        name = str(data.get('name', ''))
        version = str(data.get('version', ''))

        def work():
            self.remaining_budget = 0
            self.phase = 'Container-Paket wird in ein abgeleitetes Projekt-Image installiert …'
            result = sandbox.install_package(self.store.project, manager, name, version, self.cancel,
                                             lambda text: self.emit('log', text))
            if result.get('code') or result.get('reason'):
                raise ValueError('Paketinstallation im Container fehlgeschlagen: ' + str(result.get('output', ''))[-1500:])
            self.phase = 'Container-Paket installiert; neuer Image-Digest protokolliert.'
        return self.background(work, model_lock=False)

    def export_project(self):
        return operations.export_project(self.store.project)

    def import_project(self, data):
        if self.busy:
            raise ValueError('Import erst nach dem laufenden Vorgang.')
        data = data or {}
        source = Path(str(data.get('path', ''))).expanduser()
        if not source.is_file():
            raise ValueError('Transfer-Archiv nicht gefunden.')
        result = operations.import_project(source, self.store.project, data.get('overwrite') is True)
        self.index = project_index.refresh(self.store.project, True)
        self.scan = self.scan_project()
        self.publish('snapshot')
        return result

    def close(self):
        self.cancel.set()
        if self.engine: self.engine.stop.set()
        if self.worker: self.worker.join(timeout=12)
        if not self.busy: self.store.close()


class PilotService:
    def __init__(self):
        self.sessions = {}; self.guard = threading.Lock()
        self.hub = EventHub()
        self.question_lock = threading.Lock()
        self.questions_at = 0.0

    def get(self, path, project_id=None):
        path = str(Path(path).resolve())
        with self.guard:
            session = self.sessions.get(path)
            if session is None:
                session = Session(path, project_id)
                session.hub = self.hub
                session.service = self
                session.ident = hashlib.sha256(os.path.normcase(path).encode()).hexdigest()[:24]
                self.sessions[path] = session
            elif project_id:
                session.project_id = project_id
            return session

    def question_digest(self):
        """Global questions from every open project cockpit (read-only snapshot)."""
        digest = []
        with self.guard:
            sessions = list(self.sessions.values())
        for session in sessions:
            state = session.store.state
            if not state:
                continue
            for task in (state.get('plan') or {}).get('tasks', []):
                row = (state.get('tasks') or {}).get(task['id'], {})
                if row.get('question'):
                    digest.append({'id': session.ident, 'folder': str(session.store.project),
                                   'project': session.store.project.name, 'task': task['id'],
                                   'title': task.get('title', ''),
                                   'question': str(row['question'])[:600],
                                   'status': state.get('status'),
                                   'at': row.get('question_at') or state.get('updated_at')})
        return digest

    def publish_questions(self, force=False):
        now = time.monotonic()
        with self.question_lock:
            if not force and now - self.questions_at < 1.0:
                return None
            self.questions_at = now
            digest = self.question_digest()
        self.hub.publish_questions(digest)
        return digest

    def close(self):
        for session in self.sessions.values(): session.close()
