import json
import re
import threading
from unittest.mock import Mock, patch
import pytest
from toolforge_pilot.preflight import Studio, evaluate, suggest, signature, MAX_CANDIDATES

class FakeStudio:
    def __init__(self, bad=False): self.events=[]; self.bad=bad
    def inventory(self): return [{'key':x,'type':'llm','max_context_length':32768} for x in ['a','b','c','judge']]
    def check(self): pass
    def switch(self,key,context): self.events.extend(['unload','load:'+key]);return key
    def unload(self): self.events.append('unload')
    def chat(self,model,prompt,temp,output=1024):
        self.events.append('chat:'+model)
        if model=='judge':
            assert '"model"' not in prompt
            ids=re.findall(r'"id":\s*"(S\d+)"',prompt)
            scores={sid:90-10*(int(sid[1:])-1) for sid in ids}
            winner='nonexistent' if self.bad else ('S1' if 'S1' in ids else (ids[0] if ids else 'S1'))
            result={'winner':winner,'reason':'Konkretere Lösung.','scores':scores}
        else: result={'solution':'konkrete Lösung','checks':'Prüfen','limitations':'Stichprobe'}
        return {'response':json.dumps(result),'seconds':1,'finish_reason':'stop','usage':{}}

def run(studio,**kw):
    reports=[]
    params=dict(studio=studio,goal='Erstelle ein Tool', candidates=['a','b'],judge='judge',context=20000,kind='coding',two_temperatures=True,emit=lambda _:None,save=lambda r:reports.append(json.loads(json.dumps(r))))
    params.update(kw)
    return evaluate(**params),reports

def test_sequence_and_audit():
    studio=FakeStudio();report,saved=run(studio)
    assert studio.events==['unload','load:a','chat:a','chat:a','unload','load:b','chat:b','chat:b','unload','load:judge','chat:judge','unload']
    assert report['recommendation']['model']=='a'
    assert report['status']=='ready' and len(saved)>=6
    assert report['recommendation']['temperature']==.2

def test_invalid_winner_never_recommended():
    studio=FakeStudio(True)
    with pytest.raises(ValueError,match='Sieger'): run(studio)
    assert studio.events[-1]=='unload'

@pytest.mark.parametrize('candidates',[[],['a','a'],['a','b','judge','four'],['missing']])
def test_invalid_candidates_no_load(candidates):
    studio=FakeStudio()
    with pytest.raises(ValueError): run(studio,candidates=candidates)
    assert not studio.events

def test_context_limit_no_load():
    studio=FakeStudio()
    with pytest.raises(ValueError,match='Modelllimit'): run(studio,context=40000)
    assert not studio.events

def test_failed_unload_prevents_load():
    studio=Studio('http://localhost:1234/v1','test')
    studio.instances=Mock(return_value=[{'id':'old'}]);studio.request=Mock()
    with patch('toolforge_pilot.preflight.time.sleep'):
        with pytest.raises(ValueError,match='Entladen'): studio.switch('new',20000)
    assert all(call.args[0]!='/api/v1/models/load' for call in studio.request.call_args_list)

def test_wrong_loaded_context_rejected():
    studio=Studio('http://localhost:1234/v1','test');studio.unload=Mock()
    studio.request=Mock(return_value={'instance_id':'new'})
    studio.instances=Mock(return_value=[{'id':'new','config':{'context_length':4096}}])
    with pytest.raises(ValueError,match='Kontext abweichend'):studio.switch('new',20000)

def test_small_loaded_context_is_adopted():
    studio=Studio('http://localhost:1234/v1','test');studio.unload=Mock()
    studio.request=Mock(return_value={'instance_id':'new'})
    studio.instances=Mock(return_value=[{'id':'new','config':{'context_length':20224}}])
    assert studio.switch('new',20000)=='new'
    assert studio.actual_context==20224

def test_more_than_three_candidates_are_measured():
    studio=FakeStudio();report,_=run(studio,candidates=['a','b','c'])
    assert len(report['samples'])==6
    assert report['verdict']['scores']['S6']>=0
    assert report['recommendation']['model']=='a'
    assert MAX_CANDIDATES>=6

def test_more_than_six_candidates_rejected():
    studio=FakeStudio()
    with pytest.raises(ValueError,match='Kandidaten'):run(studio,candidates=['a','b','c','d','e','f','g'])

