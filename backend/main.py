"""Local ToolForge API. Run from any cwd: python /path/to/backend/main.py."""
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from backend.pilot_service import PilotService
from toolforge_pilot.core import project_path
DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'toolforge.db'
ALLOWED_ORIGINS = {'http://127.0.0.1:8000', 'http://localhost:8000', 'http://127.0.0.1:5173', 'http://localhost:5173'}


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=2000)

    @field_validator('name', mode='before')
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class Project(ProjectInput):
    id: str
    created_at: str
    folder_path: str | None = None
    archived: bool = False
    group_id: str | None = None


class GroupInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=60)

    @field_validator('name', mode='before')
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProjectGroup(GroupInput):
    id: str
    created_at: str
    project_count: int = 0


class FolderInput(BaseModel):
    path: str
    create: bool = False


class Database:
    def __init__(self, path):
        self.path = Path(path).resolve()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
                    created_at TEXT NOT NULL)''')
                conn.execute('CREATE INDEX IF NOT EXISTS projects_created ON projects(created_at DESC, id DESC)')
                if 'folder_path' not in [row[1] for row in conn.execute('PRAGMA table_info(projects)')]:
                    conn.execute('ALTER TABLE projects ADD COLUMN folder_path TEXT')
                if 'archived' not in [row[1] for row in conn.execute('PRAGMA table_info(projects)')]:
                    conn.execute('ALTER TABLE projects ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
                if 'group_id' not in [row[1] for row in conn.execute('PRAGMA table_info(projects)')]:
                    conn.execute('ALTER TABLE projects ADD COLUMN group_id TEXT')
                conn.execute('''CREATE TABLE IF NOT EXISTS project_groups (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)''')
                conn.execute('CREATE INDEX IF NOT EXISTS project_groups_created ON project_groups(created_at, id)')
                conn.execute('PRAGMA user_version=4')

    def all(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            return [{**dict(row),'archived':bool(row['archived'])} for row in conn.execute('SELECT * FROM projects ORDER BY created_at DESC, id DESC')]

    def get(self, ident):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute('SELECT * FROM projects WHERE id=?', (ident,)).fetchone()
            return {**dict(row),'archived':bool(row['archived'])} if row else None

    def set_folder(self, ident, path):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn: conn.execute('UPDATE projects SET folder_path=? WHERE id=?', (path, ident))

    def update(self, ident, name, archived, group_id=None):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn: conn.execute('UPDATE projects SET name=?, archived=?, group_id=? WHERE id=?',
                                    (name, int(archived), group_id, ident))

    def groups(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''SELECT g.id, g.name, g.created_at, COUNT(p.id) AS project_count
                FROM project_groups g LEFT JOIN projects p ON p.group_id = g.id
                GROUP BY g.id ORDER BY g.created_at, g.id''').fetchall()
            return [dict(row) for row in rows]

    def group(self, ident):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute('''SELECT g.id, g.name, g.created_at, COUNT(p.id) AS project_count
                FROM project_groups g LEFT JOIN projects p ON p.group_id = g.id
                WHERE g.id = ? GROUP BY g.id''', (ident,)).fetchone()
            return dict(row) if row else None

    def create_group(self, name):
        result = {'id': str(uuid4()), 'name': name,
                  'created_at': datetime.now(timezone.utc).isoformat(timespec='microseconds')}
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn:
                conn.execute('INSERT INTO project_groups(id,name,created_at) VALUES (?,?,?)',
                             (result['id'], result['name'], result['created_at']))
        return {**result, 'project_count': 0}

    def rename_group(self, ident, name):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn: conn.execute('UPDATE project_groups SET name=? WHERE id=?', (name, ident))
        return self.group(ident)

    def delete_group(self, ident):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            count = conn.execute('SELECT COUNT(*) FROM projects WHERE group_id=?', (ident,)).fetchone()[0]
            with conn:
                conn.execute('UPDATE projects SET group_id=NULL WHERE group_id=?', (ident,))
                conn.execute('DELETE FROM project_groups WHERE id=?', (ident,))
        return count

    def delete(self, ident):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn: conn.execute('DELETE FROM projects WHERE id=?', (ident,))

    def create(self, data):
        result = {'id': str(uuid4()), 'name': data.name, 'description': data.description,
                  'created_at': datetime.now(timezone.utc).isoformat(timespec='microseconds')}
        with closing(sqlite3.connect(self.path, timeout=10)) as conn:
            with conn:
                conn.execute('INSERT INTO projects(id,name,description,created_at) VALUES (?,?,?,?)',
                             (result['id'], result['name'], result['description'], result['created_at']))
        return result


