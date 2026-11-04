import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse
import requests
from PIL import Image
from .core import Canvas, canonical
from .design import demo_actions, digest, validate_protocol
from .render import render


def save(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        f.write(canonical(value))
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def load(path):
    return json.loads(Path(path).read_text())


def picture(path):
    return {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(Path(path).read_bytes()).decode()}}


def text(s):
    return {'type': 'text', 'text': s}


class API:
    """Single-attempt OpenAI-compatible Chat Completions transport."""
    def __init__(self, endpoint, backend='auto', timeout_seconds=120):
        parsed = urlparse(endpoint)
        loopback = parsed.hostname in ('localhost', '127.0.0.1', '::1')
        self.local = loopback or backend == 'self_hosted'
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and loopback):
            raise ValueError('HTTPS required except for a loopback local-model server')
        if parsed.username or parsed.password:
            raise ValueError('Credentials must not be embedded in endpoint URLs')
        self.endpoint = endpoint
        self.key = os.environ.get('HACHI_API_KEY') if loopback else os.environ['HACHI_API_KEY']
        if timeout_seconds <= 0:
            raise ValueError('Positive request timeout required')
        self.timeout_seconds = timeout_seconds

    def __call__(self, packet):
        headers = {'Authorization': 'Bearer ' + self.key} if self.key else {}
        started = time.monotonic()
        r = requests.post(self.endpoint, headers=headers, json=packet, timeout=self.timeout_seconds, allow_redirects=False)
        # Preserve provider error body; headers/auth are never serialized.
        return {'http_status': r.status_code, 'body': r.text, 'elapsed_seconds': time.monotonic()-started,
                'endpoint': self.endpoint, 'execution_kind': 'local_model' if self.local else 'remote_api'}


def replay_demo(demo, condition, seed, directory, protocol):
    actions, order = demo_actions(demo, condition, seed)
    context, paths = [], []
    for i, action in enumerate(actions):
        before = render(paths, directory / f'demo-{i}-before', protocol['image_size'], protocol['pen_width'])
        paths.append(action)
        after = render(paths, directory / f'demo-{i}-after', protocol['image_size'], protocol['pen_width'])
        # No semantic part names, step labels, retrieval, or reordered-condition labels.
        context.extend([picture(before), text(canonical(action)), picture(after)])
    return context, order


def execute(run, target, demo, protocol, directory, transport):
    """Durable response-before-replay. Uncertain outbound calls block automatic retry."""
    validate_protocol(protocol)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute(run, target, demo, protocol, directory, transport)


def _execute(run, target, demo, p, directory, transport):
    image_path = Path(target['image'])
    identity = {'run': run, 'protocol': p, 'target': target, 'demo': demo,
                'target_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest()}
    manifest = directory / 'manifest.json'
    if manifest.exists() and load(manifest) != identity:
        raise ValueError('Resume inputs differ from frozen manifest')
    save(manifest, identity)
    with Image.open(image_path) as img:
        if img.size != (p['image_size'], p['image_size']):
            raise ValueError('Target resolution must match frozen protocol')
        img.convert('RGB').save(directory / 'target.png')
    demo_context, order = replay_demo(demo, run['condition'], run['permutation_seed'], directory, p)
    save(directory / 'permutation.json', order)
    canvas, history = Canvas(), []
    while not canvas.stopped and canvas.commands < 40:
        n = canvas.commands
        prefix = directory / f'{n:02d}'
        feedback = render(canvas.paths, prefix, p['image_size'], p['pen_width'])
        req, res, pending = [directory / f'{n:02d}.{suffix}.json' for suffix in ('request', 'response', 'pending')]
        limited = history[-p['history_limit']:] if p['history_limit'] else []
        content = [text(p['prompt']), text(target['prompt']), text('Target'), picture(directory / 'target.png')]
        content += demo_context + [text('Current canvas'), picture(feedback), text(canonical(limited)), text(f'Commands used: {n}/40')]
        packet = {'model': p['model'], 'temperature': p['temperature'], 'max_tokens': p['max_output_tokens'],
                  'messages': [{'role': 'user', 'content': content}]}
        if p.get('seed_supported'):
            packet['seed'] = run['execution_seed']
        if res.exists():
            response = load(res)
        else:
            if pending.exists():
                raise RuntimeError('Uncertain API outcome: inspect pending call; no automatic paid retry')
            save(req, packet)
            save(pending, {'started_at': time.time(), 'request_sha256': digest(packet)})
            try:
                response = transport(packet)
            except Exception as e:
                save(directory / f'{n:02d}.failure.json', {'type': type(e).__name__, 'outcome': 'uncertain'})
                raise
            save(res, response)
        if response['http_status'] != 200:
            raise RuntimeError('Provider failure saved; resolve explicitly before continuation')
        body = json.loads(response['body'])
        if body.get('model') != p['model']:
            raise RuntimeError('Provider model identifier differs from frozen model; inspect before continuing')
        try:
            raw = body['choices'][0]['message']['content']
            action = json.loads(raw)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            action = None
        outcome = canvas.apply(action)
        event = {'command': n + 1, 'action': action, 'outcome': outcome, 'model': body['model'],
                 'usage': body.get('usage'), 'response_id': body.get('id')}
        save(directory / f'{n:02d}.event.json', event)
        history.append(event)
    render(canvas.paths, directory / 'final', p['image_size'], p['pen_width'])
    summary = {'run_id': run['run_id'], 'target_id': run['target_id'], 'condition': run['condition'],
               'commands': canvas.commands, 'invalid': canvas.invalid, 'stop_reason': 'stop' if canvas.stopped else 'budget',
               'completion': None, 'data_kind': 'real_model' if isinstance(transport, API) else 'technical_test'}
    save(directory / 'summary.json', summary)
    return summary