def test_cancel_before_load():
    event=threading.Event();event.set()
    studio=Studio('http://localhost:1234/v1','test',cancel=event);studio.request=Mock()
    with pytest.raises(ValueError,match='gestoppt'):studio.switch('new',20000)
    studio.request.assert_not_called()

def test_suggestions_use_real_keys():
    rows=[{'key':'local/qwen2.5-coder-14b','type':'llm','max_context_length':32000}, {'key':'qwen/qwen3.5-9b','type':'llm','max_context_length':128000}]
    result=suggest(rows,'coding')
    assert result['candidates']==[r['key'] for r in rows]
    assert result['judge']=='qwen/qwen3.5-9b'
    assert suggest(rows,'context')['candidates'][0]=='qwen/qwen3.5-9b'

def test_cleanup_failure_invalidates_result():
    studio=FakeStudio();studio.unload=Mock(side_effect=ValueError('unload failed'))
    saved=[]
    with pytest.raises(ValueError,match='unload failed'): run(studio,save=lambda r:saved.append(json.loads(json.dumps(r))))
    assert saved[-1]['status']=='error'

def test_bad_samples_never_recommended():
    studio=FakeStudio();studio.chat=Mock(return_value={'response':'no JSON','finish_reason':'stop','seconds':1})
    with pytest.raises(ValueError,match='Keine vollständige'):run(studio)
    assert 'load:judge' not in studio.events

def test_session_rejects_stale_settings(tmp_path):
    from backend.pilot_service import Session
    session=Session(tmp_path)
    session.preflight={'status':'ready','accepted':True,'goal_signature':signature('goal'),'base':session.settings['base'], 'accepted_settings':{'model':'tested','context_tokens':20000}}
    with pytest.raises(ValueError,match='Aufgabe geändert'):session.check_preflight('other')
    with pytest.raises(ValueError,match='Einstellungen'):session.check_preflight('goal')
    session.close()

def test_session_full_flow_and_changed_model(tmp_path):
    import time
    from backend.pilot_service import Session
    from toolforge_pilot.core import APP_ROOT
    session=Session(tmp_path)
    studio=FakeStudio()
    studio.instances=lambda:[{'id':'a','config':{'context_length':20000}}]
    session.studio=lambda **_:studio
    def wait():
        session.worker.join(timeout=5)
        assert not session.busy
        assert not session.error,session.error
    session.run_preflight({'goal':'Erstelle ein Tool','candidates':['a','b'],'judge':'judge','context_tokens':20000})
    wait()
    assert not session.preflight.get('accepted')
    assert session.preflight_path.exists()
    session.accept_preflight('Erstelle ein Tool');wait()
    assert session.settings['model']=='a'
    plan=json.loads((APP_ROOT/'examples/demo_plan.json').read_text())
    with patch('backend.pilot_service.chat_plan',return_value=plan):
        session.generate('Erstelle ein Tool');wait()
    assert session.store.state['plan']==plan
    studio.instances=lambda:[{'id':'wrong','config':{'context_length':20000}}]
    with pytest.raises(ValueError,match='Geladenes Modell'):session.check_preflight()
    session.close()


def test_session_can_rerun_preflight_from_stored_candidates(tmp_path):
    from backend.pilot_service import Session
    session=Session(tmp_path)
    studio=FakeStudio()
    session.studio=lambda **_:studio
    def wait():
        session.worker.join(timeout=5)
        assert not session.busy
        assert not session.error,session.error
    payload={'goal':'Erstelle ein Tool','candidates':['a','b'],'judge':'judge','context_tokens':20000}
    session.run_preflight(payload);wait()
    report=session.preflight
    assert report['status']=='ready'
    assert report['candidates']==['a','b'] and report['judge']=='judge'
    history=session.store.log_root.parent/'preflight-history'
    first=sorted(history.glob('*.json'))
    assert len(first)==1
    session.run_preflight({'goal':payload['goal'],'candidates':report['candidates'],'judge':report['judge'],
                           'context_tokens':report['context_tokens'],'kind':report['kind']})
    wait()
    assert len(list(history.glob('*.json')))==2
    assert session.preflight['status']=='ready'
    session.close()
