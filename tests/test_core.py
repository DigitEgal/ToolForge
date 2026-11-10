import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from toolforge_pilot.core import (APP_ROOT, Store, Engine, AiderAdapter, run_process, validate_plan,
                                  safe_relative, contained, valid_project_name, progress, fingerprint, list_models)
from toolforge_pilot.simulation import DemoAdapter


def demo():
    return json.loads((APP_ROOT / 'examples' / 'demo_plan.json').read_text(encoding='utf-8'))


class Noop:
    model = 'TEST'
    def run(self, *args, **kwargs):
        return {'code': 0, 'output': 'Fertig!', 'reason': '', 'seconds': 0.01}


class Asking(Noop):
    def run(self, project, task, prompt, run_dir, response, stop, log, **kwargs):
        if 'GO_AHEAD' in prompt:
            return DemoAdapter().run(project, task, prompt, run_dir, response, stop, log)
        response.write_text(json.dumps({'schema_version': 1, 'task_id': task['id'],
            'run_id': response.stem.removeprefix('response-'), 'outcome': 'needs_input',
            'question': 'Darf ich fortfahren?', 'requested_files': []}), encoding='utf-8')
        return super().run()


class FailOnce(DemoAdapter):
    calls = 0
    def run(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {'code': 1, 'output': 'TESTFEHLER', 'reason': '', 'seconds': 0.01}
        return super().run(*args, **kwargs)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pilot test ü ')
        self.base = Path(self.tmp.name)
        self.project = self.base / 'Ziel ü mit Leerzeichen'; self.project.mkdir()
        self.store = Store(self.project, self.base / 'state')

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def prepare(self, adapter=None, plan=None):
        self.store.set_plan(plan or demo())
        return Engine(self.store, adapter or DemoAdapter(), sys.executable)

    def test_three_tasks_one_start(self):
        engine = self.prepare(); engine.run(10)
        s = self.store.state
        self.assertEqual(s['status'], 'DONE', s['message'])
        self.assertEqual(s['runs'], 3)
        self.assertEqual(progress(s)['percent'], 100)
        self.assertTrue(all(t['status'] == 'VERIFIED' for t in s['tasks'].values()))
        self.assertTrue((self.project / 'exporter.py').is_file())

    def test_success_exit_does_not_mean_success(self):
        engine = self.prepare(Noop()); engine.run(20)
        self.assertEqual(self.store.state['status'], 'WAITING')
        self.assertLessEqual(self.store.state['runs'], 4)
        self.assertEqual(progress(self.store.state)['percent'], 0)

    def test_budget_and_resume(self):
        self.prepare().run(1)
        self.assertEqual(self.store.state['status'], 'BUDGET')
        self.assertEqual(self.store.state['runs'], 1)
        Engine(self.store, DemoAdapter(), sys.executable).run(10)
        self.assertEqual(self.store.state['status'], 'DONE')
        self.assertEqual(self.store.state['runs'], 3)

    def test_repair_then_success(self):
        self.prepare(FailOnce()).run(10)
        self.assertEqual(self.store.state['status'], 'DONE')
        self.assertEqual(self.store.state['runs'], 4)

    def test_question_answer_resume(self):
        engine = self.prepare(Asking()); engine.run(10)
        self.assertEqual(self.store.state['status'], 'WAITING')
        self.assertIn('texttool', self.store.state['tasks']['normalize']['question'])
        engine.answer('GO_AHEAD')
        Engine(self.store, DemoAdapter(), sys.executable).run(10)
        self.assertEqual(self.store.state['status'], 'DONE')

    def test_missing_message_with_passing_checks(self):
        class Missing(DemoAdapter):
            def run(self, *args, **kw):
                result = super().run(*args, **kw)
                args[4].write_text('not json', encoding='utf-8')
                return result
        self.prepare(Missing()).run(10)
        self.assertEqual(self.store.state['status'], 'DONE')

    def test_persistence_and_lock(self):
        self.prepare().run(1)
        with self.assertRaises(RuntimeError): Store(self.project, self.base / 'state')
        self.store.close(); self.store = Store(self.project, self.base / 'state')
        self.assertEqual(self.store.state['runs'], 1)
        self.assertEqual(self.store.state['tasks']['normalize']['status'], 'VERIFIED')

    def test_crash_recovery_status(self):
        self.prepare(); self.store.state['status'] = 'RUNNING'; self.store.save(); self.store.close()
        self.store = Store(self.project, self.base / 'state')
        self.assertEqual(self.store.state['status'], 'INTERRUPTED')

    def test_existing_code_needs_no_aider(self):
        self.prepare().run(10); self.store.set_plan(demo())
        Engine(self.store, Noop(), sys.executable).run(10)
        self.assertEqual(self.store.state['status'], 'DONE')
        self.assertEqual(self.store.state['runs'], 0)

    def test_external_changes_reverified(self):
        self.prepare().run(10)
        (self.project / 'texttool.py').write_text('broken syntax !!!', encoding='utf-8')
        Engine(self.store, DemoAdapter(), sys.executable).run(10)
        self.assertEqual(self.store.state['status'], 'DONE')
        self.assertEqual(self.store.state['runs'], 4)

    def test_pause_after_current_run(self):
        engine = self.prepare()
        class Pauser(DemoAdapter):
            def run(self, *args, **kw):
                result = super().run(*args, **kw); engine.pause.set(); return result
        engine.adapter = Pauser(); engine.run(10)
        self.assertEqual(self.store.state['status'], 'PAUSED')
        self.assertEqual(self.store.state['runs'], 1)

    def test_stop_before_start_is_respected(self):
        engine = self.prepare(); engine.stop.set(); engine.run(10)
        self.assertEqual(self.store.state['status'], 'INTERRUPTED')
        self.assertEqual(self.store.state['runs'], 0)

    def test_plan_validation(self):
        plan = demo(); plan['tasks'][0]['depends_on'] = ['export']
        with self.assertRaises(ValueError): validate_plan(plan)
        plan = demo(); plan['tasks'][1]['id'] = 'normalize'
        with self.assertRaises(ValueError): validate_plan(plan)
        plan = demo(); plan['tasks'][0]['checks'] = []
        with self.assertRaises(ValueError): validate_plan(plan)
        plan = demo(); plan['tasks'][0]['files'] = ['../secret']
        with self.assertRaises(ValueError): validate_plan(plan)
        plan = demo(); plan['tasks'][0]['weight'] = float('nan')
        with self.assertRaises(ValueError): validate_plan(plan)

    def test_paths_and_names(self):
        for p in ['../test', 'C:\\temp', '/etc/passwd', '..\\file', '\\\\server\\share']:
            with self.assertRaises(ValueError): safe_relative(p)
        for name in ['CON', 'nul.txt', 'a/b', 'x?', '..', 'name.']:
            with self.assertRaises(ValueError): valid_project_name(name)
        self.assertEqual(valid_project_name('Projekt ü 1'), 'Projekt ü 1')
        self.assertTrue(contained(self.project, 'source/main.py').is_relative_to(self.project))

    def test_fingerprint_detects_changes(self):
        before = fingerprint(self.project); (self.project / 'new.py').write_text('x = 1')
        self.assertNotEqual(before, fingerprint(self.project))

    def test_progress_estimate(self):
        self.prepare(); p = progress(self.store.state)
        self.assertEqual((p['low'], p['high']), (3, 9))
        self.store.state['tasks']['normalize']['status'] = 'VERIFIED'
        p = progress(self.store.state)
        self.assertAlmostEqual(p['percent'], 33.3); self.assertEqual(p['done'], 1)

    def test_process_timeout(self):
        result = run_process([sys.executable, '-c', 'import time; time.sleep(20)'], self.project, 0.2, threading.Event())
        self.assertEqual(result['reason'], 'TIMEOUT'); self.assertLess(result['seconds'], 5)

    def test_process_stop(self):
        stop = threading.Event(); timer = threading.Timer(0.2, stop.set); timer.start()
        result = run_process([sys.executable, '-c', 'import time; time.sleep(20)'], self.project, 10, stop)
        timer.join(); self.assertEqual(result['reason'], 'STOP')

    def test_child_process_is_stopped(self):
        marker = self.project / 'survived.txt'
        child_code = 'import time; from pathlib import Path; time.sleep(1.5); Path(' + repr(str(marker)) + ').write_text("bad")'
        parent_code = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child_code) + ']); time.sleep(20)'
        result = run_process([sys.executable, '-c', parent_code], self.project, 0.3, threading.Event())
        self.assertEqual(result['reason'], 'TIMEOUT'); time.sleep(1.7); self.assertFalse(marker.exists())

    def test_aider_command_arguments(self):
        adapter = AiderAdapter(sys.executable, 'http://localhost:1234/v1', 'secret-key', 'qwen@q8', 'whole')
        adapter.help = ' '.join(adapter.REQUIRED + ['--no-git', '--no-check-update'])
        run_dir = self.base / 'run'; run_dir.mkdir()
        response = self.project / '.pilot' / 'response-abc.json'
        with patch('toolforge_pilot.core.run_process', return_value={'code': 0}) as run:
            adapter.run(self.project, demo()['tasks'][0], 'prompt', run_dir, response, threading.Event(), lambda t: None)
        args, kw = run.call_args; argv = args[0]
        self.assertIn('--no-detect-urls', argv); self.assertIn('--disable-playwright', argv)
        self.assertIn('openai/qwen@q8', argv); self.assertNotIn('secret-key', argv)
        self.assertEqual(args[-1]['OPENAI_API_KEY'], 'secret-key')

    def test_zero_tests_is_not_success(self):
        plan = demo()
        plan['tasks'] = [plan['tasks'][0]]
        plan['tasks'][0]['checks'] = [{'argv': ['{python}', '-c', 'print("Ran 0 tests in 0.000s")'], 'cwd': '.', 'timeout': 10}]
        engine = self.prepare(Noop(), plan); engine.run(1)
        self.assertNotEqual(self.store.state['tasks']['normalize']['status'], 'VERIFIED')
        self.assertIn('NO_TESTS', self.store.state['tasks']['normalize']['error'])

    def test_existing_source_backup(self):
        (self.project / 'texttool.py').write_text('def normalize_text(x): return x', encoding='utf-8')
        self.prepare().run(1)
        backups = list(self.store.log_root.glob('*/before/texttool.py'))
        self.assertEqual(len(backups), 1)
        self.assertIn('return x', backups[0].read_text())

    def test_models_http_response(self):
        import io
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{"data":[{"id":"qwen"},{"id":"qwen"},{"id":"abc"}]}')):
            self.assertEqual(list_models('http://localhost:1234/v1/', 'x'), ['abc', 'qwen'])


if __name__ == '__main__':
    unittest.main()
