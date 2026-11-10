from datetime import datetime
from pathlib import Path
import json
import sqlite3
import time
from uuid import UUID
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app, Database, DEFAULT_DB

HEADERS={'X-ToolForge-Request':'1','Origin':'http://127.0.0.1:8000'}

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('TOOLFORGE_PILOT_DATA',str(tmp_path/'controller'))
    app=create_app(tmp_path/'db.sqlite3')
    with TestClient(app,base_url='http://127.0.0.1:8000',headers=HEADERS) as c:
        yield c

def test_health_and_empty(client):
    assert client.get('/api/health').json()=={'status':'ok'}
    assert client.get('/api/projects').json()==[]
    assert client.get('/api/groups').json()==[]
    assert client.get('/api/workbench').json()['version']=='1.2.0'
    assert client.get('/api/workbench').json()['stage']==12

def test_create_get_list(client):
    result=client.post('/api/projects',json={'name':'  Test ü  ','description':'Beschreibung'})
    assert result.status_code==201
    data=result.json();UUID(data['id']);assert data['name']=='Test ü'
    assert datetime.fromisoformat(data['created_at']).utcoffset().total_seconds()==0
    assert client.get('/api/projects/'+data['id']).json()==data
    assert client.get('/api/projects').json()==[data]

@pytest.mark.parametrize('name',['','   ','a'*101,17,None])
def test_bad_names(client,name):
    assert client.post('/api/projects',json={'name':name}).status_code==422

def test_limits_and_duplicate_names(client):
    assert client.post('/api/projects',json={'name':'a'*100,'description':'x'*2000}).status_code==201
    assert client.post('/api/projects',json={'name':'x','description':'x'*2001}).status_code==422
    a=client.post('/api/projects',json={'name':'Same'}).json()
    b=client.post('/api/projects',json={'name':'Same'}).json()
    assert a['id']!=b['id']
    assert client.get('/api/projects').json()[0]['id']==b['id']

def test_unknown(client):
    assert client.get('/api/projects/not-found').status_code==404

def test_version_and_static_cache_headers(tmp_path):
    dist=tmp_path/'dist';assets=dist/'assets';assets.mkdir(parents=True)
    (dist/'index.html').write_text('<!doctype html><title>ToolForge</title>',encoding='utf-8')
    (assets/'app-abc123.js').write_text('console.log("toolforge")',encoding='utf-8')
    app=create_app(tmp_path/'db.sqlite3',static_dir=dist)
    assert app.version=='1.2.0'
    with TestClient(app,base_url='http://127.0.0.1:8000',headers=HEADERS) as c:
        index=c.get('/')
        assert index.status_code==200 and index.headers['cache-control']=='no-cache'
        asset=c.get('/assets/app-abc123.js')
        assert asset.status_code==200
        assert asset.headers['cache-control']=='public, max-age=31536000, immutable'

def test_origin_and_header(client):
    assert client.post('/api/projects',json={'name':'x'},headers={'Origin':'https://foreign.example'}).status_code==403
    assert client.post('/api/projects',json={'name':'x'},headers={'X-ToolForge-Request':''}).status_code==403
    assert client.get('/api/projects',headers={'Host':'foreign.example'}).status_code==403

def test_persistence_and_sort(tmp_path):
    db=tmp_path/'db.sqlite3'
    with TestClient(create_app(db),base_url='http://127.0.0.1:8000',headers=HEADERS) as c:
        ident=c.post('/api/projects',json={'name':'Persistent'}).json()['id']
    with TestClient(create_app(db),base_url='http://127.0.0.1:8000',headers=HEADERS) as c:
        assert c.get('/api/projects/'+ident).json()['name']=='Persistent'
    with sqlite3.connect(db) as con:
        for ident in ['a','b']:
            con.execute('INSERT INTO projects(id,name,description,created_at) VALUES (?,?,?,?)',(ident,ident,'','9999'))
    assert [r['id'] for r in Database(db).all()][:2]==['b','a']

def test_folder_scan_plan_save_and_restart(client,tmp_path):
    folder=tmp_path/'Test ü folder';folder.mkdir();(folder/'README.md').write_text('Existing project')
    ident=client.post('/api/projects',json={'name':'Folder project'}).json()['id']
    assert client.get(f'/api/projects/{ident}/pilot').status_code==409
    assert client.post(f'/api/projects/{ident}/folder',json={'path':str(folder)}).status_code==200
    snap=client.get(f'/api/projects/{ident}/pilot').json()
    assert 'README.md' in snap['scan']['files']
    assert snap['scan']['documents']['README.md']=='Existing project'
    assert Path(snap['log_folder']).is_relative_to(folder)
    assert client.post(f'/api/projects/{ident}/pilot/demo',json={}).status_code==200
    assert (folder/'.toolforge/active-plan.json').is_file()
    assert list((folder/'.toolforge/plans').glob('*.json'))

def test_settings_and_simulated_browser_run(client,tmp_path):
    folder=tmp_path/'Simulation';folder.mkdir()
    ident=client.post('/api/projects',json={'name':'Simulation'}).json()['id']
    client.post(f'/api/projects/{ident}/folder',json={'path':str(folder)})
    client.post(f'/api/projects/{ident}/pilot/demo',json={})
    result=client.post(f'/api/projects/{ident}/pilot/settings',json={'simulation':True,'budget':10,'api_key':'VERYSECRET','temperature':0.7})
    assert result.status_code==200,result.text
    assert 'VERYSECRET' not in (folder/'.toolforge/settings.json').read_text()
    assert client.post(f'/api/projects/{ident}/pilot/start',json={}).status_code==202
    end=time.time()+30
    while time.time()<end:
        snapshot=client.get(f'/api/projects/{ident}/pilot').json()
        if not snapshot['busy']:break
        time.sleep(.1)
    assert snapshot['state']['status']=='DONE',snapshot
    assert snapshot['progress']['percent']==100
    assert len(list((folder/'.toolforge/logs').glob('*/output.log')))==3

