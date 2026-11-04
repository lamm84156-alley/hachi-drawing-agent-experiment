"""Synthetic registry fixtures only; no human demonstrations are collected here."""
import copy
import json
import pytest
from hachi.materials import freeze_materials, verify_materials, require_matching_pilot
from test_core import A

@pytest.fixture
def materials(tmp_path):
    targets=[]
    for split in ('development','evaluation'):
        image=tmp_path/f'{split}.png'; image.write_bytes(b'TEST_FIXTURE_IMAGE')
        demo=tmp_path/f'{split}.json'
        demo.write_text(json.dumps({'provenance':'human_recorded','demonstrator_id':'TEST_FIXTURE_NOT_HUMAN',
            'target_id':split,'actions':[A,A]}))
        targets.append({'id':split,'split':split,'template_id':split+'-template','image':str(image),'demo':str(demo),'prompt':'Fixture'})
    return targets

def test_shared_registry_checks_separate_sets(materials):
    dev,evaluation=materials
    registry=freeze_materials([dev],[evaluation])
    assert set(verify_materials(registry,[dev]))=={'development','evaluation'}
    assert set(verify_materials(registry,[evaluation]))=={'development','evaluation'}
    with pytest.raises(ValueError,match='overlap'):
        freeze_materials([dev],[{**evaluation,'template_id':dev['template_id']}])
    with pytest.raises(ValueError,match='Both'): freeze_materials([dev],[])

@pytest.mark.parametrize('asset',['image','demo'])
def test_unstarted_material_drift_is_detected(materials,asset):
    from pathlib import Path
    dev,evaluation=materials
    registry=freeze_materials([dev],[evaluation])
    path=Path(evaluation[asset])
    path.write_bytes(path.read_bytes()+b' ')
    # Even a pilot selecting only development must detect changed eval assets.
    with pytest.raises(ValueError,match='Frozen materials'): verify_materials(registry,[dev])

def test_registry_and_cross_campaign_mismatches(materials):
    dev,evaluation=materials
    registry=freeze_materials([dev],[evaluation])
    bad=copy.deepcopy(registry); bad['manifest']['records'][0]['target']['prompt']='changed'
    with pytest.raises(ValueError,match='hash'): verify_materials(bad,[dev])
    with pytest.raises(ValueError,match='Supplied'): verify_materials(registry,[{**dev,'prompt':'changed'}])
    pilot={'plan':{'stage':'pilot'},'materials_registry':registry}
    require_matching_pilot(registry,pilot)
    with pytest.raises(ValueError,match='identical'): require_matching_pilot(bad,pilot)
