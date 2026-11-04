"""Synthetic transport and geometry: never research evidence."""
import json
import numpy as np
import pytest
from PIL import Image
from hachi.render import render
from hachi.runner import execute, replay_demo, load
from hachi.analysis import analyze
from hachi.blind import prepare
from test_core import A

@pytest.fixture
def setup(tmp_path):
    p = dict(renderer='diffvg',command_budget=40,guidance='full_context',model='test-only',temperature=0,image_size=64,pen_width=2,history_limit=10,max_output_tokens=200,prompt='Test only',context_limit_tokens=20000,rubric_version='test')
    target = {'id':'test','prompt':'Test only','image':str(render([A],tmp_path/'target',64,2))}
    b = {'op':'draw','points':[[.4,.8],[.5,.4],[.6,.4],[.7,.8]]}
    # Test fixture claims provenance solely to exercise validation; never exported as a human record.
    demo = {'provenance':'human_recorded','demonstrator_id':'TEST_FIXTURE_NOT_HUMAN','actions':[A,b]}
    run = dict(run_id='test',target_id='test',condition='Original',permutation_seed=42,execution_seed=3,stage='pilot')
    return p,target,demo,run

def test_diffvg_reordered_final(tmp_path,setup):
    p,t,d,r = setup
    contexts=[]
    for condition in ('Original','Reordered'):
        actions = d['actions'] if condition=='Original' else d['actions'][::-1]
        image = render(actions,tmp_path/condition,64,2)
        contexts.append(np.array(Image.open(image)))
        context,order = replay_demo(d,condition,42,tmp_path/condition,p)
        assert len(context)==6
        assert sorted(order)==[0,1]
    assert contexts[0].min() < 255
    assert np.array_equal(*contexts)

def test_resume_reuses_saved_responses(tmp_path,setup):
    p,t,d,r = setup
    actions=iter([A,{'op':'undo'},None,{'op':'stop'}])
    def fake(packet):
        assert 'Target' in str(packet) and 'Current canvas' in str(packet)
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':json.dumps(next(actions))}}],'usage':{'prompt_tokens':1,'completion_tokens':1}})}
    root=tmp_path/'runs'; directory=root/'test'
    first=execute(r,t,d,p,directory,fake)
    assert first['commands']==4 and first['invalid']==1 and first['data_kind']=='technical_test'
    def forbidden(packet): raise AssertionError('Resume issued an extra request')
    assert execute(r,t,d,p,directory,forbidden)==first
    with pytest.raises(ValueError): analyze(root,tmp_path/'missing.csv',tmp_path/'out',42)
    with pytest.raises(ValueError): prepare(root,tmp_path/'blind',42)
    changed={**p,'temperature':1}
    with pytest.raises(ValueError): execute(r,t,d,changed,directory,forbidden)

def test_uncertain_call_not_retried(tmp_path,setup):
    p,t,d,r=setup
    def fail(packet): raise TimeoutError('Synthetic test')
    with pytest.raises(TimeoutError): execute(r,t,d,p,tmp_path/'run',fail)
    with pytest.raises(RuntimeError,match='Uncertain'): execute(r,t,d,p,tmp_path/'run',fail)

def test_no_demo_has_no_demo_images(tmp_path,setup):
    p,t,d,r=setup
    assert replay_demo(d,'No Demo',1,tmp_path,p)==([],[])

def test_all_invalid_hits_40_and_no_demo_payload(tmp_path,setup):
    p,t,d,r=setup
    r={**r,'condition':'No Demo'}
    calls=[]
    def fake(packet):
        content=packet['messages'][0]['content']
        assert sum(item['type']=='image_url' for item in content)==2
        calls.append(packet)
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'invalid json'}}]})}
    summary=execute(r,t,d,p,tmp_path/'invalid',fake)
    assert len(calls)==40 and summary['commands']==40 and summary['invalid']==40
    assert summary['stop_reason']=='budget'

