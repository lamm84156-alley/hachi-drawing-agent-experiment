import base64
import fcntl
import hashlib
import json
from io import BytesIO
import os
from pathlib import Path
import time
from urllib.parse import urlparse
import requests
from PIL import Image
from .core import Canvas, canonical
from .design import demo_actions, digest, validate_protocol
from .render import render, write_artifact_once
from .integrity import runtime_versions, verify_response_chain, file_sha256


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


def save_once(path, value):
    if Path(path).exists():
        if load(path) != value:
            raise ValueError(f'Immutable audit record differs: {Path(path).name}')
        return
    save(path, value)


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


def execution_source(transport):
    # Only the concrete production adapter is a real-model source. Test
    # callables/subclasses stay technical regardless of the response they return.
    if type(transport) is API:
        return {'data_kind': 'real_model', 'adapter': 'hachi.runner.API',
                'execution_kind': 'local_model' if transport.local else 'remote_api',
                'endpoint': transport.endpoint}
    return {'data_kind': 'technical_test', 'adapter': 'test_callable',
            'execution_kind': 'technical_test'}


def response_to_event(response, canvas, model):
    """Single interpretation of original model output for execution and audit."""
    if response['http_status'] != 200:
        raise RuntimeError('Provider failure saved; resolve explicitly before continuation')
    body = json.loads(response['body'])
    if not isinstance(body, dict) or body.get('model') != model:
        raise RuntimeError('Provider model identifier differs from frozen model; inspect before continuing')
    try:
        raw = body['choices'][0]['message']['content']
        action = json.loads(raw)
    except (KeyError, IndexError, TypeError, ValueError, RecursionError):
        # ValueError also includes Python's integer-string digit limit, not just
        # JSON syntax errors. The original content remains in response['body'].
        action = None
    outcome = canvas.apply(action)
    n = canvas.commands - 1
    return {'command': n + 1, 'action': action if outcome['valid'] else None,
            'response_file': f'{n:02d}.response.json', 'outcome': outcome, 'model': body['model'],
            'usage': body.get('usage'), 'response_id': body.get('id')}


def summary_from_state(run, canvas, source, directory):
    return {'run_id': run['run_id'], 'target_id': run['target_id'], 'condition': run['condition'],
            'commands': canvas.commands, 'invalid': canvas.invalid,
            'stop_reason': 'stop' if canvas.stopped else 'budget', 'completion': None,
            'data_kind': source['data_kind'],
            'artifacts_sha256': {f.name:file_sha256(f) for f in sorted(Path(directory).iterdir())
                                if f.suffix in ('.svg','.png')}}


def verify_run_provenance(directory, required_kind):
    """Fail closed for legacy, mixed, missing, or reclassified audit sources."""
    directory = Path(directory)
    manifest, summary = load(directory/'manifest.json'), load(directory/'summary.json')
    source = manifest.get('execution_source')
    runtime = manifest.get('runtime')
    if manifest.get('schema_version') != 2 or not runtime:
        raise ValueError('Legacy provenance lacks frozen code/renderer identity')
    if not source or source.get('data_kind') != required_kind or summary.get('data_kind') != required_kind:
        raise ValueError('Run provenance does not establish the required data source')
    if required_kind == 'real_model' and (source.get('adapter') != 'hachi.runner.API' or
            source.get('execution_kind') not in ('local_model', 'remote_api') or not source.get('endpoint')):
        raise ValueError('Real-model adapter provenance missing')
    response_files = {p.name for p in directory.glob('*.response.json')}
    commands = len(response_files)
    if not 1 <= commands <= 40:
        raise ValueError('Invalid command count in provenance record')
    expected_files = {f'{n:02d}.response.json' for n in range(commands)}
    if response_files != expected_files:
        raise ValueError('Response coverage does not match completed commands')
    if {p.name for p in directory.glob('*.event.json')} != {f'{n:02d}.event.json' for n in range(commands)}:
        raise ValueError('Event coverage does not match response records')
    canvas = Canvas()
    for n in range(commands):
        response = verify_response_chain(directory, n, source, runtime)
        try:
            expected_event = response_to_event(response, canvas, manifest['protocol']['model'])
        except (RuntimeError, ValueError, KeyError, TypeError) as error:
            raise ValueError(f'Cannot replay audited response {n+1}') from error
        event_path = directory/f'{n:02d}.event.json'
        if file_sha256(event_path) != digest(expected_event):
            raise ValueError('Saved event differs from original-response replay')
    if not canvas.stopped and canvas.commands < 40:
        raise ValueError('Summary claims completion of an unfinished response sequence')
    expected_summary = summary_from_state(manifest['run'], canvas, source, directory)
    if file_sha256(directory/'summary.json') != digest(expected_summary):
        raise ValueError('Saved summary differs from frozen run and original-response replay')
    artifacts = summary.get('artifacts_sha256')
    if not artifacts or not {'final.png','final.svg','target.png'} <= set(artifacts):
        raise ValueError('Rendered artifact provenance missing')
    for name, expected_hash in artifacts.items():
        if Path(name).name != name or not (directory/name).is_file() or file_sha256(directory/name) != expected_hash:
            raise ValueError('Rendered artifact hash mismatch')
    return source


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


