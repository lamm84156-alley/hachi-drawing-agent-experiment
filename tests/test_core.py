import copy
import math
import pytest
from hachi.core import Canvas, validate
from hachi.design import permutation, schedule
from hachi.analysis import bootstrap, agreement, normalized_errors, redraw_failure

A = {'op':'draw','points':[[0.1,0.1],[0.2,0.2],[0.3,0.2],[0.4,0.1]]}

def test_budget_and_undo():
    c = Canvas()
    c.apply(A); c.apply({'op':'undo'})
    assert c.paths == []
    for _ in range(38):
        assert not c.apply({'op':'bad'})['valid']
    assert c.commands == 40 and c.invalid == 38
    with pytest.raises(RuntimeError): c.apply(A)

@pytest.mark.parametrize('bad',[None, {}, {'op':'undo','extra':0}, {'op':'draw','points':[[0,0]]}, {'op':'draw','points':[[float('nan'),0]]*4}, {'op':'draw','points':[[True,0]]*4}, {'op':'draw','points':[[2,0]]*4}])
def test_invalid_preserves_canvas(bad):
    c = Canvas(); c.apply(A)
    old = copy.deepcopy(c.paths)
    assert not c.apply(bad)['valid']
    assert c.paths == old and c.commands == 2

def test_segments_stop_empty_undo():
    for n in (4,7,10,13): validate({'op':'draw','points':[[0.1,0.1]]*n})
    c = Canvas(); assert not c.apply({'op':'undo'})['valid']
    c.apply({'op':'stop'})
    with pytest.raises(RuntimeError): c.apply(A)

def test_schedule_and_permutation():
    assert permutation(5,9) == permutation(5,9) != list(range(5))
    targets = [{'id':str(i),'split':'evaluation'} for i in range(6)]
    plan = schedule(targets,3,42,'exploratory')
    assert len(plan['runs']) == 54 and len({r['run_id'] for r in plan['runs']}) == 54
    with pytest.raises(ValueError): schedule(targets,3,42,'pilot')
    with pytest.raises(ValueError): schedule(targets,5,42,'exploratory')

def test_statistics_known_extremes():
    rows = [{'target_id':str(t),'condition':c,'completion':int(c=='Original')} for t in range(3) for c in ('Original','Reordered','No Demo') for _ in range(2)]
    r = bootstrap(rows,42)
    assert r['effect_percentage_points'] == 100 and r['ci95_percentile'] == [100,100]
    assert agreement([0,1],[0,1]) == {'raw_agreement':1,'cohen_kappa':1}
    assert agreement([1,1],[1,1])['cohen_kappa'] is None
    with pytest.raises(ValueError): bootstrap(rows[:-1],42)

def test_secondary():
    assert normalized_errors([0,0,10,10],[10,0,10,10],100,100)['center_x_error'] == .1
    assert redraw_failure(.2,.2,.3)
    assert redraw_failure(.4,.3,.2)
    assert not redraw_failure(.2,.1,.15)

def test_endpoint_modes(monkeypatch):
    from hachi.runner import API
    monkeypatch.delenv('HACHI_API_KEY',raising=False)
    client=API('http://127.0.0.1:8080/v1/chat/completions')
    assert client.local and client.key is None
    with pytest.raises(ValueError): API('http://remote.example/v1/chat/completions')
    with pytest.raises(ValueError): API('https://user:secret@example.com')
    with pytest.raises(KeyError): API('https://api.example.com/v1/chat/completions')

def test_self_hosted_remote_requires_https_and_auth(monkeypatch):
    from hachi.runner import API
    monkeypatch.setenv('HACHI_API_KEY','test-only-not-a-key')
    client=API('https://authorized.example/v1/chat/completions','self_hosted',900)
    assert client.local and client.timeout_seconds==900
    with pytest.raises(ValueError): API('http://authorized.example/v1/chat/completions','self_hosted')
