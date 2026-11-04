import hashlib
import random
from pathlib import Path
from .core import CONDITIONS, canonical, validate


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def permutation(n, seed):
    if n < 2:
        raise ValueError('Non-original permutation requires at least two paths')
    rng = random.Random(seed)
    original = list(range(n))
    order = original.copy()
    while order == original:
        rng.shuffle(order)
    return order


def demo_actions(demo, condition, seed):
    actions = demo['actions']
    if demo.get('provenance') != 'human_recorded' or not demo.get('demonstrator_id'):
        raise ValueError('Research demonstrations require recorded human provenance')
    for a in actions:
        validate(a)
        if a['op'] != 'draw':
            raise ValueError('Demonstrations must contain additive draw paths only')
    if len(actions) < 2:
        raise ValueError('At least two demonstration paths required')
    if condition == 'No Demo':
        return [], []
    order = list(range(len(actions))) if condition == 'Original' else permutation(len(actions), seed)
    return [actions[i] for i in order], order


def schedule(targets, repeats, seed, stage):
    if stage not in ('pilot', 'exploratory', 'proposal'):
        raise ValueError('Unknown stage')
    if len({t['id'] for t in targets}) != len(targets) or repeats < 1:
        raise ValueError('Unique targets and positive repetitions required')
    if stage == 'pilot' and any(t['split'] != 'development' for t in targets):
        raise ValueError('Pilot must use development targets only')
    if stage != 'pilot' and any(t['split'] != 'evaluation' for t in targets):
        raise ValueError('Formal runs must use evaluation targets')
    if stage == 'exploratory' and len(targets) * repeats * 3 != 54:
        raise ValueError('Exploratory allocation must total 54; allocation needs user decision')
    if stage == 'proposal' and (len(targets), repeats) != (20, 5):
        raise ValueError('Original design is 20 targets × 5 repetitions × 3 conditions')
    rng = random.Random(seed)
    runs = []
    for target in targets:
        for repeat in range(repeats):
            perm_seed = rng.randrange(2**31)
            execution_seed = rng.randrange(2**31)
            for condition in CONDITIONS:
                row = dict(target_id=target['id'], repeat=repeat, condition=condition,
                           permutation_seed=perm_seed, execution_seed=execution_seed, stage=stage)
                row['run_id'] = digest(row)[:16]
                runs.append(row)
    rng.shuffle(runs)
    return {'schedule_seed': seed, 'stage': stage, 'runs': runs}


def validate_protocol(p):
    required = ('model', 'temperature', 'image_size', 'pen_width', 'history_limit',
                'max_output_tokens', 'prompt', 'context_limit_tokens', 'rubric_version')
    if any(p.get(k) is None for k in required):
        raise ValueError('Freeze all protocol fields before model calls')
    if p.get('renderer') != 'diffvg' or p.get('command_budget') != 40:
        raise ValueError('DiffVG and 40-command budget are mandatory')
    if p['image_size'] <= 0 or p['pen_width'] <= 0 or p['history_limit'] < 0:
        raise ValueError('Invalid drawing/history parameters')
    if p.get('guidance') != 'full_context':
        raise ValueError('Segment guidance requires an explicitly amended protocol')
