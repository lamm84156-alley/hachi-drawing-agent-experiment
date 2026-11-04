"""Human completion labels are required; no automatic completion surrogate."""
import csv
import json
from pathlib import Path
import numpy as np
from .core import CONDITIONS


def write_csv(path, rows, fields):
    with Path(path).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def agreement(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if len(a) == 0 or len(a) != len(b):
        raise ValueError('Paired ratings required')
    observed = float(np.mean(a == b))
    expected = float(np.mean(a) * np.mean(b) + (1-np.mean(a)) * (1-np.mean(b)))
    return {'raw_agreement': observed, 'cohen_kappa': None if expected == 1 else (observed-expected)/(1-expected)}


def bootstrap(rows, seed):
    targets = sorted({r['target_id'] for r in rows})
    if not targets:
        raise ValueError('No adjudicated data')
    rates, counts = [], []
    for target in targets:
        groups = [[r['completion'] for r in rows if r['target_id'] == target and r['condition'] == c] for c in CONDITIONS]
        if any(not g for g in groups) or len({len(g) for g in groups}) != 1:
            raise ValueError('Complete balanced within-target condition groups required')
        rates.append([np.mean(g) for g in groups])
        counts.append(len(groups[0]))
    if len(set(counts)) != 1:
        raise ValueError('Unequal repetitions across targets')
    rates = np.array(rates)
    rng = np.random.default_rng(seed)
    # Resample whole target clusters. All condition rates and repetitions stay paired.
    draws = rates[rng.integers(0, len(targets), size=(10000, len(targets)))].mean(axis=1)
    effects = 100 * (draws[:, 0] - draws[:, 1])
    return {'effect_percentage_points': float(100 * np.mean(rates[:, 0]-rates[:, 1])),
            'ci95_percentile': np.quantile(effects, [0.025, 0.975]).tolist(),
            'bootstrap_resamples': 10000, 'bootstrap_seed': seed, 'targets': len(targets),
            'repetitions': counts[0], 'condition_rates': dict(zip(CONDITIONS, rates.mean(axis=0).tolist()))}


def normalized_errors(target_bbox, observed_bbox, width, height):
    """Return separate center/size components; no invented aggregate layout metric."""
    tx, ty, tw, th = target_bbox
    x, y, w, h = observed_bbox
    return {'center_x_error': abs((x+w/2)-(tx+tw/2))/width,
            'center_y_error': abs((y+h/2)-(ty+th/2))/height,
            'width_error': abs(w-tw)/width, 'height_error': abs(h-th)/height}


def redraw_failure(before_layout_error, after_layout_error, frozen_threshold):
    return after_layout_error >= before_layout_error or after_layout_error > frozen_threshold


def analyze(root, ratings_path, output, seed):
    incomplete = [p.parent.name for p in Path(root).glob('*/manifest.json') if not (p.parent/'summary.json').exists()]
    if incomplete:
        raise ValueError('Incomplete runs must be reported/resolved, not excluded: ' + ', '.join(incomplete))
    summaries = [json.loads(p.read_text()) for p in Path(root).glob('*/summary.json')]
    if not summaries or any(r['data_kind'] != 'real_model' for r in summaries):
        raise ValueError('Analysis requires real-model logs; technical fixtures are prohibited')
    from .runner import verify_run_provenance
    for directory in Path(root).glob('*/summary.json'):
        verify_run_provenance(directory.parent, 'real_model')
    campaign_path = Path(root)/'campaign.json'
    if not campaign_path.exists():
        raise ValueError('Frozen campaign manifest required to detect missing/unstarted runs')
    campaign = json.loads(campaign_path.read_text())
    if {r['run_id'] for r in summaries} != {r['run_id'] for r in campaign['plan']['runs']}:
        raise ValueError('All planned runs must be present; incomplete campaigns cannot be silently reduced')
    with Path(ratings_path).open() as f:
        ratings = list(csv.DictReader(f))
    if len({r['run_id'] for r in ratings}) != len(ratings):
        raise ValueError('Duplicate rating rows')
    by_id = {r['run_id']: r for r in ratings}
    if set(by_id) != {r['run_id'] for r in summaries}:
        raise ValueError('Every run must have ratings; do not silently discard failures')
    a, b, rows = [], [], []
    for s in summaries:
        r = by_id[s['run_id']]
        if r.get('provenance') != 'human' or not r.get('rater1_id') or not r.get('rater2_id') or r['rater1_id'] == r['rater2_id']:
            raise ValueError('Two identified independent human raters required')
        if r['rater1'] not in ('0', '1') or r['rater2'] not in ('0', '1'):
            raise ValueError('Missing binary completion ratings')
        v1, v2 = int(r['rater1']), int(r['rater2'])
        a.append(v1); b.append(v2)
        if v1 == v2:
            value = v1
        elif r.get('discussion_completion') in ('0', '1') and r.get('discussion_record'):
            value = int(r['discussion_completion'])
        else:
            if r.get('adjudicated') not in ('0', '1') or not r.get('adjudicator_id') or r['adjudicator_id'] in (r['rater1_id'], r['rater2_id']):
                raise ValueError('Disagreements need a distinct third adjudicator')
            value = int(r['adjudicated'])
        rows.append({**s, 'completion': value})
    result = {**agreement(a, b), **bootstrap(rows, seed)}
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    (output / 'statistics.json').write_text(json.dumps(result, indent=2))
    write_csv(output / 'runs.csv', rows, list(rows[0]))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.bar(CONDITIONS, [100*result['condition_rates'][c] for c in CONDITIONS])
    ax.set(ylabel='Adjudicated completion (%)', ylim=(0, 100))
    for ext in ('svg', 'pdf'):
        fig.savefig(output / f'completion.{ext}', bbox_inches='tight')
    plt.close(fig)
    (output / 'report.md').write_text('# Experimental analysis\n\n' +
        f"{len(rows)} real model runs; {result['targets']} targets; {result['repetitions']} repetitions per condition.\n\n" +
        f"Original minus Reordered: {result['effect_percentage_points']:.2f} percentage points; " +
        f"95% paired whole-target percentile interval: {result['ci95_percentile']}.\n\n" +
        f"Independent raw agreement: {result['raw_agreement']}; Cohen’s kappa: {result['cohen_kappa']}.\n\n" +
        'Completion is human-adjudicated. Commands and invalid actions are in runs.csv. '
        'Part errors, omissions and redraw judgments require the separate human annotation table and frozen rubric. '
        'A 54-run exploratory study differs from the original 20 × 5 × 3 = 300 design; '
        'the 40-command limit and estimand definition remain fixed, with the target average taken over the actual exploratory targets. '
        'No population-wide or powered confirmatory claim is supported.\n')
    return result


def export_secondary(parts_path, redraws_path, output, width, height, layout_threshold):
    """Export auditable per-part/transition metrics after a rubric is frozen.

    No automatic part recognition or completion decision is performed. Bounding
    boxes and same-part associations must come from actual human annotations.
    """
    if width <= 0 or height <= 0 or layout_threshold < 0:
        raise ValueError('Positive canvas dimensions and frozen layout threshold required')
    with Path(parts_path).open() as f:
        parts = list(csv.DictReader(f))
    with Path(redraws_path).open() as f:
        redraws = list(csv.DictReader(f))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    part_rows = []
    for r in parts:
        if r.get('provenance') != 'human' or not r.get('rater_id') or r.get('omitted') not in ('0','1'):
            raise ValueError('Human part annotations required')
        errors = dict.fromkeys(('center_x_error','center_y_error','width_error','height_error'), '')
        if r['omitted'] == '0':
            target = [float(r['target_'+k]) for k in ('x','y','width','height')]
            observed = [float(r['bbox_'+k]) for k in ('x','y','width','height')]
            if not np.isfinite(target+observed).all() or min(target[2:]+observed[2:]) < 0:
                raise ValueError('Invalid annotated bounding box')
            errors = normalized_errors(target, observed, width, height)
        part_rows.append({**r, **errors})
    redraw_rows = []
    for r in redraws:
        if r.get('provenance') != 'human' or not r.get('rater_id'):
            raise ValueError('Human same-part redraw associations required')
        before, after = float(r['layout_error_before']), float(r['layout_error_after'])
        if not np.isfinite([before,after]).all() or min(before,after) < 0:
            raise ValueError('Finite nonnegative layout errors required')
        redraw_rows.append({**r,'fails_layout':int(redraw_failure(before,after,layout_threshold))})
    if part_rows: write_csv(output/'part_errors.csv',part_rows,list(part_rows[0]))
    if redraw_rows: write_csv(output/'redraw_errors.csv',redraw_rows,list(redraw_rows[0]))
    return {'parts':len(part_rows),'redraws':len(redraw_rows)}
