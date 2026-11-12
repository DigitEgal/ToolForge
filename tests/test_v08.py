import copy
import json
from pathlib import Path
import sys
import threading
from unittest.mock import patch,Mock
import pytest
from toolforge_pilot.core import Store,Engine,progress,atomic_json
from toolforge_pilot.evidence import mark_verified,invalidate
from toolforge_pilot.recovery import choose_strategy,web_research,safe_query
from backend.pilot_service import Session
from backend.workspace import Workspace

def plan():
    return {'schema_version':1,'version':1,'goal':'Test','tasks':[{'id':n,'title':n,'instruction':'Write '+n,'files':[n+'.txt'],'depends_on':deps,'acceptance':['content OK'],'checks':[{'argv':['{python}','-c','from pathlib import Path; assert Path("'+n+'.txt").read_text()=="OK"']}],'max_repairs':0} for n,deps in [('a',[]),('b',[]),('c',['a'])]]}

@pytest.fixture
def store(tmp_path):
    project=tmp_path/'project';project.mkdir();s=Store(project,tmp_path/'state');s.set_plan(plan())
    yield s;s.close()

def verify_all(s):
    for t in s.state['plan']['tasks']:(s.project/(t['id']+'.txt')).write_text('OK')
    for t in s.state['plan']['tasks']:mark_verified(s,t)

def test_invalidate_only_changed_and_dependents(store):
    verify_all(store);(store.project/'a.txt').write_text('changed')
    assert invalidate(store)=={'a','c'}
    assert store.state['tasks']['b']['status']=='VERIFIED'
    p=progress(store.state);assert p['done']==1 and p['implemented']==3 and p['recheck']==2

def test_unrelated_file_does_not_erase_progress(store):
    verify_all(store);(store.project/'unrelated.txt').write_text('new')
    assert invalidate(store)==set()

def test_plan_extension_preserves_contract_but_changed_instruction_does_not(store):
    verify_all(store);new=copy.deepcopy(store.state['plan']);new['version']+=1
    store.set_plan(new,preserve=True);assert all(r['status']=='VERIFIED' for r in store.state['tasks'].values())
    new['tasks'][0]['instruction']='Changed requirement';store.set_plan(new,preserve=True)
    assert store.state['tasks']['a']['status']=='OPEN' and store.state['tasks']['b']['status']=='VERIFIED'

def test_failure_does_not_reedit_completed_independent_task(store):
    (store.project/'a.txt').write_text('OK');mark_verified(store,store.state['plan']['tasks'][0])
    calls=[]
    class Worker:
        key='';model='test'
        def run(self,project,task,prompt,run_dir,response,*args,**kwargs):
            calls.append(task['id']);response.write_text(json.dumps({'outcome':'needs_input','question':'Please choose'}));return {'code':0,'reason':'','output':'','seconds':0}
    Engine(store,Worker(),sys.executable).run(5)
    assert 'a' not in calls and store.state['tasks']['a']['status']=='VERIFIED'
    assert set(calls)=={'b','c'}

def test_recovery_does_not_split_every_problem():
    assert choose_strategy('GUARD_REPEAT','repetition')!='split'
    assert choose_strategy('GUARD_CONTEXT','token limit')=='split'
    assert choose_strategy('GUARD_OUTPUT','No module named pandas')!='split'
    assert choose_strategy('GUARD_SCOPE','extra file')!='split'

def test_web_off_makes_no_request(tmp_path):
    with patch.dict(sys.modules,{'ddgs':Mock()}):
        assert web_research(tmp_path,'problem',{'web_search':False})==''
    assert not (tmp_path/'.toolforge/websearch.jsonl').exists()

def test_web_queries_minimal_and_failure_logged(tmp_path):
    client=Mock();client.DDGS.return_value.text.side_effect=RuntimeError('rate limited')
    with patch.dict(sys.modules,{'ddgs':client}):
        assert web_research(tmp_path,'ModuleNotFoundError private project password=abc',{'web_search':True})==''
    row=json.loads((tmp_path/'.toolforge/websearch.jsonl').read_text())
    assert row['error']=='rate limited' and 'password' not in row['query'] and row['provider']=='duckduckgo'
    assert client.DDGS.return_value.text.call_args.kwargs['backend']=='duckduckgo'

def test_diagnostics_redacts(tmp_path):
    from toolforge_pilot.diagnostics import record
    record(tmp_path,'failure','Bearer ABC api_key=secret-value private-actual',['private-actual'])
    text=(tmp_path/'.toolforge/diagnostics/errors.jsonl').read_text()
    assert 'ABC' not in text and 'secret-value' not in text and 'private-actual' not in text

