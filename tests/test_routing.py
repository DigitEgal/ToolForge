import json
import time
from unittest.mock import patch

import pytest

from backend.pilot_service import Session
from toolforge_pilot import opencode, routing


class FakeStudio:
    def __init__(self, rows, error=None):
        self.rows = rows
        self.error = error
        self.switched = []

    def inventory(self):
        return [dict(row) for row in self.rows]

    def switch(self, model, context):
        self.switched.append((model, context))
        return model

    def chat(self, model, prompt, temperature, output=1024):
        if self.error:
            raise self.error
        return {'response': 'ok', 'finish_reason': 'stop', 'seconds': 0}

    def unload(self):
        return None


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / 'project'
    folder.mkdir()
    return folder


def row(key, type='llm', context=32000):
    return {'key': key, 'type': type, 'max_context_length': context}


def test_source_order_respects_preset_preference_and_blocks():
    assert routing.source_order('free_local', 'balanced') == ('free', 'local')
    assert routing.source_order('free_local', 'max_quality') == ('local', 'free')
    assert routing.source_order('local_api', 'max_quality') == ('api', 'local')
    assert routing.source_order('local_api', 'cost_saving') == ('local', 'api')
    assert routing.source_order('free_api', 'balanced') == ('free', 'api')
    assert routing.source_order('free', 'max_quality') == ('free',)
    blocked = {'free': time.time() + 600}
    assert routing.source_order('free_local', 'balanced', blocked) == ('local',)


def test_provider_source_mapping_uses_source_names():
    assert routing.provider_source('opencode') == 'free'
    assert routing.provider_source('lmstudio') == 'local'
    assert routing.provider_source('api') == 'api'
    assert routing.source_provider('free') == 'opencode'
    assert routing.source_provider('local') == 'lmstudio'
    assert routing.source_provider('api') == 'api'


def test_source_keys_are_prefixed_only_when_needed():
    assert routing.prefixed('free', 'model', True) == 'free::model'
    assert routing.split_key('free::model', True) == ('free', 'model')
    assert routing.split_key('model', True) == (None, 'model')
    assert routing.split_key('model', False) == (None, 'model')


def test_routing_studio_prefixes_sources_and_blocks_shared_quota():
    local = FakeStudio([row('local-1')])
    free = FakeStudio([row('free-1')], opencode.OpenCodeError(
        'limit', status=429, reason='rate_limit', retry_after_ms=60000, shared_quota=True))
    blocked = {}
    studio = routing.RoutingStudio(('free', 'local'), local_factory=lambda: local,
                                   free_factory=lambda: free, blocked=blocked, prefix=True)
    assert [item['key'] for item in studio.inventory()] == ['free::free-1', 'local::local-1']
    assert studio.source_for('free::free-1') == ('free', 'free-1')
    with pytest.raises(routing.SourceBlocked) as exc:
        studio.chat('free::free-1', 'prompt', .2)
    assert exc.value.retry_after_ms == 60000
    assert blocked['free'] > time.time()
    assert studio.is_blocked('free::free-1')
    assert studio.alternatives()[0]['source'] == 'free'
    assert studio.alternatives()[0]['blocked'] is True
    assert studio.chat('local::local-1', 'prompt', .2)['response'] == 'ok'


def test_routing_studio_keeps_plain_keys_for_single_source():
    studio = routing.RoutingStudio(
        ('free',), free_factory=lambda: FakeStudio([row('free-1')]), prefix=True)
    assert studio.prefix is False
    assert studio.inventory()[0]['key'] == 'free-1'


def test_api_studio_uses_manual_model_when_catalog_hides_it():
    studio = routing.APIStudio('https://api.example.test/v1', 'secret', fallback_model='paid-1')
    studio._request = lambda path, data=None, timeout=None: (_ for _ in ()).throw(ValueError('no catalog'))
    assert [item['key'] for item in studio.inventory(refresh=True)] == ['paid-1']
    assert studio.switch('paid-1', 20000) == 'paid-1'


