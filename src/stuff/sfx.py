"""Procedural sound effects (numpy only, no licensing issues)."""
from __future__ import annotations

import numpy as np

SR = 48000


def _rng(seed):
    return np.random.default_rng(seed)


def _lp(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode="same")


def _norm(x, peak=0.9):
    m = float(np.max(np.abs(x))) or 1.0
    return (x / m * peak).astype(np.float32)


def whoosh(dur=0.9, seed=1):
    n = int(SR * dur)
    x = _rng(seed).standard_normal(n)
    x = _lp(x, 24) - _lp(x, 200)
    return _norm(x * np.sin(np.linspace(0, np.pi, n)) ** 2)


def boom(dur=1.8, seed=2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    phase = 2 * np.pi * np.cumsum(90 * np.exp(-t * 2.2) + 30) / SR
    x = np.sin(phase) * np.exp(-t * 2.0)
    noise = _lp(_rng(seed).standard_normal(n), 30) * np.exp(-t * 5.0)
    return _norm(x + 0.8 * noise)


def ding(dur=1.0, seed=3):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return _norm((np.sin(2 * np.pi * 880 * t) + 0.5 * np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 4.5), 0.6)


def rumble(dur=1.6, seed=4):
    n = int(SR * dur)
    x = _lp(_rng(seed).standard_normal(n), 300)
    return _norm(x * np.sin(np.linspace(0, np.pi, n)), 0.8)


def spark(dur=0.8, seed=5):
    n = int(SR * dur)
    r = _rng(seed)
    x = (r.random(n) > 0.9985) * r.standard_normal(n)
    x = x + 0.05 * (r.standard_normal(n) - _lp(r.standard_normal(n), 8))
    return _norm(_lp(x, 3) * np.linspace(1, 0.1, n), 0.6)


def pop(dur=0.08, seed=6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return _norm(np.sin(2 * np.pi * np.cumsum(700 - 5000 * t) / SR) * np.exp(-t * 40), 0.6)


SOUNDS = {"whoosh": whoosh, "boom": boom, "ding": ding, "rumble": rumble, "spark": spark, "pop": pop}


def render_track(events, total_seconds, volume=0.45):
    """events: iterable of (name, start_seconds, gain). Returns mono float32 at SR."""
    out = np.zeros(int(SR * total_seconds) + SR, dtype=np.float32)
    for name, t, gain in events:
        fn = SOUNDS.get(name)
        if fn is None:
            continue
        clip = fn() * float(gain)
        i = int(max(0.0, t) * SR)
        j = min(len(out), i + len(clip))
        if j > i:
            out[i:j] += clip[: j - i]
    return np.clip(out[: int(SR * total_seconds)] * volume, -1, 1).astype(np.float32)
