"""Local audit integrity checks, not cryptographic attestation of a provider."""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
from .design import digest


def file_sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def runtime_versions():
    code = Path(__file__).parent
    binary = importlib.util.find_spec('diffvg')
    binding = importlib.util.find_spec('pydiffvg')
    if binary is None or binding is None:
        raise RuntimeError('DiffVG runtime unavailable; cannot freeze renderer identity')
    binding_root = Path(binding.origin).parent
    return {'schema_version': 1, 'python': platform.python_version(),
            'code_sha256': digest({p.name:file_sha256(p) for p in sorted(code.glob('*.py'))}),
            'renderer_binary_sha256':file_sha256(binary.origin),
            'renderer_python_sha256':digest({str(p.relative_to(binding_root)):file_sha256(p) for p in sorted(binding_root.rglob('*.py'))}),
            'packages':{name:importlib.metadata.version(name) for name in
                        ('hachi-drawing-experiment','diffvg','torch','numpy','Pillow','svgpathtools')}}


def verify_response_chain(directory, n, source, runtime, expected_packet=None):
    directory = Path(directory)
    records = {}
    for kind in ('request','response','pending','receipt'):
        path = directory/f'{n:02d}.{kind}.json'
        if not path.exists():
            raise ValueError(f'Missing {kind} integrity record for command {n+1}; manual review required')
        records[kind] = json.loads(path.read_text())
        if file_sha256(path) != digest(records[kind]):
            raise ValueError(f'Saved {kind} bytes differ from immutable canonical encoding')
    request_hash = digest(records['request'])
    if expected_packet is not None and digest(expected_packet) != request_hash:
        raise ValueError('Regenerated request differs from immutable saved request')
    if records['pending'].get('request_sha256') != request_hash:
        raise ValueError('Saved request hash differs from pending-call record')
    response, receipt = records['response'], records['receipt']
    if response.get('request_sha256') != request_hash or receipt.get('request_sha256') != request_hash:
        raise ValueError('Request/response association mismatch')
    if response.get('provenance') != source:
        raise ValueError('Saved response provenance missing or inconsistent')
    if response.get('runtime_sha256') != digest(runtime):
        raise ValueError('Saved response runtime version mismatch')
    if receipt.get('response_sha256') != digest(response):
        raise ValueError('Saved response hash differs from immutable receipt')
    return response
