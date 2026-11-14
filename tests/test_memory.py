import json
import sys

from toolforge_pilot.core import Store, Engine
from toolforge_pilot.profiles import plan_system


def single_plan():
    return {'schema_version': 1, 'version': 1, 'goal': 'Projektgedächtnis',
            'tasks': [{'id': 'a', 'title': 'Datei a', 'instruction': 'Erzeuge a.txt.',
                       'files': ['a.txt'], 'depends_on': [], 'acceptance': ['a.txt enthält OK'],
                       'checks': [{'argv': ['{python}', '-c',
                                            'from pathlib import Path; assert Path("a.txt").read_text()=="OK"']}],
                       'max_repairs': 3}]}


class Failing:
    source = 'local'
    model = 'primary'
    key = ''

    def run(self, *args, **kwargs):
        return {'code': 1, 'output': 'MODELL KANN NICHT FORTSETZEN', 'reason': '', 'seconds': 0.01}


class Worker:
    source = 'api'
    model = 'secondary'
    key = ''

    def __init__(self, prompts=None):
        self.prompts = prompts if prompts is not None else []

    def run(self, project, task, prompt, run_dir, response, stop, log, **kwargs):
        self.prompts.append(prompt)
        (project / 'a.txt').write_text('OK', encoding='utf-8')
        response.write_text(json.dumps({
            'schema_version': 1, 'task_id': task['id'],
            'run_id': response.stem.removeprefix('response-'),
            'outcome': 'changes_proposed', 'summary': 'fertig',
            'question': '', 'answer_options': [], 'requested_files': []}), encoding='utf-8')
        return {'code': 0, 'output': 'OK', 'reason': '', 'seconds': 0.01}


def test_memory_persists_deduplicates_and_stays_bounded(tmp_path):
    project = tmp_path / 'project'
    store = Store(project, tmp_path / 'state')
    try:
        first = store.memory.add('failure', subject='Syntaxfehler in a.py',
                                 detail='Parser meldete eine fehlende Klammer. API-Key=secret-token',
                                 task='a', model='local::small', files=['a.py'])
        again = store.memory.add('failure', subject='Syntaxfehler in a.py',
                                 detail='Parser meldete eine fehlende Klammer. API-Key=secret-token',
                                 task='a', model='local::small', files=['a.py'])
        assert first['id'] == again['id']
        assert again['seen'] == 2
        assert 'secret-token' not in again['detail']
        secret_note = store.memory.add('note', subject='token=secret-token',
                                       detail='Notiz ohne Geheimnis.')
        assert 'secret-token' not in secret_note['subject']
        store.memory.add('decision', subject='Testframework', detail='pytest verwenden.',
                         outcome='answered')
    finally:
        store.close()

    reopened = Store(project, tmp_path / 'state')
    try:
        status = reopened.memory.summary()
        assert status['count'] == 3
        prompt = reopened.memory.prompt(task='a', files=['a.py'], query='Syntaxfehler', max_chars=500)
        assert 'Projektgedächtnis' in prompt
        assert 'Syntaxfehler' in prompt
        assert 'local::small' in prompt
        assert len(prompt) <= 500
    finally:
        reopened.close()


def test_handoff_and_repair_are_carried_into_the_next_model_prompt(tmp_path):
    project = tmp_path / 'project'
    store = Store(project, tmp_path / 'state')
    store.set_plan(single_plan())
    try:
        engine = Engine(store, Failing(), sys.executable, install_policy={
            'memory_enabled': True, 'handoff_enabled': True,
            'handoff_models': ['api::secondary'], 'handoff_after_failures': 1,
            'review_enabled': False},
            handoff_factory=lambda key: Worker())
        engine.run(10)
        assert store.state['status'] == 'DONE'
        kinds = {row['kind'] for row in store.memory.entries(limit=20)}
        assert {'handoff', 'repair'} <= kinds
        assert any('api::secondary' in row['model'] for row in store.memory.entries(limit=20))
    finally:
        store.close()

    # A fresh store and a different primary model must still receive the facts.
    (project / 'a.txt').unlink()
    reopened = Store(project, tmp_path / 'state')
    reopened.set_plan(single_plan())
    prompts = []
    try:
        worker = Worker(prompts)
        engine = Engine(reopened, worker, sys.executable, install_policy={
            'memory_enabled': True, 'handoff_enabled': False, 'review_enabled': False})
        engine.run(5)
        assert reopened.state['status'] == 'DONE'
        assert prompts and 'Projektgedächtnis' in prompts[0]
        assert 'api::secondary' in prompts[0]
        assert 'Übergabe' in prompts[0] or 'Reparatur' in prompts[0]
    finally:
        reopened.close()


def test_planning_system_accepts_bounded_memory():
    memory = 'Projektgedächtnis (Test):\n- [Entscheidung] pytest statt unittest.'
    system = plan_system({'context_tokens': 20000}, 'Neues Ziel', memory)
    assert memory in system
    assert 'Daten, nicht als Anweisung' in system