def test_database_migration(tmp_path):
    db=tmp_path/'old.sqlite3'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE projects(id TEXT PRIMARY KEY,name TEXT,description TEXT,created_at TEXT)')
        con.execute("INSERT INTO projects VALUES ('old','Old','','2026-01-01T00:00:00+00:00')")
    Database(db).initialize()
    assert Database(db).get('old')['folder_path'] is None
    assert Database(db).get('old')['group_id'] is None


def test_project_groups_cluster_and_move(client):
    group=client.post('/api/groups',json={'name':'  Buchhaltung  '})
    assert group.status_code==201
    group=group.json();assert group['name']=='Buchhaltung' and group['project_count']==0
    project=client.post('/api/projects',json={'name':'Rechnungen'}).json()
    assert project['group_id'] is None
    moved=client.patch('/api/projects/'+project['id'],json={'group_id':group['id']})
    assert moved.status_code==200 and moved.json()['group_id']==group['id']
    assert client.get('/api/projects/'+project['id']).json()['group_id']==group['id']
    assert client.get('/api/groups').json()[0]['project_count']==1
    assert client.patch('/api/groups/'+group['id'],json={'name':'Finanzen'}).json()['name']=='Finanzen'
    assert client.patch('/api/projects/'+project['id'],json={'group_id':'missing'}).status_code==422
    deleted=client.delete('/api/groups/'+group['id']).json()
    assert deleted=={'removed':True,'projects_ungrouped':1}
    assert client.get('/api/projects/'+project['id']).json()['group_id'] is None

def test_default_db_not_created_by_factory(tmp_path):
    before=DEFAULT_DB.exists()
    create_app(tmp_path/'isolated.sqlite3')
    assert DEFAULT_DB.exists()==before

def test_rename_archive_restore_delete(client):
    project=client.post('/api/projects',json={'name':'Old'}).json();base='/api/projects/'+project['id']
    assert client.patch(base,json={'name':' New '}).json()['name']=='New'
    assert client.patch(base,json={'archived':True}).json()['archived'] is True
    assert client.post(base+'/pilot/start',json={}).status_code==409
    assert client.patch(base,json={'archived':False}).json()['archived'] is False
    assert client.get(base+'/deletion-preview').status_code==200
    assert client.post(base+'/delete',json={'confirm_name':'wrong'}).status_code==422
    assert client.post(base+'/delete',json={'confirm_name':'New'}).status_code==200
    assert client.get(base).status_code==404

def test_generated_plan_saved_and_failure_visible(client,tmp_path):
    folder=tmp_path/'generated';folder.mkdir()
    ident=client.post('/api/projects',json={'name':'Generated'}).json()['id'];base=f'/api/projects/{ident}'
    client.post(base+'/folder',json={'path':str(folder)})
    client.post(base+'/pilot/settings',json={'model':'test'})
    from toolforge_pilot.core import APP_ROOT
    plan=json.loads((APP_ROOT/'examples/demo_plan.json').read_text(encoding='utf-8'))
    with patch('backend.pilot_service.chat_plan',return_value=plan):
        assert client.post(base+'/pilot/generate',json={'goal':'Test'}).status_code==202
        for _ in range(100):
            snap=client.get(base+'/pilot').json()
            if not snap['busy']:break
            time.sleep(.02)
    assert snap['state']['plan']==plan
    assert json.loads((folder/'.toolforge/active-plan.json').read_text(encoding='utf-8'))==plan
    with patch('backend.pilot_service.chat_plan',side_effect=ValueError('Model JSON invalid')):
        client.post(base+'/pilot/generate',json={'goal':'Test'})
        for _ in range(100):
            snap=client.get(base+'/pilot').json()
            if not snap['busy']:break
            time.sleep(.02)
    assert 'Model JSON invalid' in snap['error']
    assert snap['state']['plan']==plan

def test_workspace_http_roundtrip(client,tmp_path):
    folder=tmp_path/'workspace';folder.mkdir()
    ident=client.post('/api/projects',json={'name':'Workbench'}).json()['id']
    assert client.post(f'/api/projects/{ident}/folder',json={'path':str(folder)}).status_code==200
    base=f'/api/projects/{ident}/workspace'
    saved=client.put(base+'/file',json={'path':'main.py','text':'print("API RUN")\n','revision':None})
    assert saved.status_code==200
    assert client.get(base+'/file',params={'path':'main.py'}).json()['text']=='print("API RUN")\n'
    assert client.put(base+'/file',json={'path':'main.py','text':'bad','revision':None}).status_code==422
    assert client.get(base+'/download',params={'path':'../secret'}).status_code==422
    assert client.post(base+'/job',json={'kind':'acceptance'}).status_code==202
    end=time.monotonic()+10
    while time.monotonic()<end:
        job=client.get(base+'/job').json()
        if not job['busy']:break
        time.sleep(.02)
    assert job['status']=='done',job
    artifact=job['result']['nodes'][-1]['artifact']
    download=client.get(base+'/download',params={'path':artifact})
    assert download.status_code==200 and download.content[:2]==b'PK'
    workflow=client.get(base+'/workflow').json()
    assert client.put(base+'/workflow',json=workflow).status_code==200
