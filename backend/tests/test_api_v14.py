import json
from types import SimpleNamespace
from unittest.mock import patch

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


def project(client, tmp_path, name='V14'):
    folder = tmp_path / name
    folder.mkdir()
    ident = client.post('/api/projects', json={'name': name}).json()['id']
    assert client.post(f'/api/projects/{ident}/folder', json={'path': str(folder)}).status_code == 200
    return ident, folder, client.app.state.pilot.get(str(folder.resolve()))


def test_collaboration_roles_use_qualified_keys_and_runtime_updates(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    configured = client.post(base + '/settings', json={'source_mode': 'free_local'})
    assert configured.status_code == 200, configured.text

    def models(source):
        return [{'id': 'model-' + source, 'name': source, 'type': 'llm'}]

    with patch.object(session, 'models', side_effect=models):
        inventory = client.get(base + '/collaboration/models')
    assert inventory.status_code == 200, inventory.text
    payload = inventory.json()
    keys = {row['key'] for row in payload['models']}
    assert keys == {'free::model-free', 'local::model-local'}
    assert payload['settings']['handoff_enabled'] is True
    assert payload['settings']['review_min_approvals'] == 1

    accepted = client.post(base + '/settings', json={
        'handoff_models': ['local::model-local'], 'review_models': ['free::model-free'],
        'handoff_after_failures': 3, 'review_min_approvals': 2})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['settings']['handoff_models'] == ['local::model-local']

    updated = client.post(base + '/runtime/options', json={
        'review_models': ['local::model-local'], 'review_enabled': False,
        'handoff_after_failures': 1})
    assert updated.status_code == 200, updated.text
    assert updated.json()['settings']['review_models'] == ['local::model-local']
    assert updated.json()['settings']['review_enabled'] is False

    assert client.post(base + '/settings', json={'handoff_models': ['api::x']}).status_code == 422
    assert client.post(base + '/settings', json={'review_min_approvals': 9}).status_code == 422
    assert client.post(base + '/runtime/options', json={'review_strict': 'yes'}).status_code == 422


def test_preflight_options_expose_role_picker_and_skip_flag(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    studio = SimpleNamespace(prefix=False,
                             inventory=lambda: [{'key': 'model-a'}],
                             alternatives=lambda: [{'source': 'local', 'blocked': False}],
                             is_blocked=lambda key: False)
    with patch.object(session, 'preflight_studio', return_value=studio), \
            patch.object(session, 'collaboration_models', return_value={
                'models': [{'key': 'model-a'}], 'prefix': False, 'sources': ['local'],
                'blocked_message': '', 'errors': {},
                'handoff_models': [], 'review_models': [],
                'settings': {'handoff_enabled': True, 'review_enabled': True,
                             'handoff_after_failures': 2, 'review_min_approvals': 1,
                             'review_strict': True, 'skip_preflight': False,
                             'handoff_models': [], 'review_models': []}}):
        options = client.post(base + '/preflight/options', json={'kind': 'coding'})
    assert options.status_code == 200, options.text
    body = options.json()
    assert body['handoff_models'] == [] and body['review_models'] == []
    assert body['role_settings']['skip_preflight'] is False
    assert body['collaboration']['models'][0]['key'] == 'model-a'

    assert client.post(base + '/settings', json={'skip_preflight': True}).status_code == 200
    session.check_preflight()  # must not require a preflight report


def test_preflight_validates_role_models_against_live_inventory(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    studio = SimpleNamespace(prefix=False,
                             inventory=lambda: [{'key': 'model-a'}],
                             alternatives=lambda: [{'source': 'local', 'blocked': False}],
                             is_blocked=lambda key: False)
    with patch.object(session, 'preflight_studio', return_value=studio):
        result = client.post(base + '/preflight', json={
            'goal': 'Test', 'candidates': ['model-a'], 'judge': 'model-a',
            'handoff_models': ['local::missing']})
    assert result.status_code == 422
    assert 'nicht verfügbar' in result.json()['detail']


def test_project_memory_lists_notes_clears_and_can_be_disabled(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    session.store.memory.add('failure', subject='Alter Fehler', detail='a.py konnte nicht geparst werden.',
                             task='a', model='local::small', files=['a.py'])
    status = client.get(base + '/memory')
    assert status.status_code == 200, status.text
    body = status.json()
    assert body['count'] == 1 and body['entries'][0]['subject'] == 'Alter Fehler'

    note = client.post(base + '/memory', json={'action': 'note', 'text': 'Immer pytest verwenden.'})
    assert note.status_code == 200, note.text
    assert note.json()['count'] == 2

    disabled = client.post(base + '/settings', json={'memory_enabled': False})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()['settings']['memory_enabled'] is False

    cleared = client.post(base + '/memory', json={'action': 'clear'})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()['count'] == 0
    assert client.post(base + '/memory', json={'action': 'unknown'}).status_code == 422


def test_pinned_bridge_route_rejects_unknown_source(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    assert client.get(f'/api/projects/{ident}/opencode/v1/source/nope/models').status_code == 404


def test_sandbox_status_distinguishes_cli_and_daemon(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    failed = SimpleNamespace(returncode=1, stdout='', stderr='pipe dockerDesktopLinuxEngine missing')
    with patch('backend.sandbox.shutil.which', return_value='docker'), \
            patch('backend.sandbox.subprocess.run', return_value=failed):
        status = client.get(base + '/sandbox')
    assert status.status_code == 200
    body = status.json()
    assert body['docker_cli'] is True
    assert body['docker_available'] is False and body['daemon_available'] is False
    assert 'dockerDesktopLinuxEngine' in body['daemon_error']


def test_sandbox_build_rejects_unreachable_daemon_immediately(client, tmp_path):
    ident, folder, session = project(client, tmp_path)
    base = f'/api/projects/{ident}/pilot'
    with patch('backend.sandbox.shutil.which', return_value='docker'), \
            patch('backend.sandbox.daemon_status',
                  return_value={'available': False, 'version': '', 'error': 'DAEMON DOWN'}):
        result = client.post(base + '/sandbox/build', json={})
    assert result.status_code == 422
    assert 'DAEMON DOWN' in result.json()['detail']
