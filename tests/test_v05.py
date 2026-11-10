import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from toolforge_pilot.core import Store,Engine,APP_ROOT,AiderAdapter
from toolforge_pilot.profiles import parse_plan_response,chat_plan,profile
from backend.lifecycle import preview,remove


def demo():return json.loads((APP_ROOT/'examples/demo_plan.json').read_text())

def independent_plan():
    tasks=[]
    for ident,deps in [('a',[]),('b',[]),('c',['a'])]:
        tasks.append({'id':ident,'title':ident,'instruction':'Create '+ident+'.txt','files':[ident+'.txt'],'depends_on':deps,'acceptance':['File contains OK'], 'checks':[{'argv':['{python}','-c',f'from pathlib import Path; assert Path("{ident}.txt").read_text()=="OK"']}], 'max_repairs':1})
    return {'schema_version':1,'version':1,'goal':'Independent tasks','tasks':tasks}

class V05(unittest.TestCase):
    def test_plan_accepts_prose_and_fence(self):
        self.assertEqual(parse_plan_response('Hier ist dein Plan:\n```json\n'+json.dumps(demo())+'\n```'),demo())
    def test_generation_repairs_invalid_response(self):
        class Response:
            def __init__(self,text):self.text=text
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps({'choices':[{'message':{'content':self.text}}]}).encode()
        audit=[]
        with patch('toolforge_pilot.profiles.urllib.request.urlopen',side_effect=[Response('no json'),Response(json.dumps(demo()))]) as http:
            result=chat_plan('http://local/v1','key','m','Goal',profile(),lambda *x:audit.append(x))
        self.assertEqual(result,demo());self.assertEqual(http.call_count,2);self.assertTrue(audit[0][2]);self.assertFalse(audit[1][2])
    def test_invalid_plan_does_not_invent_checks(self):
        plan=demo();plan['tasks'][0]['checks']=[]
        with self.assertRaises(ValueError):parse_plan_response(json.dumps(plan))

    def test_question_defers_and_answer_reprioritizes(self):
        order=[]
        class Worker:
            model='fake';key=''
            def run(worker,project,task,prompt,run_dir,response,stop,log,**kwargs):
                order.append(task['id'])
                if task['id']=='a' and 'DECIDED' not in prompt:
                    response.write_text(json.dumps({'outcome':'needs_input','question':'Which format should a use?','run_id':'wrong-id','task_id':'wrong-task'}))
                else:
                    (project/(task['id']+'.txt')).write_text('OK')
                    response.write_text(json.dumps({'outcome':'changes_proposed','summary':'done'}))
                    if task['id']=='b':engine.enqueue_answer('a','DECIDED')
                return {'code':0,'output':'','reason':'','seconds':.01}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'p';project.mkdir();store=Store(project,root/'state')
            try:
                store.set_plan(independent_plan());engine=Engine(store,Worker(),sys.executable);engine.run(10)
                self.assertEqual(order,['a','b','a','c']);self.assertEqual(store.state['status'],'DONE')
            finally:store.close()

    def test_multiple_questions_visible_in_state(self):
        class Worker:
            model='fake';key=''
            def run(worker,project,task,prompt,run_dir,response,*args,**kwargs):
                response.write_text(json.dumps({'outcome':'needs_input','question':'Which format for '+task['id']+'?'}))
                return {'code':0,'output':'','reason':'','seconds':.01}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'p';project.mkdir();store=Store(project,root/'s')
            try:
                store.set_plan(independent_plan());Engine(store,Worker(),sys.executable).run(10)
                self.assertEqual(store.state['status'],'WAITING')
                self.assertTrue(store.state['tasks']['a']['question']);self.assertTrue(store.state['tasks']['b']['question'])
                self.assertEqual(store.state['tasks']['c']['attempts'],0)
            finally:store.close()

    def test_pytest_uses_project_python(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'p';project.mkdir();store=Store(project,root/'s')
            try:
                engine=Engine(store,object(),sys.executable);plan=independent_plan();plan['tasks'][0]['checks']=[{'argv':['pytest','test_main.py']}]
                with patch('toolforge_pilot.core.run_process',return_value={'code':0,'reason':'','output':''}) as run:engine.checks(plan['tasks'][:1])
                self.assertEqual(run.call_args.args[0][:3],[sys.executable,'-m','pytest'])
            finally:store.close()

    def test_local_cleanup_retains_shared_environment(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.toolforge').mkdir();(root/'.toolforge/installations.json').write_text(json.dumps([{'manager':'npm','name':'typescript','success':True}]))
            first={'id':'a','name':'A','folder_path':str(root)};other={'id':'b','name':'B','folder_path':str(root)}
            result=preview(first,[first,other]);self.assertFalse(result['packages'][0]['eligible']);self.assertFalse(result['folder_removal_allowed'])
    def test_global_cleanup_requires_confirmation_and_checks_archived_references(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('a','b'):
                folder=root/name/'.toolforge';folder.mkdir(parents=True)
                (folder/'installations.json').write_text(json.dumps([{'manager':'choco','name':'git','success':True}]))
            a={'id':'a','name':'A','folder_path':str(root/'a')};b={'id':'b','name':'B','folder_path':str(root/'b'),'archived':True}
            self.assertFalse(preview(a,[a,b])['packages'][0]['global_candidate'])
            self.assertTrue(preview(a,[a])['packages'][0]['global_candidate'])
            with patch('backend.lifecycle.data_root',return_value=root/'controller'),patch('backend.lifecycle.run_process') as run:
                (root/'controller').mkdir();remove(a,[a],cleanup=True)
                run.assert_not_called()

    def test_cleanup_executes_local_package_and_journals(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'p';(project/'.toolforge').mkdir(parents=True)
            (project/'package.json').write_text('{}');(project/'.toolforge/installations.json').write_text(json.dumps([{'manager':'npm','name':'typescript','success':True}]))
            row={'id':'id','name':'Name','folder_path':str(project)}
            with patch('backend.lifecycle.data_root',return_value=root/'controller'),patch('backend.lifecycle.shutil.which',return_value='/bin/npm'),patch('backend.lifecycle.run_process',return_value={'code':0,'reason':'','output':'removed'}) as run:
                report=remove(row,[row],cleanup=True)
            self.assertIn('uninstall',run.call_args.args[0]);self.assertEqual(report['results'][0]['status'],'removed')
            self.assertTrue((project/'.toolforge/uninstallations.json').exists())
            self.assertIn('Paketbereinigung',(project/'README.md').read_text())

    def test_delete_folder_is_recoverable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'p';(project/'.toolforge').mkdir(parents=True);(project/'keep.txt').write_text('important')
            row={'id':'id','name':'Name','folder_path':str(project)}
            with patch('backend.lifecycle.data_root',return_value=root/'controller'):
                report=remove(row,[row],remove_folder=True)
            self.assertFalse(project.exists());self.assertEqual((Path(report['recoverable_folder'])/'keep.txt').read_text(),'important')

    def test_session_accepts_answer_while_other_task_runs(self):
        from backend.pilot_service import Session
        entered=threading.Event();release=threading.Event();order=[]
        class Worker:
            model='fake';key=''
            def __init__(self,*args,**kwargs):pass
            def probe(self):return 'Test adapter'
            def run(self,project,task,prompt,run_dir,response,*args,**kwargs):
                order.append(task['id'])
                if task['id']=='a' and 'ANSWERED' not in prompt:
                    response.write_text(json.dumps({'outcome':'needs_input','question':'Which format?'}))
                else:
                    if task['id']=='b':entered.set();release.wait(5)
                    (project/(task['id']+'.txt')).write_text('OK')
                    response.write_text(json.dumps({'outcome':'changes_proposed'}))
                return {'code':0,'reason':'','output':'','seconds':.01}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'p';project.mkdir()
            with patch.dict('os.environ',{'TOOLFORGE_PILOT_DATA':str(root/'controller')}),patch('backend.pilot_service.AiderAdapter',Worker),patch('backend.pilot_service.discover_models',return_value=[]):
                session=Session(project)
                try:
                    session.apply_plan(independent_plan());session.configure({'model':'fake'});session.start()
                    self.assertTrue(entered.wait(5))
                    result=session.submit_answer('a','ANSWERED');self.assertIn('a',result['pending_answers'])
                    release.set();session.worker.join(10)
                    self.assertEqual(session.store.state['status'],'DONE')
                    self.assertEqual(order,['a','b','a','c']);self.assertEqual(session.pending_answers,{})
                finally:release.set();session.close()
