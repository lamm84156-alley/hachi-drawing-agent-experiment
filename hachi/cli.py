import argparse
import json
from pathlib import Path
from .design import schedule, validate_protocol, digest
from .runner import API, execute, load, save, save_once, verify_run_provenance
from .materials import freeze_materials, verify_materials, require_matching_pilot
from .integrity import runtime_versions
from .analysis import analyze
from .blind import prepare


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('freeze-materials')
    freeze.add_argument('development'); freeze.add_argument('evaluation'); freeze.add_argument('output')
    plan = sub.add_parser('plan')
    plan.add_argument('targets'); plan.add_argument('output')
    plan.add_argument('--repeats', type=int, required=True)
    plan.add_argument('--seed', type=int, required=True)
    plan.add_argument('--stage', choices=['pilot', 'exploratory', 'proposal'], required=True)
    run = sub.add_parser('run')
    for arg in ('plan', 'targets', 'protocol', 'authorization', 'output'):
        run.add_argument(arg)
    run.add_argument('--endpoint', required=True)
    run.add_argument('--materials-manifest', required=True)
    run.add_argument('--pilot-campaign')
    run.add_argument('--backend', choices=['auto', 'self_hosted'], default='auto')
    stats = sub.add_parser('analyze')
    for arg in ('runs', 'ratings', 'output'):
        stats.add_argument(arg)
    stats.add_argument('--seed', type=int, required=True)
    blind = sub.add_parser('blind')
    blind.add_argument('runs'); blind.add_argument('output'); blind.add_argument('--seed', type=int, required=True)
    args = p.parse_args()
    if args.command == 'freeze-materials':
        save_once(args.output, freeze_materials(load(args.development), load(args.evaluation)))
    elif args.command == 'plan':
        save(args.output, schedule(load(args.targets), args.repeats, args.seed, args.stage))
    elif args.command == 'analyze':
        print(json.dumps(analyze(args.runs, args.ratings, args.output, args.seed), indent=2))
    elif args.command == 'blind':
        prepare(args.runs, args.output, args.seed)
    elif args.command == 'run':
        plan, protocol, auth = load(args.plan), load(args.protocol), load(args.authorization)
        validate_protocol(protocol)
        if auth.get('approved_by_user') is not True or auth.get('stage') != plan['stage'] or auth.get('plan_sha256') != digest(plan) or auth.get('protocol_sha256') != digest(protocol):
            raise ValueError('Explicit user approval matching frozen plan and protocol required')
        transport = API(args.endpoint, args.backend, protocol.get('request_timeout_seconds', 120))
        approval_key = 'local_model_execution_approved' if transport.local else 'api_spending_approved'
        if not auth.get(approval_key) or not auth.get('approval_reference'):
            raise ValueError('Record model-execution approval and its conversation reference')
        if transport.local and not all(protocol.get(k) for k in ('weights_sha256', 'projector_sha256', 'inference_engine_version', 'quantization')):
            raise ValueError('Freeze local weights, projector, engine and quantization before runs')
        supplied_targets = load(args.targets)
        registry = load(args.materials_manifest)
        all_demos = verify_materials(registry, supplied_targets)
        if auth.get('materials_sha256') != registry['sha256']:
            raise ValueError('Approval must reference the shared frozen materials hash')
        if plan['stage'] != 'pilot':
            if not args.pilot_campaign:
                raise ValueError('Formal runs require the completed pilot campaign path')
            pilot_path = Path(args.pilot_campaign)
            pilot = load(pilot_path)
            require_matching_pilot(registry, pilot)
            for row in pilot['plan']['runs']:
                verify_run_provenance(pilot_path.parent/row['run_id'], 'real_model')
        targets = {t['id']: t for t in supplied_targets}
        selected_ids = {r['target_id'] for r in plan['runs']}
        if not selected_ids or not selected_ids <= set(targets):
            raise ValueError('Plan must contain known targets')
        selected = [t for t in targets.values() if t['id'] in selected_ids]
        expected = schedule(selected, len(plan['runs']) // (3*len(selected)), plan['schedule_seed'], plan['stage'])
        if {digest(r) for r in expected['runs']} != {digest(r) for r in plan['runs']} or len(expected['runs']) != len(plan['runs']):
            raise ValueError('Plan fails design validation')
        demos = {t['id']: all_demos[t['id']] for t in selected}
        if len({d.get('demonstrator_id') for d in demos.values()}) != 1:
            raise ValueError('The proposal requires a single demonstrator')
        for t in selected:
            d = demos[t['id']]
            if d.get('target_id') != t['id'] or d.get('image_size') != protocol['image_size'] or d.get('pen_width') != protocol['pen_width']:
                raise ValueError('Demonstration target/resolution/pen must match frozen protocol')
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        campaign = {'plan': plan, 'protocol': protocol, 'endpoint': args.endpoint, 'backend': args.backend,
                    'materials_registry': registry, 'runtime': runtime_versions()}
        campaign_path = output / 'campaign.json'
        if campaign_path.exists() and load(campaign_path) != campaign:
            raise ValueError('Output directory belongs to a different frozen campaign')
        save_once(campaign_path, campaign)
        for row in plan['runs']:
            # Recheck the entire frozen registry before each next run, including
            # targets not yet started. Never silently accept mid-campaign edits.
            verify_materials(registry, supplied_targets)
            target = targets[row['target_id']]
            record = next(r for r in registry['manifest']['records'] if r['target']['id'] == row['target_id'])
            execute(row, target, demos[row['target_id']], protocol, Path(args.output) / row['run_id'], transport,
                    frozen_material=record)


if __name__ == '__main__':
    main()
