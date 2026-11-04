"""Read-only capability snapshot; does not load weights or inspect credentials."""
import json
import os
import platform
import shutil
from pathlib import Path

def read(path):
    try: return Path(path).read_text().strip()
    except OSError: return None
cpuinfo=read('/proc/cpuinfo') or ''
model=next((line.split(':',1)[1].strip() for line in cpuinfo.splitlines() if line.startswith('model name')),None)
meminfo=read('/proc/meminfo') or ''
print(json.dumps({'os':platform.platform(),'cpu_model':model,'logical_cpus':os.cpu_count(),
    'memory':{line.split(':')[0]:line.split(':')[1].strip() for line in meminfo.splitlines() if line.startswith(('MemTotal:','MemAvailable:'))},
    'cgroup_memory_max':read('/sys/fs/cgroup/memory.max'),'cgroup_cpu_max':read('/sys/fs/cgroup/cpu.max'),
    'gpu_device_nodes':[str(p) for p in Path('/dev').glob('nvidia*')],
    'disk_free_bytes':shutil.disk_usage('.').free,
    'note':'No model throughput, multi-image capacity or environment lifetime is established by this snapshot.'},indent=2))
