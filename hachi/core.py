import copy
import json
import math
from dataclasses import dataclass, field

BUDGET = 40
CONDITIONS = ('Original', 'Reordered', 'No Demo')


def validate(action):
    if not isinstance(action, dict):
        raise ValueError('Action must be an object')
    op = action.get('op')
    if op in ('undo', 'stop'):
        if set(action) != {'op'}:
            raise ValueError('Unexpected action fields')
        return
    if op != 'draw' or set(action) != {'op', 'points'}:
        raise ValueError('Expected draw with points, undo, or stop')
    points = action['points']
    if not isinstance(points, list) or len(points) not in (4, 7, 10, 13):
        raise ValueError('One connected path with 1–4 cubic segments required')
    for p in points:
        if not isinstance(p, list) or len(p) != 2:
            raise ValueError('Each point must be [x,y]')
        # Range-check integers before math.isfinite, which converts to float and
        # can overflow for otherwise valid Python arbitrary-precision integers.
        if any(type(v) not in (int, float) or not 0 <= v <= 1 or not math.isfinite(v) for v in p):
            raise ValueError('Coordinates must be finite numbers in [0,1]')


@dataclass
class Canvas:
    paths: list = field(default_factory=list)
    commands: int = 0
    invalid: int = 0
    stopped: bool = False

    def apply(self, action):
        if self.stopped or self.commands >= BUDGET:
            raise RuntimeError('Run has ended')
        self.commands += 1
        try:
            validate(action)
            op = action['op']
            if op == 'undo':
                if not self.paths:
                    raise ValueError('Nothing to undo')
                self.paths.pop()
            elif op == 'draw':
                self.paths.append(copy.deepcopy(action))
            else:
                self.stopped = True
            return {'valid': True, 'error': None}
        except ValueError as e:
            self.invalid += 1
            return {'valid': False, 'error': str(e)}


def svg(paths, size, pen_width):
    body = []
    for a in paths:
        validate(a)
        pts = [[v * size for v in p] for p in a['points']]
        d = f'M {pts[0][0]} {pts[0][1]}'
        for i in range(1, len(pts), 3):
            d += ' C ' + ' '.join(str(v) for p in pts[i:i+3] for v in p)
        body.append(f'<path d="{d}" fill="none" stroke="black" stroke-width="{pen_width}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}"><rect width="100%" height="100%" fill="white"/>' + ''.join(body) + '</svg>'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
