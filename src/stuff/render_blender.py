"""Launcher: builds a job from the timeline and runs Blender (pip `bpy` in-process, or the `blender` binary)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .compose import encode_frames_dir
from .config import video_fps, video_size


def make_job(tl, cfg, workdir, sprite_dir, only=None):
    W, H = video_size(cfg)
    r = cfg["render"]
    shots = [s for s in tl["shots"] if only is None or s["id"] in only]
    return {"width": W, "height": H, "fps": video_fps(cfg), "engine": r["engine"], "samples": r["samples"],
            "sprite_dir": str(Path(sprite_dir).resolve()), "out_dir": str((Path(workdir) / "frames").resolve()),
            "shots": shots}


def run_job(job, workdir):
    jp = Path(workdir) / "blender_job.json"
    jp.write_text(json.dumps(job))
    try:
        import bpy  # noqa: F401  (pip install bpy==4.2.0 on Python 3.11)
        from .blender import scene_runner
        return scene_runner.run(job)
    except ImportError:
        pass
    exe = os.environ.get("BLENDER_BIN") or shutil.which("blender")
    if not exe:
        raise RuntimeError("Blender not found: `pip install bpy==4.2.0` (Python 3.11) or set BLENDER_BIN to a blender binary")
    runner = Path(__file__).parent / "blender" / "scene_runner.py"
    r = subprocess.run([exe, "-b", "-noaudio", "--python", str(runner), "--", str(jp)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"blender failed ({r.returncode})\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return json.loads((Path(job["out_dir"]) / "done.json").read_text())


def render_all(tl, cfg, workdir, sprite_dir, clips):
    job = make_job(tl, cfg, workdir, sprite_dir)
    run_job(job, workdir)
    fps = video_fps(cfg)
    for s, clip in zip(tl["shots"], clips):
        encode_frames_dir(Path(job["out_dir"]) / f"shot_{s['id']:03d}", fps, clip)
