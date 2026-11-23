from __future__ import annotations

import copy
import json
from pathlib import Path

DEFAULTS = {
    "video": {"width": 720, "height": 1280, "fps": 30, "min_seconds": 55, "max_seconds": 75, "tail_hold": 0.5},
    "voice": {
        "backend": "chatterbox",      # chatterbox | silent (silent = tests only)
        "reference_wav": None,        # path to a licensed American-male clip (10+ s) for a locked identity
        "seed": 1234,
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
        "temperature": 0.7,
        "gap_seconds": 0.12,
        "lead": 0.04,
    },
    "align": {"backend": "proportional"},   # proportional | whisper
    "captions": {"font": "DejaVu Sans", "size_ratio": 0.068, "y_ratio": 0.70, "words_per_card": 2,
                 "pop": True, "highlight": "&H0000E0FF&"},
    "render": {"renderer": "blender", "engine": "CYCLES", "samples": 24, "scale": 1.0, "fps": None},
    "sfx": {"enabled": True, "volume": 0.45},
    "transitions": {"dissolve_seconds": 0.35},
}


def deep_merge(base: dict, extra: dict) -> dict:
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path=None, overrides=None) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    if path:
        deep_merge(cfg, json.loads(Path(path).read_text(encoding="utf-8")))
    if overrides:
        deep_merge(cfg, overrides)
    return cfg


def even(n) -> int:
    n = int(round(n))
    return max(2, n - n % 2)


def video_size(cfg: dict):
    s = cfg["render"].get("scale") or 1.0
    return even(cfg["video"]["width"] * s), even(cfg["video"]["height"] * s)


def video_fps(cfg: dict) -> int:
    return int(cfg["render"].get("fps") or cfg["video"]["fps"])