class PilotLauncher:
    """Launches the included desktop Pilot only; no user-supplied commands."""
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()

    def open(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                return {'status': 'already_running', 'message': 'Das Pilot-Fenster ist bereits geöffnet.'}
            script = ROOT / 'start_toolforge_pilot.py'
            if not script.is_file():
                raise HTTPException(503, 'Pilot-Startdatei fehlt in diesem Paket.')
            folder = Path(os.environ.get('APPDATA', str(Path.home() / '.local' / 'share'))) / 'ToolForgePilot'
            folder.mkdir(parents=True, exist_ok=True)
            logfile = folder / 'desktop-start.log'
            env = os.environ.copy()
            env['TOOLFORGE_BROWSER_ORIGIN'] = 'http://127.0.0.1:8000'
            with logfile.open('a', encoding='utf-8') as log:
                self.process = subprocess.Popen([sys.executable, str(script)], cwd=ROOT, env=env,
                                               stdout=log, stderr=subprocess.STDOUT,
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            time.sleep(0.2)
            if self.process.poll() is not None:
                raise HTTPException(503, f'Der Pilot konnte nicht geöffnet werden. Startprotokoll: {logfile}')
            return {'status': 'started', 'message': 'Pilot gestartet. Wähle dort deinen Arbeitsordner.'}


def create_app(db_path=None, pilot_launcher=None, static_dir=None):
    database = Database(db_path or os.environ.get('TOOLFORGE_DB', str(DEFAULT_DB)))
    launcher = pilot_launcher or PilotLauncher()
    pilot = PilotService()
    @asynccontextmanager
    async def lifespan(app):
        database.initialize()
        yield
        pilot.close()
    app = FastAPI(title='ToolForge · lokale Workbench', version='1.2.0', lifespan=lifespan)
    app.state.database = database
    app.state.pilot = pilot
    app.state.shutdown = None

    @app.middleware('http')
    async def local_access(request: Request, call_next):
        hostname = urlsplit('http://' + request.headers.get('host', '')).hostname
        if hostname not in ('127.0.0.1', 'localhost', '::1'):
            return JSONResponse({'detail': 'Nur lokale Hostnamen sind zugelassen.'}, status_code=403)
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            origin = request.headers.get('origin')
            if origin is not None and origin not in ALLOWED_ORIGINS:
                return JSONResponse({'detail': 'Zugriff von dieser Webseite ist nicht erlaubt.'}, status_code=403)
            if request.headers.get('x-toolforge-request') != '1':
                return JSONResponse({'detail': 'ToolForge-Anfrageheader fehlt.'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Seitenübergreifende Anfrage abgelehnt.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/assets/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(sqlite3.Error)
    async def database_error(request, exc):
        return JSONResponse({'detail': 'Die lokale Datenbank ist momentan nicht verfügbar. Bitte erneut versuchen.'}, status_code=503)

    @app.post('/api/shutdown')
    def shutdown():
        if not app.state.shutdown:raise HTTPException(409,'Server bitte über Start_ToolForge starten oder im Terminal beenden.')
        threading.Timer(.3,app.state.shutdown).start()
        return {'status':'stopping'}

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    @app.get('/api/projects', response_model=list[Project])
    def projects():
        return database.all()

    @app.post('/api/projects', response_model=Project, status_code=201)
    def create_project(payload: ProjectInput):
        return database.create(payload)

    @app.get('/api/groups', response_model=list[ProjectGroup])
    def groups():
        return database.groups()

    @app.post('/api/groups', response_model=ProjectGroup, status_code=201)
    def create_group(payload: GroupInput):
        return database.create_group(payload.name)

    @app.patch('/api/groups/{group_id}', response_model=ProjectGroup)
    def rename_group(group_id: str, payload: GroupInput):
        if not database.group(group_id): raise HTTPException(404, 'Projektgruppe nicht gefunden.')
        return database.rename_group(group_id, payload.name)

    @app.delete('/api/groups/{group_id}')
    def delete_group(group_id: str):
        if not database.group(group_id): raise HTTPException(404, 'Projektgruppe nicht gefunden.')
        return {'removed': True, 'projects_ungrouped': database.delete_group(group_id)}

    @app.get('/api/projects/{project_id}', response_model=Project)
    def get_project(project_id: str):
        project = database.get(project_id)
        if project is None:
            raise HTTPException(404, 'Projekt nicht gefunden.')
        return project

    def session_for(ident):
        row = database.get(ident)
        if not row: raise HTTPException(404, 'Projekt nicht gefunden.')
        if row.get('archived'): raise HTTPException(409, 'Projekt ist archiviert. Zuerst wiederherstellen.')
        if not row.get('folder_path'): raise HTTPException(409, 'Zuerst einen Arbeitsordner zuordnen.')
        try: return pilot.get(row['folder_path'])
        except (ValueError, RuntimeError, OSError) as exc: raise HTTPException(409, str(exc))

    @app.exception_handler(OSError)
    async def filesystem_error(request, exc):
        return JSONResponse({'detail':'Dateisystemoperation fehlgeschlagen: ' + str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def input_error(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=422)

    @app.post('/api/projects/{ident}/folder', response_model=Project)
    def attach_folder(ident: str, data: FolderInput):
        if not database.get(ident): raise HTTPException(404, 'Projekt nicht gefunden.')
        folder = Path(data.path).expanduser()
        if not folder.is_absolute(): raise ValueError('Bitte einen vollständigen absoluten Ordnerpfad eingeben.')
        resolved = folder.resolve()
        if resolved.is_relative_to(ROOT) or ROOT.is_relative_to(resolved): raise ValueError('Der Arbeitsordner muss außerhalb des Pilot-Programmordners liegen.')
        if not folder.exists() and data.create: folder.mkdir(parents=True)
        folder = project_path(folder)
        old = database.get(ident).get('folder_path')
        if old and pilot.get(old).busy: raise ValueError('Vor einem Ordnerwechsel den aktiven Lauf stoppen.')
        database.set_folder(ident, str(folder))
        pilot.get(str(folder))  # inspect saved project state immediately
        return database.get(ident)

    @app.patch('/api/projects/{ident}', response_model=Project)
    def edit_project(ident: str, data: dict):
        row=get_project(ident)
        if row.get('folder_path') and pilot.get(row['folder_path']).busy: raise HTTPException(409, 'Lauf vor Verwaltungsänderungen stoppen.')
        name=data.get('name',row['name']); archived=data.get('archived',row['archived'])
        group_id=data.get('group_id',row.get('group_id'))
        if not isinstance(name,str) or not 1<=len(name.strip())<=100 or type(archived)!=bool: raise ValueError('Name: 1–100 Zeichen; archived: bool.')
        if group_id is not None and (not isinstance(group_id,str) or not database.group(group_id)): raise ValueError('Projektgruppe nicht gefunden.')
        database.update(ident,name.strip(),archived,group_id); return database.get(ident)

    @app.get('/api/projects/{ident}/deletion-preview')
    def deletion_preview(ident: str):
        from backend.lifecycle import preview
        return preview(get_project(ident),database.all())

    @app.post('/api/projects/{ident}/delete')
    def delete_project(ident: str, data: dict):
        from backend.lifecycle import remove
        row=get_project(ident)
        if data.get('confirm_name')!=row['name']:raise ValueError('Zum Löschen den aktuellen Projektnamen eingeben.')
        if any(type(data.get(k,False))!=bool for k in ('cleanup','remove_folder','include_global')):raise ValueError('Ungültige Löschoptionen.')
        if row.get('folder_path') and Path(row['folder_path']).is_dir():
            session=pilot.get(row['folder_path'])
            if session.busy:raise HTTPException(409,'Lauf vor dem Löschen stoppen.')
        session = pilot.get(row['folder_path']) if row.get('folder_path') and Path(row['folder_path']).is_dir() else None
        if session:
            with session.guard:
                if session.busy: raise HTTPException(409,'Lauf vor dem Löschen stoppen.')
                session.maintenance=True
        try: report=remove(row,database.all(),data.get('cleanup',False),data.get('remove_folder',False),data.get('include_global',False))
        finally:
            if session: session.maintenance=False
        if row.get('folder_path'):
            session=pilot.sessions.pop(str(Path(row['folder_path']).resolve()),None)
            if session:session.close()
        database.delete(ident)
        return report

    @app.post('/api/projects/{ident}/pilot/answers', status_code=202)
    def submit_answer(ident: str, data: dict):
        return session_for(ident).submit_answer(str(data.get('task_id','')),str(data.get('answer','')))

    def workspace_for(ident):
        from backend.workspace import Workspace
        session=session_for(ident)
        with session.guard:
            if not hasattr(session,'workspace'):session.workspace=Workspace(session)
            return session.workspace

    @app.get('/api/projects/{ident}/workspace/tree')
    def workspace_tree(ident: str):return workspace_for(ident).tree()

    @app.get('/api/projects/{ident}/workspace/file')
    def workspace_file(ident: str, path: str):return workspace_for(ident).read(path)

    @app.put('/api/projects/{ident}/workspace/file')
    def workspace_save(ident: str, data: dict):return workspace_for(ident).save(str(data.get('path','')),data.get('text'),data.get('revision'))

    @app.get('/api/projects/{ident}/workspace/download')
    def workspace_download(ident: str, path: str):
        file=workspace_for(ident).path(path)
        if not file.is_file():raise HTTPException(404,'Datei nicht gefunden.')
        return FileResponse(file,filename=file.name,media_type='application/octet-stream')

    @app.get('/api/projects/{ident}/workspace/job')
    def workspace_job(ident: str):return workspace_for(ident).state()

    @app.post('/api/projects/{ident}/workspace/job', status_code=202)
    def workspace_start(ident: str, data: dict):return workspace_for(ident).start(data)

    @app.get('/api/projects/{ident}/workspace/git')
    def workspace_git(ident: str):return workspace_for(ident).git_status()

    @app.post('/api/projects/{ident}/workspace/git')
    def workspace_git_action(ident: str, data: dict):return workspace_for(ident).git_action(data)

    @app.get('/api/projects/{ident}/workspace/workflow')
    def workspace_workflow(ident: str):return workspace_for(ident).workflows()

    @app.put('/api/projects/{ident}/workspace/workflow')
    def workspace_workflow_save(ident: str, data: dict):return workspace_for(ident).save_workflow(data)

    @app.post('/api/projects/{ident}/workspace/ai/apply')
    def workspace_ai_apply(ident: str, data: dict):return workspace_for(ident).apply_ai(str(data.get('id','')))

    @app.post('/api/folders/browse')
    def browse_folder():
        try:
            result = subprocess.run([sys.executable, str(ROOT / 'folder_picker.py')], capture_output=True, text=True, encoding='utf-8', timeout=120)
            if result.returncode != 0: raise ValueError('Ordnerdialog nicht verfügbar. Bitte den Pfad direkt eingeben.')
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired: raise HTTPException(408, 'Ordnerauswahl abgebrochen: Zeitlimit erreicht.')

    @app.get('/api/projects/{ident}/pilot')
    def pilot_snapshot(ident: str): return session_for(ident).snapshot()

    # --- V1.1: event stream, incremental index, benchmarks and acceptance ---

    def event_response(channel, initial, unsubscribe):
        from backend.events import stream
        headers = {'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'}

        def generate():
            try:
                yield from stream(channel, initial)
            finally:
                unsubscribe()
        return StreamingResponse(generate(), media_type='text/event-stream', headers=headers)

    @app.get('/api/events')
    def global_events():
        digest = pilot.question_digest()
        channel = pilot.hub.subscribe_global()
        return event_response(channel, [('questions', {'questions': digest, 'count': len(digest)})],
                              lambda: pilot.hub.unsubscribe_global(channel))

    @app.get('/api/projects/{ident}/pilot/events')
    def pilot_events(ident: str):
        session = session_for(ident)
        channel = pilot.hub.subscribe_session(session.ident)
        return event_response(channel, [('snapshot', session.snapshot())],
                              lambda: pilot.hub.unsubscribe_session(session.ident, channel))

    @app.post('/api/projects/{ident}/pilot/index')
    def pilot_index_refresh(ident: str, data: dict | None = None):
        return session_for(ident).refresh_index(bool((data or {}).get('force')))

    @app.post('/api/projects/{ident}/pilot/analysis')
    def pilot_analysis(ident: str, data: dict | None = None):
        return session_for(ident).analysis_context(data or {})

    @app.post('/api/projects/{ident}/pilot/plan/preview')
    def pilot_plan_preview(ident: str, data: dict):
        return session_for(ident).preview_plan(data)

    @app.get('/api/projects/{ident}/pilot/benchmark')
    def pilot_benchmark_cache(ident: str): return session_for(ident).benchmark_cache()

    @app.post('/api/projects/{ident}/pilot/benchmark', status_code=202)
    def pilot_benchmark_run(ident: str, data: dict): return session_for(ident).run_benchmark(data)

    @app.get('/api/projects/{ident}/pilot/scenarios')
    def pilot_scenarios(ident: str): return session_for(ident).snapshot().get('scenarios')

    @app.post('/api/projects/{ident}/pilot/scenarios/run', status_code=202)
    def pilot_scenarios_run(ident: str, data: dict | None = None): return session_for(ident).run_acceptance(data or {})

    @app.post('/api/projects/{ident}/pilot/scenarios/review')
    def pilot_scenarios_review(ident: str, data: dict | None = None): return session_for(ident).review_acceptance(data or {})

    @app.get('/api/projects/{ident}/pilot/research')
    def pilot_research_cache(ident: str): return session_for(ident).research_cache()

    @app.post('/api/projects/{ident}/pilot/research', status_code=202)
    def pilot_research(ident: str, data: dict): return session_for(ident).research(data)

    @app.post('/api/projects/{ident}/pilot/graph')
    def pilot_graph(ident: str, data: dict):
        from toolforge_pilot import task_graph
        session = session_for(ident)
        return task_graph.update(session.store.project, session.store.state, data)

    @app.get('/api/projects/{ident}/pilot/environment')
    def pilot_environment(ident: str): return session_for(ident).environment_lock()

    @app.post('/api/projects/{ident}/pilot/presets/export')
    def pilot_preset_export(ident: str, data: dict | None = None): return session_for(ident).export_preset(data or {})

    @app.post('/api/projects/{ident}/pilot/presets/import')
    def pilot_preset_import(ident: str, data: dict): return session_for(ident).import_preset(data)

    @app.get('/api/projects/{ident}/pilot/operations')
    def pilot_operations(ident: str):
        from toolforge_pilot import operations
        return operations.operations_status(session_for(ident).store.project)

    @app.post('/api/projects/{ident}/pilot/operations/rotate')
    def pilot_log_rotation(ident: str): return session_for(ident).rotate_logs()

    @app.post('/api/projects/{ident}/pilot/backups/restore')
    def pilot_backup_restore(ident: str, data: dict): return session_for(ident).restore_backup(data)

    @app.get('/api/projects/{ident}/pilot/export')
    def pilot_export(ident: str):
        file = session_for(ident).export_project()
        return FileResponse(file, filename=file.name, media_type='application/zip')

    @app.post('/api/projects/{ident}/pilot/import')
    def pilot_import(ident: str, data: dict): return session_for(ident).import_project(data)

    @app.get('/api/projects/{ident}/pilot/sandbox')
    def pilot_sandbox(ident: str): return session_for(ident).sandbox_status()

    @app.post('/api/projects/{ident}/pilot/sandbox/build', status_code=202)
    def pilot_sandbox_build(ident: str): return session_for(ident).sandbox_build()

    @app.post('/api/projects/{ident}/pilot/sandbox/image/remove', status_code=202)
    def pilot_sandbox_image_remove(ident: str): return session_for(ident).sandbox_remove_image()

    @app.post('/api/projects/{ident}/pilot/sandbox/network', status_code=202)
    def pilot_sandbox_network(ident: str, data: dict): return session_for(ident).sandbox_network(data)

    @app.post('/api/projects/{ident}/pilot/sandbox/package', status_code=202)
    def pilot_sandbox_package(ident: str, data: dict): return session_for(ident).sandbox_package(data)

    @app.get('/api/help')
    def help_docs():
        from backend.assistance import help_documents
        return help_documents()

    @app.post('/api/projects/{ident}/pilot/assistant/options')
    def assistant_options(ident: str):return session_for(ident).assistant_options()

    @app.post('/api/projects/{ident}/pilot/improvements/suggest',status_code=202)
    def improvements_suggest(ident: str,data:dict):return session_for(ident).propose_improvements(data)

    @app.post('/api/projects/{ident}/pilot/improvements/add',status_code=202)
    def improvements_add(ident: str,data:dict):return session_for(ident).queue_improvement(data.get('text',''),data.get('selected'))

    @app.post('/api/projects/{ident}/pilot/help',status_code=202)
    def help_chat(ident: str,data:dict):return session_for(ident).help_question(data)

    @app.post('/api/projects/{ident}/pilot/settings')
    def pilot_settings(ident: str, data: dict): return session_for(ident).configure(data)

    @app.post('/api/projects/{ident}/pilot/models')
    def pilot_models(ident: str): return session_for(ident).models()

    @app.post('/api/projects/{ident}/pilot/plan')
    def pilot_plan(ident: str, data: dict):
        confirm = data.get('confirm') is True if isinstance(data, dict) else False
        plan = data.get('plan', data) if isinstance(data, dict) else data
        return session_for(ident).apply_plan(plan, confirm=confirm)

    @app.post('/api/projects/{ident}/pilot/demo')
    def pilot_demo(ident: str):
        return session_for(ident).apply_plan(json.loads((ROOT / 'examples/demo_plan.json').read_text(encoding='utf-8')), confirm=True)

    @app.post('/api/projects/{ident}/pilot/preflight/options')
    def preflight_options(ident: str, data: dict):
        return session_for(ident).preflight_options(str(data.get('kind','coding')))

    @app.post('/api/projects/{ident}/pilot/preflight', status_code=202)
    def preflight_run(ident: str, data: dict): return session_for(ident).run_preflight(data)

    @app.post('/api/projects/{ident}/pilot/preflight/accept', status_code=202)
    def preflight_accept(ident: str, data: dict): return session_for(ident).accept_preflight(str(data.get('goal','')))

    @app.post('/api/projects/{ident}/pilot/generate', status_code=202)
    def pilot_generate(ident: str, data: dict): return session_for(ident).generate(str(data.get('goal', '')))

    @app.post('/api/projects/{ident}/pilot/start', status_code=202)
    def pilot_start(ident: str, data: dict): return session_for(ident).start(str(data.get('answer', '')))

    @app.post('/api/projects/{ident}/pilot/runtime/options')
    def runtime_options(ident: str,data:dict):return session_for(ident).runtime_options(data)

    @app.post('/api/projects/{ident}/pilot/pause/cancel')
    def cancel_pause(ident: str):return session_for(ident).cancel_pause()

    @app.post('/api/projects/{ident}/pilot/pause')
    def pilot_pause(ident: str): return session_for(ident).stop(False)

    @app.post('/api/projects/{ident}/pilot/stop')
    def pilot_stop(ident: str): return session_for(ident).stop(True)

    @app.post('/api/projects/{ident}/pilot/logs/open')
    def pilot_logs(ident: str): return session_for(ident).open_logs()

    @app.post('/api/pilot/open')
    def open_pilot():
        return launcher.open()

    @app.get('/api/workbench')
    def workbench():
        return {'name': 'ToolForge', 'version': '1.2.0', 'stage': 12, 'pilot_included': (ROOT / 'start_toolforge_pilot.py').is_file()}

    dist = Path(static_dir or ROOT / 'frontend' / 'dist')
    if (dist / 'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

    @app.get('/', include_in_schema=False)
    def index():
        file = dist / 'index.html'
        if not file.is_file():
            return JSONResponse({'detail': 'Frontend-Build fehlt. Im Ordner frontend: npm ci und npm run build.'}, status_code=503)
        return FileResponse(file, headers={'Cache-Control': 'no-cache'})

    return app


app = create_app()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
