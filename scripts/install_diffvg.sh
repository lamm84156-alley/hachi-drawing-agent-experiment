#!/bin/sh
set -eu
# Pin renderer and update only its Python bindings for Python 3.12 compatibility.
git clone --recursive https://github.com/BachiLi/diffvg.git /tmp/hachi-diffvg
cd /tmp/hachi-diffvg
git checkout 85802a71fbcc72d79cb75716eb4da4392fd09532
git submodule update --init --recursive
git -C pybind11 fetch origin tag v2.13.6
git -C pybind11 checkout v2.13.6
python - <<'PYTHON'
from pathlib import Path
p = Path('setup.py')
p.write_text(p.read_text().replace("'-DPYTHON_INCLUDE_PATH=' + include_path", "'-DPYTHON_INCLUDE_PATH=' + include_path, '-DPYTHON_INCLUDE_DIR=' + include_path"))
PYTHON
DIFFVG_CUDA=0 python setup.py bdist_wheel
python -m pip install --no-deps dist/*.whl
