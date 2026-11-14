import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from toolforge_pilot import collaboration
from toolforge_pilot.core import Store, Engine


def single_plan():
    return {'schema_version': 1, 'version': 1, 'goal': 'Handoff und Prüfung',
            'tasks': [{'id': 'a', 'title': 'Datei a', 'instruction': 'Erzeuge a.txt.',
                       'files': ['a.txt'], 'depends_on': [], 'acceptance': ['a.txt enthält OK'],
                       'checks': [{'argv': ['{python}', '-c',
                                            'from pathlib import Path; assert Path("a.txt").read_text()=="OK"']}],
                       'max_repairs': 3}]}


class Primary:
    source = 'local'
    model = 'primary'
    key = ''

    def __init__(self):
        self.calls = 0

    def run(self, *args, **kwargs):
        self.calls += 1
        return {'code': 1, 'output': 'MODELL KANN NICHT FORTSETZEN', 'reason': '', 'seconds': 0.01}


class Worker:
    def __init__(self, source='api', model='secondary'):
        self.source, self.model, self.key = source, model, ''

    def run(self, project, task, prompt, run_dir, response, stop, log, **kwargs):
        (project / 'a.txt').write_text('OK', encoding='utf-8')
        response.write_text(json.dumps({'schema_version': 1, 'task_id': task['id'],
                                        'run_id': response.stem.removeprefix('response-'),
                                        'outcome': 'changes_proposed', 'summary': 'fertig',
                                        'question': '', 'answer_options': [], 'requested_files': []}),
                           encoding='utf-8')
        return {'code': 0, 'output': 'OK', 'reason': '', 'seconds': 0.01}


class Reviewer:
    source = 'api'
    model = 'reviewer'
    key = ''


def test_role_keys_are_qualified_and_deduplicated():
    rows = collaboration.clean_models(['deepseek', 'free::qwen', 'free::qwen'])
    assert rows == ['local::deepseek', 'free::qwen']
    with pytest.raises(ValueError):
        collaboration.clean_models(['free::qwen'], ['local'])
    with pytest.raises(ValueError):
        collaboration.clean_models(['bad model'])


def test_review_verdict_parser_accepts_wrapped_json():
    value = collaboration.parse_review(
        'Ergebnis:\n```json\n{"verdict":"APPROVE","confidence":1.4,'
        '"reasons":["ok"],"issues":""}\n```')
    assert value['verdict'] == 'approve' and value['confidence'] == 1.0
    assert value['issues'] == []
    with pytest.raises(ValueError):
        collaboration.parse_review('{"verdict":"maybe"}')


def test_engine_hands_task_to_configured_model_and_restores_primary(tmp_path):
    store = Store(tmp_path / 'project', tmp_path / 'state')
    store.set_plan(single_plan())
    primary = Primary()
    engine = Engine(store, primary, sys.executable, install_policy={
        'handoff_enabled': True, 'handoff_models': ['api::secondary'],
        'handoff_after_failures': 2, 'review_enabled': False},
        handoff_factory=lambda key: Worker('api', key.split('::', 1)[1]))
    try:
        engine.run(10)
        state = store.state
        assert state['status'] == 'DONE'
        assert state['tasks']['a']['creator'] == 'api::secondary'
        assert state['tasks']['a']['handoff']['tried'] == ['api::secondary']
        assert engine.adapter is engine.base_adapter
        with store.connect() as con:
            events = [json.loads(row[0]) for row in con.execute(
                "SELECT payload FROM events WHERE kind='handoff'").fetchall()]
        assert events and events[0]['to'] == 'api::secondary'
    finally:
        store.close()


def test_independent_review_excludes_creator_and_gates_completion(tmp_path):
    store = Store(tmp_path / 'project', tmp_path / 'state')
    store.set_plan(single_plan())
    calls = []

    def review_chat(key, prompt):
        calls.append(key)
        return '{"verdict":"approve","confidence":0.9,"reasons":["belegt"],"issues":[]}'

    engine = Engine(store, Worker('local', 'primary'), sys.executable, install_policy={
        'handoff_enabled': False, 'review_enabled': True,
        'review_models': ['local::primary', 'api::reviewer'],
        'review_min_approvals': 1, 'review_strict': True},
        review_chat=review_chat)
    try:
        engine.run(10)
        state = store.state
        assert state['status'] == 'DONE'
        assert calls and set(calls) == {'api::reviewer'}
        assert state['tasks']['a']['review']['status'] == 'approved'
        assert state['tasks']['a']['review']['results'][0]['model'] == 'api::reviewer'
        assert state['final_review']['status'] == 'approved'
    finally:
        store.close()


def test_review_rejection_triggers_repair_then_approval(tmp_path):
    store = Store(tmp_path / 'project', tmp_path / 'state')
    store.set_plan(single_plan())
    verdicts = iter([
        '{"verdict":"reject","confidence":0.8,"reasons":["fehlt"],"issues":["a.txt nicht belegt"]}',
        '{"verdict":"approve","confidence":0.9,"reasons":["ok"],"issues":[]}',
        '{"verdict":"approve","confidence":0.9,"reasons":["ok"],"issues":[]}',
    ])

    def review_chat(key, prompt):
        return next(verdicts)

    engine = Engine(store, Worker('local', 'primary'), sys.executable, install_policy={
        'handoff_enabled': False, 'review_enabled': True, 'review_models': ['api::reviewer'],
        'review_min_approvals': 1, 'review_strict': True},
        review_chat=review_chat)
    try:
        engine.run(10)
        state = store.state
        assert state['status'] == 'DONE'
        assert state['tasks']['a']['review']['status'] == 'approved'
        assert state['tasks']['a']['review_rejections'] == 1
    finally:
        store.close()
