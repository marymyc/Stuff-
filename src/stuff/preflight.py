"""Pre-flight checks for the stages that tend to break: ffmpeg/fonts, Blender render stack, Chatterbox voice."""
from __future__ import annotations

import importlib.metadata as md
import json
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np


def _check(name, fn, results):
    t0 = time.time()
    try:
        detail = fn()
        results.append({"name": name, "ok": True, "detail": detail, "seconds": round(time.time() - t0, 1)})
    except Exception as e:  # noqa: BLE001
        results.append({"name": name, "ok": False, "detail": f"{type(e).__name__}: {e}",
                        "trace": traceback.format_exc()[-2500:], "seconds": round(time.time() - t0, 1)})


def _ver(pkg):
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return None


def light(out, cfg, results):
    def env():
        return {"python": sys.version.split()[0], "platform": platform.platform(),
                "numpy": _ver("numpy"), "scipy": _ver("scipy"), "Pillow": _ver("Pillow"), "soundfile": _ver("soundfile")}

    def ff():
        from .compose import ffmpeg_has_filter
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg missing")
        v = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.splitlines()[0]
        miss = [f for f in ("ass", "xfade") if not ffmpeg_has_filter(f)]
        if miss:
            raise RuntimeError(f"ffmpeg lacks filters: {miss}")
        return v

    def fonts():
        r = subprocess.run(["fc-list"], capture_output=True, text=True).stdout
        if "DejaVu Sans" not in r:
            raise RuntimeError("DejaVu Sans not installed (apt install fonts-dejavu-core)")
        return "DejaVu Sans present"

    _check("environment", env, results)
    _check("ffmpeg (libass + xfade)", ff, results)
    _check("caption font", fonts, results)


def blender(out, cfg, results):
    from .config import load_config
    from .planner import build_plan
    from .sprites import ensure_sprites, pairs_from_plan

    def imp():
        import bpy
        return f"bpy {bpy.app.version_string}"

    _check("import bpy", imp, results)
    if not results[-1]["ok"]:
        return

    def render_kits():
        from PIL import Image
        from . import render_blender
        wd = Path(out) / "blender_preflight"
        wd.mkdir(parents=True, exist_ok=True)
        c = load_config(None, {"render": {"engine": "CYCLES", "samples": 2, "scale": 0.25, "fps": 6}})
        plan = build_plan("Soldiers marched across the valley. A train raced through the canyon. "
                          "He walked into the lab. Then the wall exploded.", "pf")
        kits_cycle = ["fortress", "canyon", "interior", "field"]
        sizes = ["wide", "medium", "close", "medium_low"]
        moves = ["pull_back", "orbit_slow", "push_in", "dutch_push"]
        shots = []
        for i, s in enumerate(plan["shots"][:4]):
            s.update(kit=kits_cycle[i], shot_size=sizes[i], camera_move=moves[i], render_seconds=0.5,
                     frames_override=2, tod=["day", "dusk", "night", "dawn"][i],
                     characters=[{"role": "hero", "expression": "worried", "side": "left"},
                                 {"role": "rival", "expression": "rage", "side": "right"}],
                     props=["cart", "lamp"] if i == 0 else ["table"] if i == 2 else [],
                     fx=["explosion"] if i == 3 else [])
            shots.append(s)
        sprite_dir = wd / "sprites"
        ensure_sprites(pairs_from_plan({"shots": shots}), sprite_dir)
        job = render_blender.make_job({"shots": shots}, c, wd, sprite_dir)
        t0 = time.time()
        render_blender.run_job(job, wd)
        det = []
        for s in shots:
            files = sorted((Path(job["out_dir"]) / f"shot_{s['id']:03d}").glob("f_*.png"))
            if not files:
                raise RuntimeError(f"no frames for shot {s['id']} ({s['kit']})")
            a = np.asarray(Image.open(files[-1]).convert("L"), dtype=float)
            if a.std() < 3:
                raise RuntimeError(f"frame for kit {s['kit']} is blank (std={a.std():.2f})")
            det.append(f"{s['kit']}:{len(files)}f std={a.std():.1f}")
            Image.open(files[-1]).save(Path(out) / f"preview_{s['kit']}.png")
        return f"{'; '.join(det)}; {time.time() - t0:.1f}s total"

    _check("render 4 kits (Cycles CPU, tiny)", render_kits, results)


