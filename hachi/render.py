"""DiffVG is mandatory for experimental feedback; no renderer fallback."""
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
from .core import svg, validate


def write_artifact_once(path, content):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f'Immutable rendered artifact differs: {path.name}')
        return
    path.write_bytes(content)


def render(paths, prefix, size, pen_width):
    import torch
    import pydiffvg
    pydiffvg.set_use_gpu(False)
    shapes, groups = [], []
    for a in paths:
        validate(a)
        points = torch.tensor(a['points'], dtype=torch.float32) * size
        shapes.append(pydiffvg.Path(num_control_points=torch.tensor([2] * ((len(points)-1)//3), dtype=torch.int32),
                                   points=points, stroke_width=torch.tensor(float(pen_width)), is_closed=False))
        groups.append(pydiffvg.ShapeGroup(shape_ids=torch.tensor([len(shapes)-1]), fill_color=None,
                                         stroke_color=torch.tensor([0., 0., 0., 1.])))
    if shapes:
        args = pydiffvg.RenderFunction.serialize_scene(size, size, shapes, groups)
        with torch.no_grad():
            rgba = pydiffvg.RenderFunction.apply(size, size, 2, 2, 0, None, *args)
            rgb = rgba[:, :, :3] * rgba[:, :, 3:4] + (1 - rgba[:, :, 3:4])
        pixels = (rgb.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    else:
        pixels = np.full((size, size, 3), 255, dtype=np.uint8)
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    write_artifact_once(prefix.with_suffix('.svg'), svg(paths, size, pen_width).encode())
    buffer = BytesIO()
    Image.fromarray(pixels).save(buffer, format='PNG')
    write_artifact_once(prefix.with_suffix('.png'), buffer.getvalue())
    return prefix.with_suffix('.png')