def test_planning_quota_falls_back_only_to_allowed_local_source(tmp_path, project, monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA', str(tmp_path / 'controller'))
    session = Session(project)
    session.settings.update(source_mode='free_local', preference='balanced', provider='opencode',
                            free_model='free-1', local_model='local-1', model='free-1')
    rows = {
        'free': [{'id': 'free-1', 'type': 'chat', 'loaded_context': None, 'max_context': 32000}],
        'local': [{'id': 'local-1', 'type': 'llm', 'loaded_context': 20000, 'max_context': 32000}],
    }
    session.models = lambda source=None: rows[source or session.active_source()]
    plan = {'schema_version': 1, 'version': 1, 'goal': 'Test', 'tasks': []}
    quota = opencode.OpenCodeError('shared limit', status=429, reason='rate_limit',
                                   retry_after_ms=60000, shared_quota=True)
    with patch('backend.pilot_service.opencode.chat_plan', side_effect=quota), \
            patch('backend.pilot_service.chat_plan', return_value=plan) as local_plan:
        assert session.plan_with_sources('Test') == plan
    assert local_plan.call_count == 1
    assert session.plan_source == 'local'
    assert session.settings['provider'] == 'lmstudio'
    assert session.settings['local_model'] == 'local-1'
    assert session.blocked_sources['free'] > time.time()
    assert session.effective_sources() == ['local']
    session.close()


def test_free_only_quota_never_falls_back_to_local_or_api(tmp_path, project, monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA', str(tmp_path / 'controller'))
    session = Session(project)
    session.settings.update(source_mode='free', preference='balanced', provider='opencode',
                            free_model='free-1', model='free-1')
    session.models = lambda source=None: [
        {'id': 'free-1', 'type': 'chat', 'loaded_context': None, 'max_context': 32000}]
    quota = opencode.OpenCodeError('shared limit', status=429, reason='rate_limit',
                                   retry_after_ms=60000, shared_quota=True)
    with patch('backend.pilot_service.opencode.chat_plan', side_effect=quota), \
            patch('backend.pilot_service.chat_plan', side_effect=AssertionError('local must not run')):
        with pytest.raises(ValueError, match='Planung fehlgeschlagen'):
            session.plan_with_sources('Test')
    assert session.settings['provider'] == 'opencode'
    assert session.blocked_sources['free'] > time.time()
    assert session.effective_sources() == []
    session.close()


def test_configure_validates_preset_and_keeps_per_source_models(tmp_path, project, monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA', str(tmp_path / 'controller'))
    session = Session(project)
    session.configure({'source_mode': 'free_local', 'preference': 'balanced',
                       'local_model': 'local-1', 'free_model': 'free-1', 'model': 'free-1'})
    assert session.settings['provider'] == 'opencode'
    assert session.settings['local_model'] == 'local-1'
    assert session.settings['free_model'] == 'free-1'
    session.configure({'source_mode': 'local_api', 'preference': 'max_quality',
                       'local_model': 'local-1', 'api_model': 'paid-1'})
    assert session.settings['provider'] == 'api'
    assert session.settings['local_model'] == 'local-1'
    assert session.settings['api_model'] == 'paid-1'
    assert session.settings['model'] == 'paid-1'
    session.configure({'source_mode': 'local'})
    assert session.settings['provider'] == 'lmstudio'
    with pytest.raises(ValueError, match='gehört nicht'):
        session.configure({'source_mode': 'local', 'provider': 'opencode'})
    session.close()


def test_snapshot_exposes_source_metadata(tmp_path, project, monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA', str(tmp_path / 'controller'))
    session = Session(project)
    sources = session.snapshot()['sources']
    assert sources['modes']['free_local'] == 'Free & Lokal'
    assert sources['preferences']['max_quality'] == 'MAX Quality'
    assert sources['labels']['free'] == 'OpenCode Free'
    assert json.dumps(sources, ensure_ascii=False)
    session.close()
