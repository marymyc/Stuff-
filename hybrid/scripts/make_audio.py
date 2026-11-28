"""Mix narration + procedural score + frame-locked SFX, duck under voice, and master to -15.0 LUFS."""
import json
import os
import subprocess
import sys
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp import (  # noqa: E402
    SR,
    convolve_st,
    dbg,
    fades,
    integrated,
    limiter,
    lra,
    make_ir,
    ns,
    pan,
    place,
    read_wav,
    rng,
    st,
    true_peak,
    widen,
    write_wav,
)
from instruments import brush, glock, m2f, pad, pluck, triangle, vibes  # noqa: E402
from sfx_gen import whoosh  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VOICE_WAV = os.path.join(ROOT, "public", "audio", "voice.wav")
WORDS_JSON = os.path.join(ROOT, "public", "audio", "words.json")
MIX_WAV = os.path.join(ROOT, "public", "audio", "mix.wav")

TARGET_LUFS = -15.0
CEIL_DBTP = -1.2


def ensure_stereo(x, r, ms=12.0, amount=0.7):
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 2:
        return arr if arr.shape[0] == 2 else np.stack([arr[0], arr[0]])
    return widen(arr, r, ms, amount)


def build_music(n_samples: int, r: np.random.Generator) -> np.ndarray:
    """Light curious marimba/plucked groove matching animated explainer storytelling."""
    buf = np.zeros((2, n_samples))
    bpm = 112.0
    beat = 60.0 / bpm
    bar = 4 * beat
    chords = [(48, 52, 55), (53, 57, 60), (50, 53, 57), (55, 59, 62)]  # C - F - Dm - G
    n_bars = int(np.ceil((n_samples / SR) / bar))

    for b_idx in range(n_bars):
        t0 = b_idx * bar
        chord = chords[b_idx % len(chords)]
        if t0 < n_samples / SR:
            p = pad([m2f(m + 12) for m in chord], bar * 0.95, 0.35, r, att=0.18, rel=0.25)
            place(buf, p, t0, gain=0.16)
        for sub in range(8):
            ts = t0 + sub * (beat * 0.5)
            if ts >= n_samples / SR:
                break
            note = chord[sub % len(chord)] + (12 if sub % 4 == 2 else 0)
            pl = pluck(m2f(note), 0.55, r, dur=0.36, bright=0.45)
            place(buf, pan(pl, -0.25 if sub % 2 == 0 else 0.25), ts, gain=0.22)
            if sub % 2 == 1:
                place(buf, pan(brush(0.24, r, dur=0.12), 0.3), ts, gain=0.14)

    ir = make_ir(0.65, 19, hf=1.4)
    return buf * 0.85 + 0.15 * convolve_st(buf, ir)


def build_sfx(n_samples: int, r: np.random.Generator) -> np.ndarray:
    """Place frame-locked SFX cues at exact transition/reaction frames (f / 30.0)."""
    buf = np.zeros((2, n_samples))
    if 75 / 30.0 < n_samples / SR:
        place(buf, ensure_stereo(whoosh(0.35, r, peak=0.16, f_lo=300, f_hi=2400), r), 73 / 30.0, gain=0.42)
        chime = glock(1046.5, 0.7, r, dur=0.9) + triangle(0.4, r, dur=0.9, f=1568.0)
        place(buf, pan(chime, 0.0), 75 / 30.0, gain=0.26)
        place(buf, pan(vibes(m2f(72), 0.65, r, dur=0.6), -0.2), 78 / 30.0, gain=0.20)
    return buf


def build_duck_curve(n_samples: int, words: list[dict]) -> np.ndarray:
    dk = np.zeros(n_samples)
    for w in words:
        a = max(0, ns(float(w["s"]) - 0.04))
        b = min(n_samples, ns(float(w["e"]) + 0.06))
        dk[a:b] = -5.2
    return ndimage.uniform_filter1d(dk, ns(0.09), mode="nearest")


def main():
    with open(WORDS_JSON, encoding="utf-8") as f:
        meta = json.load(f)
    words = meta.get("words", [])

    if os.path.exists(VOICE_WAV):
        v_raw, sr = read_wav(VOICE_WAV)
        assert sr == SR, f"Expected {SR}Hz voice.wav, got {sr}"
        v = st(v_raw)
    else:
        dur_fallback = float(meta.get("durationSec", 5.0))
        v = np.zeros((2, ns(dur_fallback)))

    n_samples = v.shape[1]
    dur_total = n_samples / SR

    r = rng(2026)
    m_raw = build_music(n_samples, r)
    s_raw = build_sfx(n_samples, r)

    has_voice = np.max(np.abs(v)) > 1e-4
    v_lufs = integrated(v) if has_voice else -16.0
    m_lufs = integrated(m_raw)
    s_lufs = integrated(s_raw)
    m_gain = dbg((v_lufs - 11.5) - m_lufs) if np.isfinite(m_lufs) else 0.0
    s_gain = dbg((v_lufs - 9.0) - s_lufs) if np.isfinite(s_lufs) else 0.0

    dk = build_duck_curve(n_samples, words) if has_voice else np.zeros(n_samples)
    m = m_raw * m_gain * dbg(dk)[None, :]
    s = s_raw * s_gain * dbg(dk * 0.45)[None, :]

    mix0 = v + m + s
    end_idx = ns(max(0.0, dur_total - 0.04))
    mix0[:, end_idx:] *= np.linspace(1.0, 0.0, n_samples - end_idx)[None, :]

    gain_db = TARGET_LUFS - integrated(mix0)
    for _ in range(5):
        y, _ = limiter(mix0 * dbg(gain_db), ceil_db=CEIL_DBTP)
        cur_i = integrated(y)
        if abs(cur_i - TARGET_LUFS) < 0.03:
            break
        gain_db += TARGET_LUFS - cur_i

    y = fades(y, 0.002, 0.035)
    write_wav(MIX_WAV, y, bits=24)
    print(f"mix.wav written: {n_samples} samples ({dur_total:.3f}s), I={integrated(y):.2f} LUFS, TP={true_peak(y):.2f} dBTP, LRA={lra(y):.1f} LU")

    eb = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", MIX_WAV, "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    idx = eb.stderr.rfind("Summary:")
    print(eb.stderr[idx:] if idx >= 0 else eb.stderr[-800:])


if __name__ == "__main__":
    main()
