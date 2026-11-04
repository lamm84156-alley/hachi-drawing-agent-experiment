import csv
import json
import random
import shutil
from pathlib import Path
from .analysis import write_csv
from .core import validate
from .runner import verify_run_provenance


def blind_event(event):
    """Export only validated geometry/operations; raw responses remain private."""
    command = event['command']
    valid = event['outcome']['valid']
    if type(command) is not int or not 1 <= command <= 40 or type(valid) is not bool:
        raise ValueError('Malformed command metadata in audit log')
    action = None
    if valid:
        # Fail closed on an inconsistent legacy/tampered record rather than
        # exporting arbitrary fields under an asserted valid flag.
        validate(event['action'])
        action = {'op': event['action']['op']}
        if action['op'] == 'draw':
            action['points'] = [list(p) for p in event['action']['points']]
    return {'command': command, 'action': action, 'valid': valid}


def prepare(root, output, seed):
    root, output = Path(root), Path(output)
    if output.exists():
        raise ValueError('Use a new blind packet directory to preserve assignments')
    summaries = list(root.glob('*/summary.json'))
    if not summaries:
        raise ValueError('No completed runs to blind')
    for file in summaries:
        if json.loads(file.read_text())['data_kind'] != 'real_model':
            raise ValueError('Research blind packet refuses technical fixtures')
        verify_run_provenance(file.parent, 'real_model')
    random.Random(seed).shuffle(summaries)
    output.mkdir(parents=True)
    private = output / 'coordinator_only'; private.mkdir(mode=0o700)
    mapping, blank = [], []
    for i, file in enumerate(summaries):
        anonymous = f'item-{i+1:04d}'
        source = file.parent
        summary = json.loads(file.read_text())
        packet = output / 'raters' / anonymous; packet.mkdir(parents=True)
        manifest = json.loads((source / 'manifest.json').read_text())
        (packet / 'target-instructions.txt').write_text(manifest['target']['prompt'])
        for name in ('final.png', 'final.svg', 'target.png'):
            shutil.copyfile(source / name, packet / name)
        # Do not expose prompt, demonstration, condition, model text, usage, or run ID.
        events = [json.loads(f.read_text()) for f in sorted(source.glob('*.event.json'))]
        actions = [blind_event(e) for e in events]
        (packet / 'actions.json').write_text(json.dumps(actions, indent=2, allow_nan=False))
        for frame in source.glob('[0-9][0-9].png'):
            shutil.copyfile(frame, packet / frame.name)
        mapping.append({'blind_id': anonymous, 'run_id': summary['run_id']})
        blank.append({'blind_id': anonymous, 'completion': '', 'notes': ''})
    write_csv(private / 'mapping.csv', mapping, ['blind_id', 'run_id'])
    for rater in ('rater1', 'rater2'):
        write_csv(output / 'raters' / f'{rater}.csv', blank, ['blind_id', 'completion', 'notes'])
    write_csv(output / 'raters' / 'parts.csv', [], ['blind_id', 'rater_id', 'provenance', 'part', 'omitted', 'valid_shape', 'target_x', 'target_y', 'target_width', 'target_height', 'bbox_x', 'bbox_y', 'bbox_width', 'bbox_height', 'notes'])
    write_csv(output / 'raters' / 'redraws.csv', [], ['blind_id', 'rater_id', 'provenance', 'command_before', 'command_after', 'part', 'layout_error_before', 'layout_error_after', 'notes'])
