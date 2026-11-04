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
