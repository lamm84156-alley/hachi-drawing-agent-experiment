"""Packet construction checks only; do not claim real VLM acceptance."""
import importlib.util
import json
from pathlib import Path
from PIL import Image


def test_probe_packets_preserve_two_image_identity_and_order(tmp_path):
    script=Path(__file__).parents[1]/'scripts'/'prepare_vision_check.py'
    spec=importlib.util.spec_from_file_location('vision_check',script)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    output=tmp_path/'probe'
    module.prepare(output,'TEST_FIXTURE_NO_MODEL',64)
    ab=json.loads((output/'AB-adjacent.request.json').read_text())['messages'][0]['content']
    ba=json.loads((output/'BA-adjacent.request.json').read_text())['messages'][0]['content']
    assert [v['type'] for v in ab]==['text','image_url','image_url']
    assert ab[1]==ba[2] and ab[2]==ba[1] and ab[1]!=ab[2]
    newline=json.loads((output/'AB-newline-diagnostic.request.json').read_text())['messages'][0]['content']
    assert newline[2]=={'type':'text','text':'\n'}
    assert Image.open(output/'A.png').size==Image.open(output/'B.png').size==(64,64)
    plan=json.loads((output/'diagnostic-plan.json').read_text())
    assert plan['real_model_run_status']=='not_run' and not plan['production_separator_changed']
