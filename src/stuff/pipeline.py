"""Orchestration: script -> plan -> voice -> timeline -> sprites -> clips -> captions -> mix -> final MP4."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import compose
from .align import build_timeline
from .captions import build_ass
from .config import video_fps, video_size
from .planner import build_plan, validate_plan
from .sprites import ensure_sprites, pairs_from_plan
from .tts import synthesize_plan


def _log(msg):
    print(f"[stuff] {msg}", flush=True)


def stage_plan(script_path, workdir, plan_path=None):
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    if plan_path:
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    else:
        text = Path(script_path).read_text(encoding="utf-8")
        plan = build_plan(text, Path(script_path).stem)
    errs = validate_plan(plan)
    if errs:
        raise ValueError("invalid plan: " + "; ".join(errs))
    (wd / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan


def stage_timeline(plan, workdir, cfg, force_voice=False):
    wd = Path(workdir)
    manifest = synthesize_plan(plan, wd, cfg, force=force_voice)
    tl = build_timeline(plan, manifest, cfg)
    (wd / "timeline.json").write_text(json.dumps(tl, indent=2, ensure_ascii=False), encoding="utf-8")
    lo, hi = cfg["video"]["min_seconds"], cfg["video"]["max_seconds"]
    if not lo <= tl["total_seconds"] <= hi:
        _log(f"WARNING: total {tl['total_seconds']}s is outside the {lo}-{hi}s target; adjust the script length")
    return tl


def stage_render(tl, workdir, cfg):
    wd = Path(workdir)
    clips_dir = wd / "clips"
    clips_dir.mkdir(exist_ok=True)
    sprite_dir = wd / "sprites"
    ensure_sprites(pairs_from_plan({"shots": tl["shots"]}), sprite_dir)
    renderer = cfg["render"]["renderer"]
    clips = [clips_dir / f"shot_{s['id']:03d}.mp4" for s in tl["shots"]]
    if renderer == "pil":
        from .render_pil import render_shot
        for s, c in zip(tl["shots"], clips):
            render_shot(s, cfg, sprite_dir, c)
    elif renderer == "blender":
        from .render_blender import render_all
        render_all(tl, cfg, wd, sprite_dir, clips)
    else:
        raise ValueError(f"unknown renderer {renderer}")
    return clips


def stage_compose(tl, clips, workdir, cfg, name):
    wd = Path(workdir)
    W, H = video_size(cfg)
    (wd / "captions.ass").write_text(build_ass(tl, cfg, W, H), encoding="utf-8")
    compose.build_mix(tl, cfg, wd / "mix.wav")
    compose.join_video(clips, tl, cfg, wd / "joined.mp4")
    out = wd / f"{name}.mp4"
    captions_burned = compose.burn_and_mux(wd / "joined.mp4", wd / "mix.wav", wd / "captions.ass", out, tl["total_seconds"])
    v = compose.verify_output(out, W, H, tl["total_seconds"])
    v["captions_burned"] = captions_burned
    return out, v


def make(script_path, workdir, cfg, plan_path=None, name=None):
    t0 = time.time()
    name = name or Path(script_path).stem
    plan = stage_plan(script_path, workdir, plan_path)
    _log(f"plan: {len(plan['shots'])} shots, ~{plan['meta']['est_seconds']}s estimated")
    tl = stage_timeline(plan, workdir, cfg)
    _log(f"timeline: {tl['total_seconds']}s, voice={cfg['voice']['backend']}")
    clips = stage_render(tl, workdir, cfg)
    _log(f"rendered {len(clips)} clips with {cfg['render']['renderer']}")
    out, v = stage_compose(tl, clips, workdir, cfg, name)
    v["seconds_taken"] = round(time.time() - t0, 1)
    (Path(workdir) / "report.json").write_text(json.dumps(v, indent=2))
    _log(f"done: {out} {v}")
    if not v["ok"]:
        raise RuntimeError(f"output verification failed: {v}")
    return out, v
