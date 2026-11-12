import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, PropertyMock
from toolforge_pilot.core import Store,AiderAdapter,Engine,validate_plan
from toolforge_pilot.profiles import profile,adapt_plan,context_check,ContextBudgetError,discover_models,effective_edit
from toolforge_pilot.installations import InstallManager,InstallBlocked,validate_requirement,diagnose

ROOT=Path(__file__).resolve().parents[1]
def demo():return json.loads((ROOT/'examples/demo_plan.json').read_text())

class Improvements(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir()
    def tearDown(self):self.temp.cleanup()
    def test_headless_metadata_temperature(self):
        adapter=AiderAdapter(sys.executable,'http://localhost:1234/v1','key','unknown-model',model_profile={'context_tokens':4096,'output_tokens':512,'temperature':0.65})
        adapter.help=' '.join(adapter.REQUIRED)
        folder=self.root/'run';folder.mkdir()
        with patch('toolforge_pilot.core.run_process',return_value={'code':0}) as runner:
            adapter.run(self.project,demo()['tasks'][0],'small prompt',folder,self.project/'.pilot/response.json',threading.Event(),lambda x:None)
        argv=runner.call_args.args[0];env=runner.call_args.args[-1]
        for flag in ('--no-fancy-input','--no-pretty','--no-show-model-warnings','--disable-playwright','--no-detect-urls'):self.assertIn(flag,argv)
        self.assertEqual(env['TERM'],'dumb')
        self.assertEqual(argv[argv.index('--max-chat-history-tokens')+1],'1000000000')
        meta=json.loads((folder/'model-metadata.json').read_text())['openai/unknown-model']
        self.assertEqual(meta['max_tokens'],4096)
        settings=json.loads((folder/'model-settings.yml').read_text())[0]
        self.assertEqual(settings['extra_params']['temperature'],0.65)
        self.assertEqual(settings['extra_params']['top_p'],.95)
    def test_small_model_prefers_whole_files_and_top_p_is_kept(self):
        self.assertEqual(profile({'context_tokens':12000,'output_tokens':2048,'temperature':.2,'top_p':.8})['top_p'],.8)
        small=profile({'context_tokens':12000,'output_tokens':2048,'temperature':.2})
        large=profile({'context_tokens':32000,'output_tokens':2048,'temperature':.2})
        self.assertEqual(effective_edit('auto',small,True),'whole')
        self.assertEqual(effective_edit('auto',large,True),'auto')
        self.assertEqual(effective_edit('diff',small,True),'diff')
        self.assertEqual(effective_edit('auto',small,False),'auto')
    def test_loaded_context_not_theoretical(self):
        def get(url,key):
            if url.endswith('/v1/models') and '/api/' not in url:return {'data':[{'id':'m'}]}
            return {'models':[{'key':'m','type':'llm','max_context_length':131072,'loaded_instances':[{'id':'m','config':{'context_length':4096}}]}]}
        with patch('toolforge_pilot.profiles.get_json',side_effect=get):
            m=discover_models('http://localhost:1234/v1','x')[0]
        self.assertEqual(m['loaded_context'],4096);self.assertEqual(m['max_context'],131072)
    def test_model_plan_version_retains_acceptance(self):
        plan=demo();plan['tasks'][0]['files']=['a.py','b.py','c.py']
        adapted,changed=adapt_plan(plan,self.project,profile({'context_tokens':4096,'output_tokens':512,'model':'small'}))
        self.assertTrue(changed);self.assertGreater(len(adapted['tasks']),len(plan['tasks']))
        gate=next(t for t in adapted['tasks'] if t['id']=='normalize')
        self.assertEqual(gate['checks'],plan['tasks'][0]['checks']);self.assertEqual(gate['acceptance'],plan['tasks'][0]['acceptance'])
        self.assertEqual(gate['depends_on'],['normalize_ctx_3'])
        again,changed=adapt_plan(adapted,self.project,adapted['model_profile']);self.assertFalse(changed)
        validate_plan(adapted)
    def test_context_budget_rejects_oversized_file(self):
        (self.project/'large.py').write_text('x=1\n'*10000)
        with self.assertRaises(ContextBudgetError):context_check(self.project,{'files':['large.py']},'prompt',profile({'context_tokens':4096,'output_tokens':512}))
    def test_local_logs_plan_and_auto_import(self):
        store=Store(self.project,self.root/'state');store.set_plan(demo());self.assertTrue(store.log_root.is_relative_to(self.project))
        self.assertTrue((self.project/'.toolforge/active-plan.json').exists());store.close()
        other=Store(self.project,self.root/'new-state');self.assertEqual(other.state['plan']['goal'],demo()['goal']);other.close()
    def test_diagnostics_specific(self):
        self.assertEqual(diagnose("ModuleNotFoundError: No module named 'openpyxl'")['package'],'openpyxl')
        self.assertIn('API-Schlüssel',diagnose('401 Unauthorized')['question'])
        self.assertEqual(diagnose('maximum context length exceeded')['kind'],'context')
    def test_installs_disabled_and_names_validated(self):
        manager=InstallManager(self.project,sys.executable,{},threading.Event(),lambda x:None)
        for engine in ('pip','choco','npm','npx'):
            with self.assertRaises(InstallBlocked):manager.install({'manager':engine,'name':'pytest'})
        for name in ('x;del','--index-url','https://evil','../pkg'):
            with self.assertRaises(ValueError):validate_requirement({'manager':'pip','name':name})
    def test_install_record_readme_and_summary(self):
        manager=InstallManager(self.project,sys.executable,{'allow_npm':True},threading.Event(),lambda x:None)
        with patch('toolforge_pilot.installations.shutil.which',return_value='/bin/npm'),patch('toolforge_pilot.installations.run_process',return_value={'code':0,'reason':'','output':'Installed','seconds':1}):
            self.assertTrue(manager.install({'manager':'npm','name':'typescript','version':'5.0.4'}))
        self.assertIn('typescript',(self.project/'README.md').read_text())
        self.assertIn('typescript',(self.project/'.toolforge/INSTALLATIONS.md').read_text())
        self.assertTrue(json.loads((self.project/'.toolforge/installations.json').read_text())[0]['success'])
    def test_failure_is_recorded(self):
        manager=InstallManager(self.project,sys.executable,{'allow_choco':True},threading.Event(),lambda x:None)
        with patch('toolforge_pilot.installations.shutil.which',return_value='choco'),patch('toolforge_pilot.installations.run_process',return_value={'code':1,'reason':'','output':'Access denied','seconds':1}):
            with self.assertRaises(InstallBlocked):manager.install({'manager':'choco','name':'git'})
        self.assertFalse(manager.records[-1]['success'])
        self.assertIn('fehlgeschlagen',(self.project/'README.md').read_text())
    def test_pip_source_build_failure_retries_newer_wheel(self):
        manager=InstallManager(self.project,sys.executable,{'allow_pip':True},threading.Event(),lambda x:None)
        failed={'code':1,'reason':'','output':'Failed building wheel for Pillow\nRequiredDependencyException: zlib','seconds':1}
        installed={'code':0,'reason':'','output':'Successfully installed Pillow','seconds':1}
        with patch.object(InstallManager,'python',new_callable=PropertyMock,return_value='/fake/python'), \
             patch('toolforge_pilot.installations.interpreter_version',return_value=(3,11)), \
             patch('toolforge_pilot.installations.pypi_compatible_version',return_value='10.4.0'), \
             patch('toolforge_pilot.installations.run_process',side_effect=[failed,installed]) as runner:
            self.assertTrue(manager.install({'manager':'pip','name':'Pillow','version':'8.4.0'}))
        self.assertEqual(manager.last_resolution['version'],'10.4.0')
        self.assertEqual(manager.last_resolution['failed_version'],'8.4.0')
        self.assertEqual(len(manager.records),2)
        self.assertFalse(manager.records[0]['success'])
        self.assertTrue(manager.records[1]['success'])
        self.assertEqual(manager.records[1]['version'],'10.4.0')
        self.assertIn('Pillow==10.4.0',' '.join(runner.call_args_list[1].args[0]))
        self.assertIn('ausgewichen',manager.records[1]['note'])
    def test_diagnose_pip_build_failure(self):
        found=diagnose('ERROR: Failed building wheel for Pillow\nRequiredDependencyException: zlib')
        self.assertEqual(found['kind'],'install_build')
        self.assertEqual(found['package'],'Pillow')
        self.assertIn('Wheel',found['question'])
    def test_install_resolution_versions_plan(self):
        from toolforge_pilot.simulation import DemoAdapter
        store=Store(self.project,self.root/'state')
        try:
            plan=demo();plan['tasks'][0]['requirements']=[{'manager':'pip','name':'PIL','version':'8.4.0'}]
            store.set_plan(plan)
            engine=Engine(store,DemoAdapter(),sys.executable)
            engine.apply_install_resolution(store.state['plan']['tasks'][0],{'package':'Pillow','version':'10.4.0','python':'3.11','reason':'Quelltext-Build fehlgeschlagen','source':'PyPI-Metadaten'})
            row=store.state['plan']['tasks'][0]
            self.assertEqual(row['requirements'][0]['version'],'10.4.0')
            self.assertEqual(store.state['plan']['version'],plan['version']+1)
            self.assertIn('10.4.0',row['instruction'])
            self.assertTrue(store.state['plan_file'])
        finally:store.close()
    def test_explicit_dependency_validation(self):
        plan=demo();plan['tasks'][0]['requirements']=[{'manager':'pip','name':'bad; command'}]
        with self.assertRaises(ValueError):validate_plan(plan)

if __name__=='__main__':unittest.main()

class CheckPolicy(unittest.TestCase):
    def test_install_commands_must_use_audit(self):
        from toolforge_pilot.installations import prepare_check
        for argv in (['python','-m','pip','install','pytest'], ['npm','ci'], ['choco','install','git'], ['npx','--yes','tsc']):
            with self.assertRaises(InstallBlocked): prepare_check(argv)
        # Force the plain npx path so the assertion is independent of an installed Node.js.
        with patch('toolforge_pilot.installations.shutil.which',return_value=None):
            self.assertEqual(prepare_check(['npx','tsc','--noEmit']), ['npx','--no-install','tsc','--noEmit'])
        self.assertEqual(prepare_check(['python','-m','pytest']), ['python','-m','pytest'])
    def test_completed_tasks_retained_on_model_change(self):
        plan=demo();plan['tasks'][0]['files']=['a.py','b.py','c.py']
        adapted,_=adapt_plan(plan,Path('.'),profile({'model':'new','context_tokens':4096,'output_tokens':512}),completed={'normalize'})
        self.assertEqual(adapted['tasks'][0],plan['tasks'][0])
    def test_force_install_after_environment_loss(self):
        with tempfile.TemporaryDirectory() as d:
            manager=InstallManager(Path(d),sys.executable,{'allow_npm':True},threading.Event(),lambda x:None)
            with patch('toolforge_pilot.installations.shutil.which',return_value='/bin/npm'),patch('toolforge_pilot.installations.run_process',return_value={'code':0,'reason':'','output':'Installed','seconds':1}) as run:
                manager.install({'manager':'npm','name':'typescript'})
                manager.install({'manager':'npm','name':'typescript'},force=True)
                self.assertEqual(run.call_count,2)

    def test_runtime_context_narrowing_keeps_checks(self):
        from toolforge_pilot.simulation import DemoAdapter
        class Narrow(DemoAdapter):
            def run(self, project, task, *args, **kwargs):
                if len(task['files']) > 1: raise ContextBudgetError('Too many files')
                return super().run(project, task, *args, **kwargs)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'target';target.mkdir();store=Store(target,root/'state')
            try:
                plan=demo();plan['tasks'][0]['files']=['texttool.py','extra.py'];store.set_plan(plan)
                Engine(store,Narrow(),sys.executable).run(10)
                self.assertEqual(store.state['status'],'DONE')
                self.assertGreater(store.state['plan']['version'],plan['version'])
                self.assertEqual(store.state['plan']['tasks'][0]['checks'],plan['tasks'][0]['checks'])
            finally:store.close()
