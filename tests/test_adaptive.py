import copy
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from toolforge_pilot.adaptive import OutputGuard, split_task, file_steps, request_steps
from toolforge_pilot.core import Store, Engine, run_process, APP_ROOT
from toolforge_pilot.profiles import profile
from toolforge_pilot.simulation import DemoAdapter


def demo():return json.loads((APP_ROOT/'examples/demo_plan.json').read_text())


class AdaptiveTests(unittest.TestCase):
    def test_user_token_message_chunked(self):
        guard=OutputGuard(2000)
        for chunk in ['Model openai/meta-llama-3.1','-8b-instruct@q8_0 has hit a ','token limit!\n']:
            reason=guard(chunk)
        self.assertEqual(reason,'GUARD_CONTEXT')

    def test_repeated_files_across_chunks(self):
        guard=OutputGuard(10000)
        cycle='backend/main.py\n```python\nprint("hello")\n```\n'
        self.assertFalse(guard(cycle));self.assertFalse(guard(cycle))
        self.assertEqual(guard(cycle),'GUARD_REPEAT')

    def test_repeated_code_without_filename(self):
        guard=OutputGuard(10000)
        block='\n'.join('unique_long_statement_'+str(i) for i in range(12))+'\n'
        guard(block);guard(block)
        self.assertEqual(guard(block),'GUARD_REPEAT')

    def test_normal_code_not_rejected(self):
        g=OutputGuard(2048,['app.py'])
        self.assertFalse(g('app.py\n```python\n'+''.join(f'def f{i}(): return {i}\n' for i in range(100))+'```\n'))

    def test_scope_and_output(self):
        self.assertEqual(OutputGuard(2048,['a.py'])('unrelated.py\n'),'GUARD_SCOPE')
        self.assertEqual(OutputGuard(256)('x'*9000),'GUARD_OUTPUT')

    def test_guard_kills_process_before_timeout(self):
        start=time.monotonic()
        r=run_process([sys.executable,'-u','-c','import time;print("has hit a token limit!",flush=True);time.sleep(20)'],Path('.'),10,threading.Event(),output_guard=OutputGuard(2048))
        self.assertEqual(r['reason'],'GUARD_CONTEXT');self.assertLess(time.monotonic()-start,5)

    def test_gate_preserves_all_original_checks_and_dependencies(self):
        plan=demo();plan['tasks'][0]['files']=['a.py','b.py']
        original=copy.deepcopy(plan)
        new=split_task(plan,'normalize',file_steps(plan['tasks'][0]),'GUARD_REPEAT')
        gate=next(t for t in new['tasks'] if t['id']=='normalize')
        for field in ['instruction','checks','acceptance']:self.assertEqual(gate[field],plan['tasks'][0][field])
        self.assertEqual(next(t for t in new['tasks'] if t['id']=='cli')['depends_on'],['normalize'])
        self.assertEqual(plan,original)
        self.assertEqual(len([t for t in new['tasks'] if t.get('adaptive_part')]),2)

    def test_replanning_is_bounded_across_descendants(self):
        plan=demo();plan['tasks'][0]['files']=['a.py','b.py']
        plan=split_task(plan,'normalize',file_steps(plan['tasks'][0]),'x')
        child=plan['tasks'][0]
        steps=[{'file':'a.py','instruction':'Implement first small function'}, {'file':'a.py','instruction':'Implement second small function'}]
        plan=split_task(plan,child['id'],steps,'x')
        with self.assertRaises(ValueError):split_task(plan,plan['tasks'][0]['id'],steps,'x')

    def test_model_replanner_contract_and_token_bound(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'steps':[{'file':'texttool.py','instruction':'Implement normalization of whitespace'},{'file':'texttool.py','instruction':'Handle empty input and uppercase conversion'}]})}}]}).encode()
        with patch('toolforge_pilot.adaptive.urllib.request.urlopen',return_value=Response()) as http:
            steps=request_steps('http://localhost:1234/v1','key','model',demo()['tasks'][0],'error',profile({'context_tokens':4096,'output_tokens':1024}))
        payload=json.loads(http.call_args.args[0].data)
        self.assertEqual(len(steps),2);self.assertEqual(payload['max_tokens'],1024)
        self.assertFalse(payload['stream'])

    def test_guard_replans_and_resumes_without_resetting_budget(self):
        class Adapter(DemoAdapter):
            calls=0
            def replan(self,task,error):return [{'file':'texttool.py','instruction':'Implement normalization of whitespace'}, {'file':'texttool.py','instruction':'Check empty input handling and uppercase conversion'}]
            def run(self,project,task,*args,**kwargs):
                self.calls+=1
                if self.calls==1:return {'code':-9,'output':'context window exceeded','reason':'GUARD_CONTEXT','seconds':.01}
                if task.get('adaptive_part'):
                    (project/'texttool.py').write_text('def normalize_text(text):\n    if not isinstance(text, str): raise TypeError("str required")\n    return text.strip().lower()\n')
                    return {'code':0,'output':'','reason':'','seconds':.01}
                return super().run(project,task,*args,**kwargs)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'p';target.mkdir();store=Store(target,root/'s')
            try:
                store.set_plan(demo());adapter=Adapter();Engine(store,adapter,sys.executable).run(1)
                self.assertEqual(store.state['status'],'BUDGET')
                self.assertEqual(store.state['session_used'],1)
                self.assertEqual(len(store.state['plan']['replanning']),1)
                Engine(store,adapter,sys.executable).run(10)
                self.assertEqual(store.state['status'],'DONE')
                self.assertEqual(len(store.state['plan']['replanning']),1)
                parts=[row for ident,row in store.state['tasks'].items() if '_r' in ident]
                self.assertEqual([row['attempts'] for row in parts],[1,1])
            finally:store.close()

    def test_partial_success_never_completes_integration(self):
        class Partial:
            model='TEST';key=''
            def run(self,project,task,*args,**kwargs):
                if task.get('adaptive_part'):(project/'texttool.py').write_text('x=1\n')
                return {'code':0,'reason':'','seconds':.01,'output':'done'}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'p';target.mkdir();store=Store(target,root/'s')
            try:
                plan=demo();plan=split_task(plan,'normalize',[{'file':'texttool.py','instruction':'Small change one'},{'file':'texttool.py','instruction':'Small change two'}],'test')
                store.set_plan(plan);Engine(store,Partial(),sys.executable).run(15)
                self.assertEqual(store.state['status'],'WAITING')
                self.assertNotEqual(store.state['tasks']['normalize']['status'],'VERIFIED')
            finally:store.close()

    def test_bad_model_replans_rejected(self):
        cases=[{'steps':[{'file':'../escape.py','instruction':'Implement a small function'}]*2},
               {'steps':[{'file':'texttool.py','instruction':'Same repeated instruction'}]*2}, {'steps':[]}]
        for payload in cases:
            class Response:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def read(self,n):return json.dumps({'choices':[{'message':{'content':json.dumps(payload)}}]}).encode()
            with patch('toolforge_pilot.adaptive.urllib.request.urlopen',return_value=Response()):
                with self.assertRaises(ValueError):request_steps('http://localhost:1234/v1','key','m',demo()['tasks'][0],'x',profile())
