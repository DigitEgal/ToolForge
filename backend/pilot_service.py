"""In-process bridge between the browser workbench and the verified Pilot engine."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from toolforge_pilot.core import APP_ROOT, Store, Engine, AiderAdapter, atomic_json, data_root, fingerprint, project_path, progress, validate_plan
from toolforge_pilot.profiles import profile, discover_models, adapt_plan, chat_plan
from toolforge_pilot import project_index, benchmarks, planning, task_graph, scenarios, environments, operations
from toolforge_pilot.simulation import DemoAdapter
from toolforge_pilot.preflight import Studio, MODEL_LOCK, evaluate, suggest, signature, context_compatible
from backend.events import EventHub

AIDER_PYTHON = APP_ROOT / '.aider-venv' / ('Scripts/python.exe' if os.name=='nt' else 'bin/python')
DEFAULTS = {'aider_python': str(AIDER_PYTHON) if AIDER_PYTHON.is_file() else sys.executable, 'python': sys.executable, 'base': 'http://localhost:1234/v1', 'model': '', 'context_tokens': 20000,
            'output_tokens': 2048, 'temperature': 0.2, 'edit': 'auto', 'budget': 20, 'timeout': 900,
            'sandbox':False,'sandbox_network':'','sandbox_memory':'4g','sandbox_cpus':2,'sandbox_pids':256,'sandbox_ports':'',
            'web_search':False, 'research_domains':'', 'debug_logging':False, 'allow_pip': False, 'allow_choco': False, 'allow_npm': False, 'simulation': False}


from backend.assistance import AssistanceMixin

class Session(AssistanceMixin):
    def __init__(self, folder):
        self.store = Store(project_path(folder))
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
        for name in ('README.md', 'PROGRESS.md', 'IMPLEMENTATION_PLAN.md'):
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
                'operations': operations.operations_status(self.store.project),
                'environment': {'lock_file': str(APP_ROOT / 'runtime' / 'environment-lock.json'),
                                'presets': environments.list_presets()}}

    def configure(self, settings):
        if self.busy: raise ValueError('Während eines Laufs erst pausieren oder stoppen.')
        clean = {k: v for k, v in settings.items() if k in DEFAULTS}
        candidate = {**self.settings, **clean}
        p = profile(candidate)
        candidate.update(context_tokens=p['context_tokens'], output_tokens=p['output_tokens'], temperature=p['temperature'])
        if candidate['edit'] not in ('auto', 'whole', 'diff'): raise ValueError('Ungültiges Edit-Format.')
        if not 1 <= int(candidate['budget']) <= 500: raise ValueError('Budget: 1 bis 500.')
        if not 30 <= int(candidate['timeout']) <= 86400: raise ValueError('Timeout: 30 bis 86400 Sekunden.')
        for key in ('allow_pip', 'allow_choco', 'allow_npm', 'simulation','web_search','debug_logging','sandbox'):
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
        atomic_json(self.settings_path, candidate)
        # Each model has its own persistent context + temperature profile.
        profiles_file = data_root() / 'model-profiles.json'
        try: profiles = json.loads(profiles_file.read_text(encoding='utf-8'))
        except FileNotFoundError: profiles = {}
        if candidate['model']:
            profiles[candidate['base'].rstrip('/') + '|' + candidate['model']] = p
            atomic_json(profiles_file, profiles)
        return self.snapshot()

    def models(self):
        values = discover_models(self.settings['base'], self.api_key)
        try: saved = json.loads((data_root() / 'model-profiles.json').read_text(encoding='utf-8'))
        except FileNotFoundError: saved = {}
        for item in values:
            item['saved_profile'] = saved.get(self.settings['base'].rstrip('/') + '|' + item['id'])
        return values

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
            key = self.api_key
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
            def run():
                operation = function
                while True:
                    acquired = MODEL_LOCK.acquire(blocking=False) if model_lock else False
                    try:
                        if model_lock and not acquired: raise ValueError('Ein anderes Projekt nutzt gerade den Modellserver. Später erneut starten.')
                        operation()
                    except Exception as exc:
                        if self.settings.get('debug_logging'):
                            import traceback
                            from toolforge_pilot.diagnostics import record
                            record(self.store.project,'session_exception',traceback.format_exc(),[self.api_key])
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

    def studio(self):
        return Studio(self.settings['base'], self.api_key, int(self.settings['timeout']), self.cancel)

    def preflight_options(self, kind='coding'):
        return suggest(self.studio().inventory(), kind)

    def run_preflight(self, data):
        goal = str(data.get('goal', '')).strip()
        candidates = data.get('candidates', [])
        if not isinstance(candidates, list) or not all(isinstance(x, str) for x in candidates):
            raise ValueError('Kandidaten müssen eine Liste von Modellschlüsseln sein.')
        def save(report):
            report['base'] = self.settings['base']
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
            save({'status':'running','accepted':False,'goal':goal,'samples':[],'note':'Vergleich wird vorbereitet.'})
            try:
                evaluate(self.studio(), goal, candidates, str(data.get('judge','')),
                    data.get('context_tokens',20000), str(data.get('kind','coding')),
                    data.get('two_temperatures',True) is True, phase, save)
            except Exception as exc:
                self.preflight.update(status='error', error=str(exc), accepted=False)
                save(self.preflight)
                raise
            self.phase = 'Vorabcheck fertig. Arbeitsproben prüfen und Empfehlung übernehmen.'
        return self.background(work)

    def accept_preflight(self, goal):
        report = self.preflight
        if not report or report.get('status') != 'ready': raise ValueError('Keine gültige Empfehlung vorhanden.')
        if report['goal_signature'] != signature(goal): raise ValueError('Aufgabe geändert. Vorabcheck erneut ausführen.')
        if report['base'] != self.settings['base']: raise ValueError('Modellserver geändert. Vorabcheck erneut ausführen.')
        recommendation = dict(report['recommendation'])
        def work():
            self.phase = 'Empfohlenes Modell und Kontext laden …'
            studio = self.studio()
            try:
                ident = studio.switch(recommendation['model'], recommendation['context_tokens'])
                actual = getattr(studio, 'actual_context', None)
                # Adopt the context LM Studio actually confirmed instead of the requested value.
                if type(actual) is not int: actual = recommendation['context_tokens']
                values = {'temperature':recommendation['temperature'], 'context_tokens':actual,
                          'output_tokens':min(recommendation['output_tokens'], max(256, actual//4))}
                values['model'] = ident
                self.settings.update(values)
                atomic_json(self.settings_path, self.settings)
                report['recommendation']['context_tokens'] = actual
                report['accepted_settings'] = values
                report['accepted'] = True
                atomic_json(self.preflight_path, report)
                self.phase = f'Empfehlung übernommen. Geprüfter Kontext: {actual} Tokens. Plan kann erstellt werden.'
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
        expected = report['accepted_settings']
        if self.settings['base'] != report['base'] or any(self.settings[k] != v for k,v in expected.items()):
            raise ValueError('Einstellungen weichen von der Empfehlung ab. Empfehlung erneut übernehmen oder Vorabcheck wiederholen.')
        instances = self.studio().instances()
        if (len(instances) != 1 or instances[0]['id'] != expected['model']
                or not context_compatible(expected['context_tokens'], instances[0].get('config',{}).get('context_length'))):
            raise ValueError('Geladenes Modell/Kontext geändert. Empfehlung erneut übernehmen.')

    def generate(self, goal):
        if not goal.strip(): raise ValueError('Bitte ein Projektziel eingeben.')
        def work():
            self.remaining_budget = 0
            self.check_preflight(goal)
            self.phase = 'Plan wird aus der Beschreibung erzeugt …'
            p = profile(self.settings)
            if not self.settings['model']: raise ValueError('Bitte zuerst ein Modell unter Einstellungen wählen.')
            folder = self.store.log_root.parent / 'planning'; folder.mkdir(exist_ok=True)
            def audit(attempt, raw, error):
                atomic_json(folder / (str(time.time_ns()) + '.json'), {'attempt':attempt+1,'response':raw,'error':error})
                self.phase = ('Planantwort wird korrigiert: ' + error) if error else 'Plan validiert; speichern …'
            plan = chat_plan(self.settings['base'], self.api_key, self.settings['model'], goal, p, audit)
            planning.backup_plan(self.store.project, self.store.state, 'Vor Planerzeugung')
            with self.answer_lock:
                self.pending_answers.clear()
                atomic_json(self.store.log_root.parent / 'pending-answers.json', {})
            self.store.set_plan(plan)
            self.phase = 'Plan erstellt, versioniert und aktiv. Bitte prüfen; Start erfolgt erst auf Knopfdruck.'
        return self.background(work)

    def start(self, answer=''):
        if not self.store.state: raise ValueError('Zuerst einen Aufgabenplan erstellen oder laden.')
        s = dict(self.settings)
        def work():
            self.apply_pending_improvements()
            self.phase = 'Projektstand und Modellprofil vergleichen …'
            if s['simulation']:
                plan = json.loads((APP_ROOT / 'examples' / 'demo_plan.json').read_text(encoding='utf-8'))
                if self.store.state['plan'] != plan: raise ValueError('Simulation benötigt den unveränderten Beispielplan.')
                adapter = DemoAdapter()
            else:
                self.check_preflight()
                if not s['model']: raise ValueError('Bitte ein Modell auswählen.')
                p = profile(s)
                # Prefer the actual loaded instance limit, never its theoretical maximum.
                try:
                    entries = discover_models(s['base'], self.api_key)
                    match = next((x for x in entries if x['id'] == s['model']), None)
                    if match and match['loaded_context']:
                        p['context_tokens'] = min(p['context_tokens'], match['loaded_context'])
                        p['output_tokens'] = min(p['output_tokens'], p['context_tokens'] // 4)
                        p['source'] = 'lmstudio-loaded-instance'
                except Exception as exc:
                    self.emit('log', 'Modellmetadaten nicht automatisch lesbar; manuelles Profil verwendet: ' + str(exc) + '\n')
                p['model'] = s['model']
                adapted, changed = adapt_plan(self.store.state['plan'], self.store.project, p, completed={k for k,v in self.store.state['tasks'].items() if v['status']=='VERIFIED'})
                if changed:
                    self.store.set_plan(adapted, preserve=True)
                    self.emit('log', 'Modellspezifische Planversion gespeichert: ' + self.store.state['plan_file'] + '\n')
                adapter = AiderAdapter(s['aider_python'], s['base'], self.api_key, s['model'], s['edit'], int(s['timeout']), p)
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
            benchmarks.measure(self.studio(), goal, model, judge, kind, contexts, repeats, two,
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

    def get(self, path):
        path = str(Path(path).resolve())
        with self.guard:
            session = self.sessions.get(path)
            if session is None:
                session = Session(path)
                session.hub = self.hub
                session.service = self
                session.ident = hashlib.sha256(os.path.normcase(path).encode()).hexdigest()[:24]
                self.sessions[path] = session
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
