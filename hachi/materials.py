"""Shared development/evaluation registry, frozen before any campaign call."""
from pathlib import Path
import json
from .design import digest, demo_actions
from .integrity import file_sha256


def freeze_materials(development, evaluation):
    if not development or not evaluation:
        raise ValueError('Both development and evaluation sets are required to establish isolation')
    for split, targets in (('development',development),('evaluation',evaluation)):
        if any(t.get('split') != split or not t.get('id') or not t.get('template_id') for t in targets):
            raise ValueError('Every material needs an ID, template ID and correct declared split')
    targets = development + evaluation
    if len({t['id'] for t in targets}) != len(targets):
        raise ValueError('Target IDs must be unique across both sets')
    if {t['template_id'] for t in development} & {t['template_id'] for t in evaluation}:
        raise ValueError('Development/evaluation templates overlap across the shared registry')
    records=[]
    for t in targets:
        demo_path, image_path = Path(t['demo']), Path(t['image'])
        demo = json.loads(demo_path.read_text())
        demo_actions(demo,'Original',0)
        if demo.get('target_id') != t['id']:
            raise ValueError('Recorded demonstration target does not match registry target')
        records.append({'target':t,'target_sha256':digest(t),'demo':demo,
                        'demo_file_sha256':file_sha256(demo_path),'image_sha256':file_sha256(image_path)})
    if len({r['demo']['demonstrator_id'] for r in records}) != 1:
        raise ValueError('One demonstrator is required across the shared material sets')
    manifest={'schema_version':1,'scope':'development-and-evaluation',
              'development_ids':[t['id'] for t in development],
              'evaluation_ids':[t['id'] for t in evaluation], 'records':records}
    return {'manifest':manifest,'sha256':digest(manifest)}


def verify_materials(registry, selected_targets):
    manifest=registry.get('manifest',{})
    if registry.get('sha256') != digest(manifest) or manifest.get('scope') != 'development-and-evaluation':
        raise ValueError('Shared materials manifest/hash missing or invalid')
    targets=[r['target'] for r in manifest.get('records',[])]
    current=freeze_materials([t for t in targets if t.get('split')=='development'],
                             [t for t in targets if t.get('split')=='evaluation'])
    if current != registry:
        raise ValueError('Frozen materials differ from current files or registry metadata')
    by_id={t['id']:t for t in targets}
    if len({t['id'] for t in selected_targets}) != len(selected_targets):
        raise ValueError('Duplicate supplied targets')
    if any(by_id.get(t['id']) != t for t in selected_targets):
        raise ValueError('Supplied targets differ from the shared frozen registry')
    return {r['target']['id']:r['demo'] for r in manifest['records']}


def require_matching_pilot(registry, campaign):
    if campaign.get('plan',{}).get('stage') != 'pilot':
        raise ValueError('Formal stage requires a recorded development pilot campaign')
    if campaign.get('materials_registry') != registry:
        raise ValueError('Pilot and formal campaigns must use the identical frozen material registry')