def _f0(x, sr):
    x = x - x.mean()
    n, hop = int(0.04 * sr), int(0.02 * sr)
    lo, hi = int(sr / 400), int(sr / 60)
    out = []
    for i in range(0, len(x) - n, hop):
        f = x[i:i + n]
        if np.sqrt((f ** 2).mean()) < 0.01:
            continue
        ac = np.correlate(f, f, "full")[n - 1:]
        if ac[0] <= 0:
            continue
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] / ac[0] > 0.35:
            out.append(sr / k)
    return float(np.median(out)) if out else 0.0


def _spec(x, sr):
    n = 1024
    frames = [x[i:i + n] * np.hanning(n) for i in range(0, len(x) - n, n // 2) if np.sqrt((x[i:i + n] ** 2).mean()) > 0.01]
    mag = np.log1p(np.abs(np.fft.rfft(np.array(frames), axis=1))).mean(axis=0)
    mag = mag[: int(len(mag) * 8000 / (sr / 2))]
    return np.array([b.mean() for b in np.array_split(mag, 40)])


def voice(out, cfg, results):
    import soundfile as sf
    holder = {}

    def load():
        from .tts import ChatterboxVoice
        c = dict(cfg["voice"], backend="chatterbox")
        holder["v"] = ChatterboxVoice(c)
        return f"chatterbox-tts {_ver('chatterbox-tts')}, torch {_ver('torch')}, ref={'yes' if c.get('reference_wav') else 'built-in default'}"

    _check("load Chatterbox", load, results)
    if not results[-1]["ok"]:
        return

    def synth():
        v, seed = holder["v"], cfg["voice"]["seed"]
        texts = ["In 1869, two railroad companies were racing across the desert.",
                 "The owner laughed, and the sun heated the steel."]
        wavs = []
        for i, t in enumerate(texts):
            t0 = time.time()
            x = v.synth(t, seed)
            sf.write(Path(out) / f"voice_test_{i}.wav", x, v.sr)
            wavs.append(x)
            holder.setdefault("times", []).append(round(time.time() - t0, 1))
        holder["wavs"], holder["sr"] = wavs, v.sr
        if any(len(w) / v.sr < 0.8 or np.abs(w).max() < 0.05 for w in wavs):
            raise RuntimeError("generated audio too short or silent")
        return f"durations={[round(len(w) / v.sr, 2) for w in wavs]}s gen_time={holder['times']}s"

    _check("generate 2 test sentences", synth, results)
    if not results[-1]["ok"]:
        return

    def ident():
        sr, w = holder["sr"], holder["wavs"]
        f0 = [_f0(x, sr) for x in w]
        sim = float(np.corrcoef(_spec(w[0], sr), _spec(w[1], sr))[0, 1])
        male = all(70 <= f <= 175 for f in f0 if f)
        return f"f0_median_hz={[round(f) for f in f0]} (adult male typically 85-155) spectral_corr={sim:.3f} male_range={male}"

    _check("voice identity metrics (crude)", ident, results)


def run_preflight(mode, out, cfg):
    outp = Path(out)
    outp.mkdir(parents=True, exist_ok=True)
    results = []
    modes = ["light", "blender", "voice"] if mode == "all" else [mode]
    for m in modes:
        {"light": light, "blender": blender, "voice": voice}[m](outp, cfg, results)
    ok = all(r["ok"] for r in results)
    rep = {"mode": mode, "ok": ok, "checks": results}
    (outp / f"preflight_{mode}.json").write_text(json.dumps(rep, indent=2))
    lines = [f"# Preflight `{mode}`: {'PASS' if ok else 'FAIL'}", ""]
    for r in results:
        lines.append(f"- {'PASS' if r['ok'] else 'FAIL'} **{r['name']}** ({r['seconds']}s): {r['detail']}")
        if not r["ok"]:
            lines.append("```\n" + r.get("trace", "") + "\n```")
    (outp / f"preflight_{mode}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if ok else 1
