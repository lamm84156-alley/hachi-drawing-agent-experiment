import csv
import json
import random
import shutil
from pathlib import Path
from .analysis import write_csv


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
        actions = [{'command': e['command'], 'action': e['action'], 'valid': e['outcome']['valid']} for e in events]
        (packet / 'actions.json').write_text(json.dumps(actions, indent=2))
        for frame in source.glob('[0-9][0-9].png'):
            shutil.copyfile(frame, packet / frame.name)
        mapping.append({'blind_id': anonymous, 'run_id': summary['run_id']})
        blank.append({'blind_id': anonymous, 'completion': '', 'notes': ''})
    write_csv(private / 'mapping.csv', mapping, ['blind_id', 'run_id'])
    for rater in ('rater1', 'rater2'):
        write_csv(output / 'raters' / f'{rater}.csv', blank, ['blind_id', 'completion', 'notes'])
    write_csv(output / 'raters' / 'parts.csv', [], ['blind_id', 'rater_id', 'provenance', 'part', 'omitted', 'valid_shape', 'target_x', 'target_y', 'target_width', 'target_height', 'bbox_x', 'bbox_y', 'bbox_width', 'bbox_height', 'notes'])
    write_csv(output / 'raters' / 'redraws.csv', [], ['blind_id', 'rater_id', 'provenance', 'command_before', 'command_after', 'part', 'layout_error_before', 'layout_error_after', 'notes'])
