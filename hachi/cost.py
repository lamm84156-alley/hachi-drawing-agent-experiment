import json
from pathlib import Path


def estimate(root, input_per_million, output_per_million, calls=2160):
    """Supply current verified provider prices; no guessed tariffs or token counts."""
    usages = []
    for f in Path(root).glob('*/*.response.json'):
        manifest = json.loads((f.parent/'manifest.json').read_text())
        if manifest['run']['stage'] != 'pilot':
            continue
        summary = f.parent/'summary.json'
        if not summary.exists() or json.loads(summary.read_text())['data_kind'] != 'real_model':
            continue
        from .runner import verify_run_provenance
        verify_run_provenance(f.parent, 'real_model')
        response = json.loads(f.read_text())
        if response['http_status'] != 200:
            continue
        body = json.loads(response['body'])
        u = body.get('usage')
        if not u or not all(k in u for k in ('prompt_tokens','completion_tokens')):
            raise ValueError('Provider usage missing; do not invent costs')
        usages.append(u)
    if not usages:
        raise ValueError('No real pilot usage available for an empirical estimate')
    spent = sum(u['prompt_tokens']*input_per_million + u['completion_tokens']*output_per_million for u in usages)/1e6
    return {'observed_calls':len(usages), 'estimated_observed_cost':spent,
            '54_run_max_command_calls':calls, 'projection_at_pilot_mean_tokens_per_call':spent/len(usages)*calls,
            'note':'Projection, not a billing cap; ignores cache discounts. Verify image/reasoning billing and provider invoice. Context grows across commands; pilot must cover all conditions.'}
