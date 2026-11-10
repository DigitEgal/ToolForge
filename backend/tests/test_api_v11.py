import copy
import io
import json
from unittest.mock import patch
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

HEADERS = {'X-ToolForge-Request': '1', 'Origin': 'http://127.0.0.1:8000'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA', str(tmp_path / 'controller'))
    app = create_app(tmp_path / 'db.sqlite3')
    with TestClient(app, base_url='http://127.0.0.1:8000', headers=HEADERS) as test_client:
        yield test_client


def project_with_folder(client, tmp_path, name='V11'):
    folder = tmp_path / name
    folder.mkdir()
    (folder / 'main.py').write_text('def greet():\n    return "hallo"\n', encoding='utf-8')
    (folder / 'README.md').write_text('# V11\n', encoding='utf-8')
    ident = client.post('/api/projects', json={'name': name}).json()['id']
    assert client.post(f'/api/projects/{ident}/folder', json={'path': str(folder)}).status_code == 200
    return ident, folder


def demo_plan():
    from toolforge_pilot.core import APP_ROOT
    return json.loads((APP_ROOT / 'examples/demo_plan.json').read_text(encoding='utf-8'))


def test_v11_index_analysis_and_plan_preview(client, tmp_path):
    ident, folder = project_with_folder(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'

    index = client.post(base + '/index', json={})
    assert index.status_code == 200
    assert index.json()['indexed'] is True
    assert index.json()['summary']['files'] >= 2

    analysis = client.post(base + '/analysis', json={'max_chars': 8000})
    assert analysis.status_code == 200
    payload = analysis.json()
    assert payload['coverage']['files_included'] >= 1
    assert payload['manifest']['files_total'] >= 2
    assert payload['chunks']
    assert client.post(base + '/analysis', json={'max_chars': 10}).status_code == 422

    assert client.post(base + '/demo', json={}).status_code == 200
    plan = demo_plan()
    proposed = copy.deepcopy(plan)
    proposed['version'] = 2
    proposed['tasks'].append({
        'id': 'docs', 'title': 'Dokumentation', 'instruction': 'Ergänze die README.',
        'depends_on': ['export'], 'files': ['README.md'], 'acceptance': ['README erklärt alles'],
        'weight': 1, 'estimate': [1, 2], 'max_repairs': 2,
        'checks': [{'argv': ['{python}', '-c', 'print("docs")'], 'cwd': '.', 'timeout': 30}],
    })
    preview = client.post(base + '/plan/preview', json=proposed)
    assert preview.status_code == 200, preview.text
    diff = preview.json()
    assert diff['old_version'] == 1 and diff['new_version'] == 2
    assert diff['added'][0]['id'] == 'docs'
    assert diff['task_count'] == {'before': 3, 'after': 4}
    assert diff['requires_confirmation'] is False
    assert client.post(base + '/plan', json={'plan': proposed, 'confirm': False}).status_code == 200

    session = client.app.state.pilot.get(str(folder.resolve()))
    session.store.state['tasks']['normalize']['status'] = 'VERIFIED'
    session.store.save()
    risky = copy.deepcopy(proposed)
    risky['version'] = 3
    risky['tasks'][0]['instruction'] = 'Geänderte Anweisung für bereits geprüften Code.'
    preview = client.post(base + '/plan/preview', json=risky).json()
    assert preview['requires_confirmation'] is True
    assert preview['risk'] == 'high'
    assert preview['verified_impacted'][0]['task'] == 'normalize'
    rejected = client.post(base + '/plan', json={'plan': risky, 'confirm': False})
    assert rejected.status_code == 422
    assert 'ausdrücklich bestätigen' in rejected.json()['detail']
    confirmed = client.post(base + '/plan', json={'plan': risky, 'confirm': True})
    assert confirmed.status_code == 200
    assert confirmed.json()['state']['plan']['version'] == 3


def test_v11_graph_environment_operations_presets_and_export(client, tmp_path):
    ident, folder = project_with_folder(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    assert client.post(base + '/demo', json={}).status_code == 200

    graph = client.post(base + '/graph', json={'priorities': {'cli': 90}})
    assert graph.status_code == 200
    node = next(row for row in graph.json()['nodes'] if row['id'] == 'cli')
    assert node['priority'] == 90
    conflict = next(row for row in graph.json()['conflicts'] if row['file'] == 'texttool.py')
    assert conflict['blocking'] is False
    approved = client.post(base + '/graph', json={'approve_file': 'texttool.py', 'approved': True})
    assert approved.status_code == 200
    assert next(row for row in approved.json()['conflicts'] if row['file'] == 'texttool.py')['approved'] is True

    environment = client.get(base + '/environment')
    assert environment.status_code == 200
    lock = environment.json()
    assert lock['controller']['requirements']
    assert lock['aider']['pinned'][0]['name'] == 'aider-chat'
    assert 'docker' in lock

    operations = client.get(base + '/operations')
    assert operations.status_code == 200
    ops = operations.json()
    assert {'installer', 'tray', 'plan_backups'} <= set(ops)
    assert ops['installer']['installer_definition'] is True
    assert ops['installer']['build_script'] is True
    assert client.post(base + '/operations/rotate', json={}).status_code == 200

    preset = client.post(base + '/presets/export', json={'name': 'API Preset'})
    assert preset.status_code == 200
    exported = preset.json()
    assert exported['preset']['settings'].get('api_key') is None
    imported = client.post(base + '/presets/import', json={'file': exported['file'], 'apply': False})
    assert imported.status_code == 200
    assert imported.json()['imported']['name'] == 'API-Preset'

    archive = client.get(base + '/export')
    assert archive.status_code == 200
    assert archive.content[:2] == b'PK'
    with zipfile.ZipFile(io.BytesIO(archive.content)) as handle:
        names = handle.namelist()
        assert 'toolforge-transfer.json' in names
        assert 'main.py' in names
        assert not any(name.startswith('.toolforge/') for name in names)


def test_v11_sandbox_status_has_graceful_fallback(client, tmp_path):
    ident, _ = project_with_folder(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    with patch('backend.sandbox.shutil.which', return_value=None):
        result = client.get(base + '/sandbox')
    assert result.status_code == 200
    assert result.json()['docker_available'] is False
    configured = client.post(base + '/settings', json={'sandbox_memory': 'viel'})
    assert configured.status_code == 422
    configured = client.post(base + '/settings', json={'sandbox_memory': '2g', 'sandbox_cpus': 1.5,
                                                       'sandbox_pids': 128, 'sandbox_ports': '8000:8000'})
    assert configured.status_code == 200, configured.text
    assert configured.json()['settings']['sandbox_ports'] == '8000:8000'


def test_v11_event_routes_are_registered(client, tmp_path):
    project_with_folder(client, tmp_path)
    paths = {route.path for route in client.app.routes}
    assert '/api/events' in paths
    assert '/api/projects/{ident}/pilot/events' in paths
    # The stream format and hub delivery are covered by EventHubTests without
    # keeping an infinite HTTP stream open inside the synchronous test client.
