import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

from toolforge_pilot import benchmarks, environments, operations, planning, project_index, research, scenarios, task_graph
from toolforge_pilot.core import validate_plan
from backend.events import EventHub, stream

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads((ROOT / 'examples/demo_plan.json').read_text(encoding='utf-8'))


class ProjectIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def test_incremental_symbols_imports_and_context(self):
        self.write('pkg/__init__.py', 'from .util import helper\nVALUE = 1\n')
        self.write('pkg/util.py', 'TOP = 1\n\nclass Thing:\n    pass\n\ndef helper():\n    return TOP\n')
        self.write('app.py', 'from pkg.util import helper\nimport pkg\nprint(helper())\n')
        index = project_index.refresh(self.project)
        files = index['files']
        self.assertEqual(index['summary']['files'], 3)
        self.assertIn('pkg/util.py', files)
        self.assertEqual(files['pkg/util.py']['language'], 'python')
        names = {row['name'] for row in files['pkg/util.py']['symbols']}
        self.assertTrue({'TOP', 'Thing', 'helper'} <= names)
        self.assertIn('pkg/util.py', files['app.py']['dependencies'])
        self.assertIn('pkg/util.py', files['pkg/__init__.py']['dependencies'])
        result = project_index.context(self.project, 20000)
        self.assertGreater(result['coverage']['chars_included'], 0)
        self.assertEqual(result['manifest']['files_total'], 3)
        self.assertTrue(any(chunk['path'] == 'pkg/util.py' for chunk in result['chunks']))
        self.write('pkg/util.py', 'TOP = 2\n\nclass Thing:\n    pass\n\ndef helper():\n    return TOP\n\ndef second():\n    return 2\n')
        updated = project_index.refresh(self.project)
        self.assertEqual(updated['last_change']['changed'], ['pkg/util.py'])
        self.assertGreaterEqual(updated['last_change']['unchanged'], 2)
        status = project_index.status(self.project)
        self.assertTrue(status['indexed'])
        self.assertIn('second', {row['name'] for row in updated['files']['pkg/util.py']['symbols']})


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_diff_detects_verified_impact_and_backup(self):
        old = demo()
        new = copy.deepcopy(old)
        new['tasks'][0]['checks'][0]['argv'] = ['{python}', '-c', 'print("strenger")']
        new['version'] = 2
        new['tasks'].append({
            'id': 'extra', 'title': 'Zusatz', 'instruction': 'Ergänze eine Hilfe.',
            'depends_on': [], 'files': ['texttool.py'], 'acceptance': ['Hilfe vorhanden'],
            'weight': 1, 'estimate': [1, 2], 'max_repairs': 2,
            'checks': [{'argv': ['{python}', '-c', 'print("ok")'], 'cwd': '.', 'timeout': 30}],
        })
        state = {'plan': old, 'tasks': {'normalize': {'status': 'VERIFIED'}}}
        diff = planning.diff_plans(old, new, state)
        self.assertEqual(diff['old_version'], 1)
        self.assertEqual(diff['new_version'], 2)
        self.assertTrue(diff['requires_confirmation'])
        self.assertEqual(diff['risk'], 'high')
        self.assertEqual(diff['added'][0]['id'], 'extra')
        self.assertTrue(diff['verified_impacted'])
        backup = planning.backup_plan(self.project, state, 'Test')
        self.assertIsNotNone(backup)
        rows = planning.list_backups(self.project)
        self.assertEqual(len(rows), 1)
        loaded = planning.load_backup(self.project, rows[0]['file'])
        self.assertEqual(loaded['plan']['goal'], old['goal'])
        with self.assertRaises(ValueError):
            planning.load_backup(self.project, '../outside.json')


class TaskGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        plan = demo()
        plan['tasks'].append({'id': 'lint', 'title': 'Lint', 'instruction': 'Lint.',
                              'depends_on': [], 'files': ['texttool.py'], 'acceptance': ['sauber'],
                              'weight': 1, 'estimate': [1, 1], 'max_repairs': 1,
                              'checks': [{'argv': ['{python}', '-c', 'print("lint")'], 'cwd': '.', 'timeout': 30}]})
        self.plan = validate_plan(plan)
        self.state = {'plan': self.plan,
                      'tasks': {task['id']: {'status': 'OPEN', 'question': None} for task in self.plan['tasks']}}

    def tearDown(self):
        self.temp.cleanup()

    def test_parallel_conflict_requires_explicit_approval(self):
        self.assertIn('texttool.py', task_graph.blocking_files(self.plan['tasks'], 'lint'))
        self.assertEqual(task_graph.build(self.project, self.state)['nodes'][-1]['approval_missing'], ['texttool.py'])
        graph = task_graph.update(self.project, self.state, {'approve_file': 'texttool.py', 'approved': True})
        node = next(row for row in graph['nodes'] if row['id'] == 'lint')
        self.assertEqual(node['approval_missing'], [])
        self.assertFalse(node['blocked'])
        conflict = next(row for row in graph['conflicts'] if row['file'] == 'texttool.py')
        self.assertTrue(conflict['approved'])
        graph = task_graph.update(self.project, self.state, {'priorities': {'lint': 90}})
        self.assertEqual(next(row for row in graph['nodes'] if row['id'] == 'lint')['priority'], 90)
        task_graph.apply_priorities(self.project, self.state)
        self.assertEqual(next(task for task in self.state['plan']['tasks'] if task['id'] == 'lint')['priority'], 90)

    def test_dependent_shared_file_is_safe(self):
        # cli and export both use texttool.py, but execute in dependency order.
        tasks = [task for task in self.plan['tasks'] if task['id'] != 'lint']
        plan = {**self.plan, 'tasks': tasks}
        state = {'plan': plan, 'tasks': {task['id']: {'status': 'OPEN', 'question': None} for task in tasks}}
        graph = task_graph.build(self.project, state)
        cli = next(row for row in graph['nodes'] if row['id'] == 'cli')
        self.assertNotIn('texttool.py', cli['blocking_conflicts'])
        self.assertTrue(cli['conflicts'])


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        (self.project / 'tests').mkdir()
        (self.project / 'tests' / 'test_sample.py').write_text('def test_one():\n    assert True\n', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def test_test_change_review_and_declared_cli_scenario(self):
        baseline = scenarios.save_test_baseline(self.project)
        self.assertIn('tests/test_sample.py', baseline)
        (self.project / 'tests' / 'test_sample.py').write_text('def test_one():\n    assert 1 == 1\n', encoding='utf-8')
        changes = scenarios.test_changes(self.project, baseline)
        self.assertTrue(changes['review_required'])
        self.assertEqual(changes['changed'], ['tests/test_sample.py'])
        self.assertTrue(changes['diffs'][0]['diff'])
        state = {
            'plan': {'acceptance_scenarios': [
                {'id': 'hello', 'kind': 'cli', 'argv': ['{python}', '-c', "print('OK')"],
                 'cwd': '.', 'expect_text': 'OK', 'expect_code': 0},
            ]},
            'test_baseline': baseline,
        }
        result = scenarios.run(self.project, sys.executable, threading.Event(), lambda text: None, state)
        self.assertTrue(result['passed'])
        self.assertTrue(result['review_required'])
        reviewed = scenarios.mark_reviewed(self.project, 'Teständerung fachlich geprüft.')
        self.assertIsNotNone(reviewed['reviewed_at'])
        self.assertEqual(scenarios.last(self.project)['review_note'], 'Teständerung fachlich geprüft.')

    def test_auto_cli_fallback_is_informational(self):
        (self.project / 'main.py').write_text('print("hilfe")\n', encoding='utf-8')
        state = {'plan': {}, 'test_baseline': {}}
        result = scenarios.run(self.project, sys.executable, threading.Event(), lambda text: None, state)
        self.assertFalse(result['passed'])
        self.assertTrue(result['scenarios'][0]['informational'])
        self.assertTrue(result['scenarios'][0]['auto'])


class FakeStudio:
    def __init__(self):
        self.actual_context = None
        self.unloaded = False

    def inventory(self):
        return [{'key': 'fake/model', 'type': 'llm', 'max_context_length': 32768,
                 'selected_variant': 'Q4_K_M', 'loaded_instances': []}]

    def switch(self, model, context):
        self.actual_context = context
        return 'instance-1'

    def check(self):
        return None

    def chat(self, ident, prompt, temperature, max_tokens):
        return {'response': json.dumps({'solution': 'print(1)', 'checks': ['exit 0'],
                                        'limitations': 'kleine Probe'}),
                'finish_reason': 'stop', 'seconds': 2.0, 'usage': {'completion_tokens': 40}}

    def instances(self):
        return [{'id': 'instance-1', 'config': {'context_length': self.actual_context},
                 'size_bytes': 12 * 1024 * 1024}]

    def unload(self):
        self.unloaded = True


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'TOOLFORGE_PILOT_DATA': self.temp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_repeated_measurement_dispersion_and_cache(self):
        studio = FakeStudio()
        report = benchmarks.measure(studio, 'Kleine Funktion implementieren', 'fake/model', '',
                                    'coding', [4096, 8192], repeats=2)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(len(report['samples']), 4)
        self.assertEqual(report['recommendation']['model'], 'fake/model')
        self.assertTrue(report['recommendation']['tokens_per_second'])
        self.assertTrue(report['recommendation']['vram_peak_bytes'])
        self.assertTrue(report['groups'])
        self.assertTrue(studio.unloaded)
        cached = benchmarks.measure(studio, 'Kleine Funktion implementieren', 'fake/model', '',
                                    'coding', [4096, 8192], repeats=2)
        self.assertTrue(cached['cached'])
        self.assertTrue(benchmarks.cache_rows())
        self.assertTrue(benchmarks.hardware_fingerprint())
        groups = benchmarks._group_stats([
            {'model': 'm', 'context_tokens': 4096, 'score': 50, 'tokens_per_second': 10},
            {'model': 'm', 'context_tokens': 4096, 'score': 70, 'tokens_per_second': 20},
        ])
        self.assertEqual(groups[0]['quality_mean'], 60.0)
        self.assertGreater(groups[0]['quality_stdev'], 0)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_domain_validation_and_cache_hit(self):
        self.assertEqual(research.domains('docs.python.org, https://example.com/path'), ['docs.python.org', 'example.com'])
        with self.assertRaises(ValueError):
            research.domains('not a domain')
        self.assertFalse(research.allowed('http://127.0.0.1/x', []))
        self.assertTrue(research.allowed('https://docs.python.org/3/', ['python.org']))
        query = 'pytest fixture scope'
        key = hashlib.sha256((query.lower() + '|').encode()).hexdigest()[:32]
        entry = {'id': 'cached', 'at': time.time(), 'task': 'manual', 'query': query, 'domains': [],
                 'provider': 'duckduckgo', 'error': '', 'error_hash': '', 'cache_key': key,
                 'results': [{'title': 'Fixtures', 'url': 'https://docs.pytest.org/x', 'host': 'docs.pytest.org',
                              'snippet': 'Snippet', 'evidence': [{'text': 'Fixture scope is explicit.', 'score': 2}]}]}
        path = research.cache_path(self.project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({key: entry}), encoding='utf-8')
        result = research.search(self.project, query)
        self.assertTrue(result['cached'])
        self.assertEqual(result['results'][0]['evidence'][0]['text'], 'Fixture scope is explicit.')
        self.assertTrue(research.cache_rows(self.project))
        self.assertTrue((self.project / '.toolforge' / 'websearch.jsonl').is_file())


class EnvironmentAndOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.env = patch.dict(os.environ, {'TOOLFORGE_PILOT_DATA': str(self.root / 'data')})
        self.env.start()
        (self.root / 'data').mkdir()
        (self.root / 'data' / 'aider-lock.json').write_text(json.dumps({'version': '0.86.2'}), encoding='utf-8')

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_lock_preset_and_project_transfer(self):
        with patch('toolforge_pilot.environments._docker_digest',
                   return_value={'available': False, 'tag': 'toolforge-project:latest', 'image_id': None, 'repo_digests': []}):
            lock = environments.lock_report(sys.executable)
        self.assertTrue(lock['controller']['requirements'])
        self.assertEqual(lock['aider']['installed_version'], '0.86.2')
        self.assertEqual(lock['aider']['pinned'][0]['name'], 'aider-chat')
        settings = {'context_tokens': 20000, 'output_tokens': 2048, 'temperature': 0.2,
                    'model': 'fake/model', 'api_key': 'secret', 'base': 'http://localhost:1234/v1'}
        plan = demo()
        plan['tasks'][0]['requirements'] = [{'manager': 'pip', 'name': 'requests', 'version': '2.32.3'}]
        state = {'plan': plan}
        payload = environments.export_preset(settings, state, lock, 'Test Preset')
        self.assertNotIn('api_key', payload['settings'])
        self.assertTrue(environments.list_presets())
        imported = environments.import_preset(payload)
        self.assertEqual(imported['name'], 'Test-Preset')
        self.assertTrue(imported['task_requirements'])
        (self.project / 'README.md').write_text('# Projekt\n', encoding='utf-8')
        archive = operations.export_project(self.project, self.root / 'export.zip')
        with zipfile.ZipFile(archive) as handle:
            self.assertIn('toolforge-transfer.json', handle.namelist())
        target = self.root / 'target'
        result = operations.import_project(archive, target)
        self.assertTrue(result['imported'])
        self.assertEqual((target / 'README.md').read_text(encoding='utf-8'), '# Projekt\n')
        bad = self.root / 'bad.zip'
        with zipfile.ZipFile(bad, 'w') as handle:
            handle.writestr('../evil.txt', 'x')
            handle.writestr('toolforge-transfer.json', json.dumps({'schema_version': 1, 'files': []}))
        with self.assertRaises(ValueError):
            operations.import_project(bad, self.root / 'bad-target')

    def test_log_rotation(self):
        log = self.project / '.toolforge' / 'diagnostics' / 'errors.jsonl'
        log.parent.mkdir(parents=True)
        log.write_text('x' * 200, encoding='utf-8')
        self.assertTrue(operations.rotate_file(log, max_bytes=100, backups=2))
        self.assertTrue(log.with_name('errors.jsonl.1').is_file())

    def test_pinned_dependencies_and_installer_definition(self):
        root = Path(__file__).resolve().parents[1]
        assert 'aider-chat==0.86.2' in (root / 'requirements-aider.txt').read_text(encoding='utf-8')
        assert (root / 'installer' / 'ToolForge.iss').is_file()
        assert (root / 'installer' / 'build_installer.ps1').is_file()
        status = operations.installer_status()
        self.assertTrue(status['installer_definition'])
        self.assertTrue(status['build_script'])


class EventHubTests(unittest.TestCase):
    def test_session_and_question_events(self):
        hub = EventHub()
        channel = hub.subscribe_session('a')
        hub.publish_session('a', 'snapshot', {'busy': True})
        generator = stream(channel, [('snapshot', {'initial': True})], heartbeat=False)
        first = next(generator)
        second = next(generator)
        generator.close()
        self.assertIn('initial', first)
        self.assertIn('"busy": true', second)
        hub.unsubscribe_session('a', channel)
        hub.publish_questions([{'task': 'a'}])
        hub.publish_questions([{'task': 'a'}])
        self.assertEqual(hub.last_questions, json.dumps([{'task': 'a'}], sort_keys=True))


class SandboxTests(unittest.TestCase):
    def test_resource_and_port_validation(self):
        from backend import sandbox
        self.assertEqual(sandbox.parse_ports('8000:8000, 9000:80'), [(8000, 8000), (9000, 80)])
        with self.assertRaises(ValueError):
            sandbox.parse_ports('80:80')
        settings = {'sandbox_network': 'team', 'sandbox_memory': '2g', 'sandbox_cpus': 1.5,
                    'sandbox_pids': 128, 'sandbox_ports': '8000:8000'}
        sandbox.validate(settings)
        with patch('backend.sandbox.shutil.which', return_value='docker'):
            args = sandbox.command(Path(tempfile.gettempdir()), ['python', 'app.py'],
                                   Path(tempfile.gettempdir()), settings, 'test-job')
        self.assertIn('--memory', args)
        self.assertIn('2g', args)
        self.assertIn('--pids-limit', args)
        self.assertIn('127.0.0.1:8000:8000', args)
        with self.assertRaises(ValueError):
            sandbox.validate({**settings, 'sandbox_memory': 'viel'})


if __name__ == '__main__':
    unittest.main()
