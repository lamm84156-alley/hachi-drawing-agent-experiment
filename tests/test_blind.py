"""Synthetic on-disk export fixtures, never model observations or rater scores."""
import json
from pathlib import Path
import pytest
from hachi.blind import prepare
from hachi.runner import save
from hachi.design import digest
from hachi.integrity import runtime_versions, file_sha256
from test_core import A


def test_invalid_free_text_never_enters_blind_packet(tmp_path):
    # Exercise the real-model-format export branch with a deliberately synthetic
    # file-format fixture. No API call or scientific result is represented here.
    source = tmp_path/'TEST_FIXTURE_runs'/'TEST_FIXTURE_run'
    source.mkdir(parents=True)
    marker = 'SECRET_CONDITION_Reordered_TEST_FIXTURE'
    provenance = {'data_kind':'real_model','adapter':'hachi.runner.API','execution_kind':'remote_api','endpoint':'https://TEST_FIXTURE.invalid/v1/chat/completions'}
    save(source/'summary.json', {'run_id':'TEST_FIXTURE_run','data_kind':'real_model','commands':6})
    runtime = runtime_versions()
    save(source/'manifest.json', {'schema_version':2,'runtime':runtime,'target':{'prompt':'Draw the specified face.'},'execution_source':provenance})
    for name in ('final.png','final.svg','target.png','00.png'):
        (source/name).write_bytes(b'TEST_FIXTURE_NOT_AN_IMAGE')
    events = [
        {'command':1,'action':marker,'outcome':{'valid':False,'error':marker}},
        {'command':2,'action':{'op':'draw','points':A['points'],'explanation':marker},'outcome':{'valid':False}},
        {'command':3,'action':{'op':marker,'nested':{'condition':marker}},'outcome':{'valid':False}},
        {'command':4,'action':A,'outcome':{'valid':True}},
        {'command':5,'action':{'op':'undo'},'outcome':{'valid':True}},
        {'command':6,'action':{'op':'stop'},'outcome':{'valid':True}},
    ]
    for i,e in enumerate(events):
        save(source/f'{i:02d}.event.json',e)
        request={'synthetic_fixture_command':i}
        response={'provenance':provenance,'body':'TEST_FIXTURE_NO_MODEL_CALL','request_sha256':digest(request),'runtime_sha256':digest(runtime)}
        save(source/f'{i:02d}.request.json',request)
        save(source/f'{i:02d}.response.json',response)
        save(source/f'{i:02d}.pending.json',{'request_sha256':digest(request)})
        save(source/f'{i:02d}.receipt.json',{'request_sha256':digest(request),'response_sha256':digest(response)})
    summary=json.loads((source/'summary.json').read_text())
    summary['artifacts_sha256']={p.name:file_sha256(p) for p in source.iterdir() if p.suffix in ('.png','.svg')}
    save(source/'summary.json',summary)
    raw_snapshot = {p.name:p.read_bytes() for p in source.iterdir()}
    out = tmp_path/'TEST_FIXTURE_blind'
    prepare(source.parent, out, 42)
    for p in (out/'raters').rglob('*'):
        if p.is_file(): assert marker.encode() not in p.read_bytes()
    actions = json.loads((out/'raters'/'item-0001'/'actions.json').read_text())
    assert [a['action'] for a in actions[:3]] == [None,None,None]
    assert [a['valid'] for a in actions] == [False,False,False,True,True,True]
    assert actions[3]['action'] == A
    assert actions[4]['action'] == {'op':'undo'}
    assert actions[5]['action'] == {'op':'stop'}
    assert raw_snapshot == {p.name:p.read_bytes() for p in source.iterdir()}


@pytest.mark.parametrize('event', [
    {'command':1,'action':{'op':'stop','note':'SECRET'},'outcome':{'valid':True}},
    {'command':'SECRET','action':None,'outcome':{'valid':False}},
    {'command':1,'action':None,'outcome':{'valid':'SECRET'}},
])
def test_inconsistent_blind_record_fails_closed(event):
    from hachi.blind import blind_event
    with pytest.raises(ValueError): blind_event(event)