def test_full_context_and_wrong_model_halt(tmp_path,setup):
    p,t,d,r=setup
    def fake(packet):
        assert sum(item['type']=='image_url' for item in packet['messages'][0]['content'])==6
        return {'http_status':200,'body':json.dumps({'model':'unexpected-version','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    with pytest.raises(RuntimeError,match='model identifier'): execute(r,t,d,p,tmp_path/'mismatch',fake)
    assert (tmp_path/'mismatch'/'00.response.json').exists()
    assert not (tmp_path/'mismatch'/'summary.json').exists()

@pytest.mark.parametrize('token', ['NaN', 'Infinity', '-Infinity', '1e309'])
def test_nonfinite_action_consumes_budget_and_resumes(tmp_path, setup, token):
    p,t,d,r = setup
    r = {**r, 'condition': 'No Demo'}
    raw = '{"op":"draw","points":[[' + token + ',0.1],[0.2,0.2],[0.3,0.2],[0.4,0.1]]}'
    outputs = iter([raw, '{"op":"stop"}'])
    directory = tmp_path / 'nonfinite'
    def fake(packet):
        return {'http_status':200, 'body':json.dumps({'model':'test-only', 'choices':[{'message':{'content':next(outputs)}}]})}
    summary = execute(r,t,d,p,directory,fake)
    assert summary['commands'] == 2 and summary['invalid'] == 1
    assert summary['data_kind'] == 'technical_test'
    body = json.loads(load(directory/'00.response.json')['body'])
    assert body['choices'][0]['message']['content'] == raw
    assert load(directory/'00.event.json')['action'] is None
    assert np.array_equal(np.array(Image.open(directory/'00.png')), np.array(Image.open(directory/'01.png')))
    def forbidden(packet):
        raise AssertionError('Resume must not repeat a model call')
    assert execute(r,t,d,p,directory,forbidden) == summary

def test_technical_resume_cannot_be_reclassified_as_real(tmp_path,setup,monkeypatch):
    from hachi.runner import API
    p,t,d,r=setup
    directory=tmp_path/'runs'/'test'
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    summary=execute(r,t,d,p,directory,fake)
    snapshot={f.name:f.read_bytes() for f in directory.iterdir() if f.name!='.lock'}
    def forbidden(self,packet): raise AssertionError('No actual model call is authorized by this test')
    monkeypatch.setattr(API,'__call__',forbidden)
    api=API('http://127.0.0.1:1/v1/chat/completions')
    with pytest.raises(ValueError,match='provenance'): execute(r,t,d,p,directory,api)
    assert summary['data_kind']=='technical_test'
    assert snapshot=={f.name:f.read_bytes() for f in directory.iterdir() if f.name!='.lock'}
    with pytest.raises(ValueError): prepare(directory.parent,tmp_path/'blind',42)


def test_missing_response_source_blocks_resume_and_blind_export(tmp_path,setup):
    from hachi.runner import save
    p,t,d,r=setup
    directory=tmp_path/'runs'/'test'
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    execute(r,t,d,p,directory,fake)
    response=load(directory/'00.response.json')
    response.pop('provenance')
    save(directory/'00.response.json',response)
    with pytest.raises(ValueError,match='provenance'): execute(r,t,d,p,directory,fake)
    # A manually relabelled summary cannot bypass the independent source checks.
    summary=load(directory/'summary.json'); summary['data_kind']='real_model'
    save(directory/'summary.json',summary)
    with pytest.raises(ValueError,match='provenance'): prepare(directory.parent,tmp_path/'blind',42)

@pytest.mark.parametrize('record', ['request','response','pending','receipt','event'])
def test_changed_audit_record_stops_without_overwrite(tmp_path,setup,record):
    from hachi.runner import save
    p,t,d,r=setup
    directory=tmp_path/'run'
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    execute(r,t,d,p,directory,fake)
    path=directory/f'00.{record}.json'
    value=load(path)
    if record=='request': value['model']='tampered-model'
    elif record=='response': value['body']='tampered-response'
    elif record=='pending': value['request_sha256']='tampered-request-hash'
    elif record=='receipt': value['response_sha256']='tampered-response-hash'
    else: value['action']={'op':'undo'}
    save(path,value)
    snapshot={f.name:f.read_bytes() for f in directory.iterdir() if f.name!='.lock'}
    def forbidden(packet): raise AssertionError('Tampering must not trigger a new call')
    with pytest.raises(ValueError): execute(r,t,d,p,directory,forbidden)
    assert snapshot=={f.name:f.read_bytes() for f in directory.iterdir() if f.name!='.lock'}

@pytest.mark.parametrize('version_key',['code_sha256','renderer_binary_sha256'])
def test_version_drift_blocks_resume(tmp_path,setup,monkeypatch,version_key):
    import hachi.runner as runner
    p,t,d,r=setup
    directory=tmp_path/'run'
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    execute(r,t,d,p,directory,fake)
    versions=runner.runtime_versions()
    monkeypatch.setattr(runner,'runtime_versions',lambda:{**versions,version_key:'changed'})
    with pytest.raises(ValueError,match='runtime versions'): execute(r,t,d,p,directory,fake)

def test_saved_request_byte_change_is_not_normalized_away(tmp_path,setup):
    p,t,d,r=setup
    directory=tmp_path/'run'
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    execute(r,t,d,p,directory,fake)
    request=directory/'00.request.json'
    request.write_bytes(request.read_bytes()+b'\n')
    changed=request.read_bytes()
    with pytest.raises(ValueError,match='bytes differ'): execute(r,t,d,p,directory,fake)
    assert request.read_bytes()==changed

@pytest.mark.parametrize('token',['1'+'0'*400,'9'*5000],ids=['huge-integer','integer-parser-limit'])
def test_extreme_integer_action_is_invalid_not_fatal(tmp_path,setup,token):
    p,t,d,r=setup
    raw='{"op":"draw","points":[['+token+',0],[0,0],[0,0],[0,0]]}'
    outputs=iter([raw,'{"op":"stop"}'])
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':next(outputs)}}]})}
    directory=tmp_path/'extreme'
    summary=execute(r,t,d,p,directory,fake)
    assert summary['commands']==2 and summary['invalid']==1
    assert json.loads(load(directory/'00.response.json')['body'])['choices'][0]['message']['content']==raw
    assert load(directory/'00.event.json')['action'] is None
    def forbidden(packet): raise AssertionError('No model calls during resume')
    assert execute(r,t,d,p,directory,forbidden)==summary

@pytest.mark.parametrize('change',['event_action','condition','invalid','completion','target_id','stop_reason'])
def test_audit_replays_events_and_summary(tmp_path,setup,change):
    from hachi.runner import save, verify_run_provenance
    p,t,d,r=setup
    def fake(packet):
        return {'http_status':200,'body':json.dumps({'model':'test-only','choices':[{'message':{'content':'{"op":"stop"}'}}]})}
    directory=tmp_path/'audit'
    execute(r,t,d,p,directory,fake)
    verify_run_provenance(directory,'technical_test')
    path=directory/('00.event.json' if change=='event_action' else 'summary.json')
    value=load(path)
    if change=='event_action': value['action']={'op':'undo'}
    else: value[change]={'condition':'Reordered','invalid':1,'completion':1,'target_id':'OTHER','stop_reason':'budget'}[change]
    save(path,value)
    original=path.read_bytes()
    with pytest.raises(ValueError): verify_run_provenance(directory,'technical_test')
    assert path.read_bytes()==original