def execute(run, target, demo, protocol, directory, transport, frozen_material=None):
    """Durable response-before-replay. Uncertain outbound calls block automatic retry."""
    validate_protocol(protocol)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute(run, target, demo, protocol, directory, transport, frozen_material)


def _execute(run, target, demo, p, directory, transport, frozen_material):
    image_path = Path(target['image'])
    image_bytes = image_path.read_bytes()
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    if frozen_material is not None and (frozen_material['target'] != target or frozen_material['demo'] != demo or
                                       frozen_material['image_sha256'] != image_hash):
        raise ValueError('Run inputs differ from frozen campaign materials')
    source = execution_source(transport)
    runtime = runtime_versions()
    identity = {'schema_version': 2, 'runtime': runtime, 'run': run, 'protocol': p, 'target': target, 'demo': demo, 'execution_source': source,
                'target_sha256': image_hash, 'frozen_material_sha256': digest(frozen_material)}
    manifest = directory / 'manifest.json'
    if manifest.exists() and load(manifest) != identity:
        raise ValueError('Resume inputs, execution provenance, or runtime versions differ from frozen manifest; legacy logs require review')
    save_once(manifest, identity)
    with Image.open(BytesIO(image_bytes)) as img:
        if img.size != (p['image_size'], p['image_size']):
            raise ValueError('Target resolution must match frozen protocol')
        buffer = BytesIO()
        img.convert('RGB').save(buffer, format='PNG')
        write_artifact_once(directory / 'target.png', buffer.getvalue())
    demo_context, order = replay_demo(demo, run['condition'], run['permutation_seed'], directory, p)
    save_once(directory / 'permutation.json', order)
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
            response = verify_response_chain(directory, n, source, runtime, packet)
        else:
            if pending.exists():
                raise RuntimeError('Uncertain API outcome: inspect pending call; no automatic paid retry')
            save_once(req, packet)
            save_once(pending, {'started_at': time.time(), 'request_sha256': digest(packet)})
            try:
                response = {**transport(packet), 'provenance': source,
                            'request_sha256': digest(packet), 'runtime_sha256': digest(runtime)}
            except Exception as e:
                save(directory / f'{n:02d}.failure.json', {'type': type(e).__name__, 'outcome': 'uncertain'})
                raise
            save_once(res, response)
            save_once(directory / f'{n:02d}.receipt.json', {'request_sha256': digest(packet),
                                                         'response_sha256': digest(response)})
        if response.get('provenance') != source:
            raise ValueError('Saved response provenance missing or inconsistent; no reclassification allowed')
        event = response_to_event(response, canvas, p['model'])
        save_once(directory / f'{n:02d}.event.json', event)
        history.append(event)
    render(canvas.paths, directory / 'final', p['image_size'], p['pen_width'])
    summary = summary_from_state(run, canvas, response['provenance'], directory)
    save_once(directory / 'summary.json', summary)
    return summary
