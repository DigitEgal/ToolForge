import io
import json
import os
from pathlib import Path
import sys
import threading
import time
import zipfile
from unittest.mock import patch
import pytest
from backend.pilot_service import Session
from backend.workspace import Workspace
from backend.workflows import example,execute,validate_workflow,xlsx_bytes,acceptance

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA',str(tmp_path/'controller'))
    folder=tmp_path/'project';folder.mkdir();session=Session(folder)
    try:yield Workspace(session)
    finally:session.close()

def wait(ws):
    end=time.monotonic()+10
    while ws.session.busy and time.monotonic()<end:time.sleep(.02)
    assert not ws.session.busy
    return ws.job

def test_save_conflict_backup_and_traversal(workspace):
    ws=workspace;doc=ws.save('src/main.py','print(1)\n',None)
    assert ws.read('src/main.py')['revision']==doc['revision']
    with pytest.raises(ValueError):ws.save('src/main.py','print(2)',None)
    saved=ws.save('src/main.py','print(3)',doc['revision'])
    assert list((ws.root/'.toolforge/editor-backups').glob('*/src/main.py'))
    (ws.root/'src/main.py').write_text('external')
    with pytest.raises(ValueError):ws.save('src/main.py','clobber',saved['revision'])
    for name in ('../escape.py','.env','.git/config','CON.py'):
        with pytest.raises(ValueError):ws.save(name,'x',None)

def test_editor_rejects_binary_and_busy(workspace):
    ws=workspace;(ws.root/'image.bin').write_bytes(b'\x00abc')
    with pytest.raises(ValueError):ws.read('image.bin')
    ws.session.maintenance=True
    with pytest.raises(ValueError):ws.save('x.py','x',None)
    ws.session.maintenance=False

def test_python_job_outputs_and_stop(workspace):
    ws=workspace;ws.save('hello.py','print("Hello runner",flush=True)',None)
    ws.start({'kind':'python','path':'hello.py'})
    assert wait(ws)['status']=='done';assert 'Hello runner' in ws.job['output']
    ws.save('sleep.py','import time\nprint("started",flush=True)\ntime.sleep(30)',None)
    ws.start({'kind':'python','path':'sleep.py'})
    while 'started' not in ws.job['output']:time.sleep(.01)
    ws.session.stop(True)
    assert wait(ws)['status']=='stopped'

def test_git_commit_and_diff(workspace):
    ws=workspace;ws.save('main.py','print(1)\n',None)
    assert not ws.git_status()['initialized']
    assert ws.git_action({'action':'init'})['initialized']
    result=ws.git_action({'action':'commit','files':['main.py'],'message':'Initial tool','name':'Test User','email':'test@example.test'})
    assert 'Initial tool' in result['history']
    (ws.root/'main.py').write_text('print(2)\n')
    assert '+print(2)' in ws.git_status()['diff']

def test_git_does_not_commit_unselected_staged_changes(workspace):
    ws=workspace;ws.git_action({'action':'init'})
    for name in ('a.py','b.py'):ws.save(name,'print(1)',None)
    ws.git(['add','b.py'])
    ws.git_action({'action':'commit','files':['a.py'],'message':'Only A','name':'Test','email':'test@example.test'})
    assert ws.git(['ls-tree','--name-only','HEAD']).strip()=='a.py'
    assert 'b.py' in ws.git(['diff','--cached','--name-only'])

def test_workflow_acceptance(workspace):
    result=acceptance(workspace.root,sys.executable,threading.Event(),lambda text:None)
    assert result['code']==0,result
    assert [n['rows'] for n in result['nodes']]==[3,3,2,2]
    assert (workspace.root/result['nodes'][-1]['artifact']).is_file()

def test_csv_invalid_width_missing_required_and_overwrite(workspace):
    root=workspace.root;(root/'data').mkdir();source=root/'data/input.csv';flow=example()
    source.write_text('name,email\nBad\n')
    assert execute(root,flow,sys.executable,threading.Event(),lambda x:None)['code']==1
    source.write_text('name,email\nAda,\n')
    assert 'Pflichtwert' in execute(root,flow,sys.executable,threading.Event(),lambda x:None)['reason']
    source.write_text('name,email\nAda,a@example.test\n')
    assert execute(root,flow,sys.executable,threading.Event(),lambda x:None)['code']==0
    old=(root/'output/clean.xlsx').read_bytes()
    assert execute(root,flow,sys.executable,threading.Event(),lambda x:None)['code']==1
    assert (root/'output/clean.xlsx').read_bytes()==old

def test_workflow_cycles_and_paths(workspace):
    flow=example();flow['nodes'][1]['input']='export'
    with pytest.raises(ValueError):validate_workflow(flow)
    flow=example();flow['nodes'][0]['config']['path']='../data.csv'
    with pytest.raises(ValueError):validate_workflow(flow)

def test_python_node_contract(workspace):
    workspace.save('tool.py','import argparse,json\np=argparse.ArgumentParser();p.add_argument("--input");p.add_argument("--output");a=p.parse_args();open(a.output,"w").write(json.dumps({"columns":["a"],"rows":[[1]]}))',None)
    flow={'version':1,'nodes':[{'id':'tool','kind':'python','input':None,'config':{'path':'tool.py'}},{'id':'out','kind':'excel','input':'tool','config':{'path':'custom.xlsx'}}]}
    result=execute(workspace.root,flow,sys.executable,threading.Event(),lambda x:None)
    assert result['code']==0,result
    assert result['nodes'][-1]['rows']==1

def test_excel_formula_text_is_not_executed():
    raw=xlsx_bytes({'columns':['text'],'rows':[['=HYPERLINK("https://example.test")'],['Ä & < >']]})
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text=z.read('xl/worksheets/sheet1.xml').decode()
        assert '<f>' not in text and 'inlineStr' in text and '&amp;' in text

def test_ai_preview_requires_explicit_apply_and_stale_revision_rejected(workspace):
    ws=workspace;ws.save('main.py','print(1)\n',None);ws.session.settings['model']='test'
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,n):return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'text':'print(2)\n','summary':'Change value'})}}]}).encode()
    with patch('urllib.request.urlopen',return_value=Response()):proposal=ws.prepare_ai({'path':'main.py','instruction':'Use 2'},threading.Event())['proposal']
    assert ws.read('main.py')['text']=='print(1)\n'
    assert '+print(2)' in proposal['diff']
    assert ws.apply_ai(proposal['id'])['text']=='print(2)\n'
    with pytest.raises(ValueError):ws.apply_ai(proposal['id'])