@pytest.fixture
def session(tmp_path,monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA',str(tmp_path/'controller'))
    folder=tmp_path/'project';folder.mkdir();s=Session(folder);s.apply_plan(plan());s.settings['model']='fake'
    yield s;s.close()

def test_pending_pause_can_be_revoked(session):
    session.engine=Engine(session.store,object(),sys.executable)
    session.running=True;session.stop(False)
    assert session.pause_request.is_set() and session.engine.pause.is_set()
    session.cancel_pause();assert not session.pause_request.is_set() and not session.engine.pause.is_set()
    session.running=False

def test_manual_check_install_has_one_shot_permission(session):
    workspace=Workspace(session)
    with patch('backend.workspace.InstallManager') as factory:
        factory.return_value.records=[]
        workspace.start({'kind':'install_checks'});session.worker.join(5)
        assert factory.call_args.args[2]['allow_pip'] is True
        assert session.settings['allow_pip'] is False
        assert [call.args[0]['name'] for call in factory.return_value.install.call_args_list]==['pytest','ruff','mypy']

def test_additive_extension_preserves_verified_work(session):
    verify_all(session.store)
    new=plan();new['tasks']=new['tasks'][1:2]
    new['tasks'][0]['id']='new';new['tasks'][0]['files']=['extra.txt']
    with patch('backend.pilot_service.chat_plan',return_value=new):
        session.queue_improvement('Add an export');session.worker.join(5)
    assert not session.error
    assert len(session.store.state['plan']['tasks'])==4
    assert all(session.store.state['tasks'][n]['status']=='VERIFIED' for n in ['a','b','c'])
    assert session.assistance['pending'][0]['status']=='applied'

def test_extension_can_queue_while_busy_and_bad_plan_preserves_old(session):
    old=copy.deepcopy(session.store.state['plan']);session.running=True
    session.queue_improvement('Add feature')
    assert session.assistance['pending'][0]['status']=='queued'
    with patch('backend.pilot_service.chat_plan',side_effect=ValueError('invalid JSON')):session.apply_pending_improvements()
    assert session.store.state['plan']==old
    assert session.assistance['pending'][0]['status']=='error'
    session.running=False

def test_stale_suggestions_are_not_applied(session):
    session.assistance['suggestions']=[{'id':'a','title':'T','description':'D','acceptance':'A'}]
    session.assistance['source_hash']='old'
    with pytest.raises(ValueError,match='geändert'):session.queue_improvement(selected=['a'])

def test_docker_argv_isolated_and_network_opt_in(tmp_path):
    from backend.sandbox import command
    with patch('backend.sandbox.shutil.which',return_value='docker'):
        args=command(tmp_path,[sys.executable,str(tmp_path/'main.py')],tmp_path,{'sandbox_network':''},'unique')
        assert args[args.index('--network')+1]=='none'
        assert '--privileged' not in args and '--cap-drop' in args
        assert args[-2:]==['python','/workspace/main.py']
        args=command(tmp_path,['python','app.py'],tmp_path,{'sandbox_network':'shared'},'unique')
        assert 'toolforge-shared' in args
        with pytest.raises(ValueError):command(tmp_path,['python'],tmp_path,{'sandbox_network':'--host'},'unique')

def test_docker_container_removed_on_timeout(tmp_path):
    from backend.sandbox import run
    with patch('backend.sandbox.shutil.which',return_value='docker'),patch('backend.sandbox.run_process',return_value={'code':1,'reason':'TIMEOUT'}),patch('backend.sandbox.subprocess.run') as cleanup:
        run(tmp_path,['python','main.py'],tmp_path,1,threading.Event(),lambda x:None,{'sandbox':True})
    assert cleanup.call_args.args[0][1:3]==['rm','-f']

def test_help_covers_requested_features():
    from backend.assistance import help_documents
    docs=help_documents();text='\n'.join(d['text'] for d in docs)
    for word in ['Vorabcheck','Verbesserungen','DuckDuckGo','Sandbox','Pause zurücknehmen','Stop_ToolForge']:
        assert word in text

def test_runtime_flags_apply_at_next_task_boundary(session):
    session.engine=Engine(session.store,object(),sys.executable,install_policy=dict(session.settings))
    session.running=True
    session.runtime_options({'debug_logging':True,'web_search':True})
    assert not session.engine.policy['debug_logging']
    session.before_cycle()
    assert session.engine.policy['debug_logging'] and session.engine.policy['web_search']
    with pytest.raises(ValueError):session.runtime_options({'allow_pip':True})
    session.running=False

def test_sandbox_does_not_rewrite_python_code_escapes(tmp_path):
    from backend.sandbox import command
    source='print("hello\\nworld")'
    with patch('backend.sandbox.shutil.which',return_value='docker'):
        args=command(tmp_path,['python','-c',source],tmp_path,{},'test')
    assert args[-1]==source

def test_setup_installs_separate_aider_and_validates(tmp_path):
    import setup_toolforge as setup
    with patch.object(setup,'ROOT',tmp_path),patch('setup_toolforge.venv.EnvBuilder') as env,patch('setup_toolforge.subprocess.run') as run,patch('toolforge_pilot.core.AiderAdapter.probe') as probe:
        setup.main()
    calls=[call.args[0] for call in run.call_args_list]
    assert any(str(tmp_path/'requirements-aider.txt') in args and '--python' in args for args in calls)
    assert any(args[-3:]==['-m','aider','--version'] for args in calls)
    probe.assert_called_once()
    assert '.aider-venv' in (tmp_path/'setup-runtime.json').read_text()

def test_restoration_of_working_model_even_when_assistance_fails(session):
    from backend.assistance import AssistanceMixin
    from toolforge_pilot.preflight import Studio
    session.settings['model']='old-instance'
    inventory=[{'key':'old','type':'llm','max_context_length':32768,'loaded_instances':[{'id':'old-instance','config':{'context_length':20000}}]}, {'key':'new','type':'llm','max_context_length':32768,'loaded_instances':[]}]
    with patch.object(Studio,'inventory',return_value=inventory),patch.object(Studio,'switch',side_effect=['new-instance','restored-instance']) as switch:
        with pytest.raises(RuntimeError):session.with_model('new',lambda _:(_ for _ in ()).throw(RuntimeError('bad response')))
    assert switch.call_args_list[-1].args==('old',20000)
    assert session.settings['model']=='restored-instance'

def test_non_model_work_can_run_while_model_lock_is_held(session):
    from toolforge_pilot.preflight import MODEL_LOCK
    called=[]
    MODEL_LOCK.acquire()
    try:
        session.background(lambda:called.append(True),model_lock=False)
        session.worker.join(5)
        assert called==[True] and not session.error
    finally:MODEL_LOCK.release()
