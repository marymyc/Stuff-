from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import pipeline
from .config import load_config


def _cfg(a):
    ov = {"voice": {}, "render": {}, "align": {}}
    if getattr(a, "voice", None):
        ov["voice"]["backend"] = a.voice
    if getattr(a, "ref_voice", None):
        ov["voice"]["reference_wav"] = a.ref_voice
    if getattr(a, "renderer", None):
        ov["render"]["renderer"] = a.renderer
    if getattr(a, "scale", None):
        ov["render"]["scale"] = a.scale
    if getattr(a, "fps", None):
        ov["render"]["fps"] = a.fps
    if getattr(a, "engine", None):
        ov["render"]["engine"] = a.engine
    if getattr(a, "samples", None):
        ov["render"]["samples"] = a.samples
    if getattr(a, "align", None):
        ov["align"]["backend"] = a.align
    return load_config(a.config, ov)


def main(argv=None):
    p = argparse.ArgumentParser(prog="stuff", description="Script in, 9:16 educational video out.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, script=True):
        if script:
            sp.add_argument("script")
        sp.add_argument("--workdir", default=None)
        sp.add_argument("--config", default=None)
        sp.add_argument("--voice", choices=["chatterbox", "silent"])
        sp.add_argument("--ref-voice", dest="ref_voice")
        sp.add_argument("--renderer", choices=["blender", "pil"])
        sp.add_argument("--engine", choices=["CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"])
        sp.add_argument("--samples", type=int)
        sp.add_argument("--scale", type=float)
        sp.add_argument("--fps", type=int)
        sp.add_argument("--align", choices=["proportional", "whisper"])
        sp.add_argument("--plan", default=None, help="use an existing/edited plan.json instead of auto-planning")

    sp = sub.add_parser("plan", help="split script into shots")
    common(sp)
    sp = sub.add_parser("make", help="full pipeline: script -> final MP4")
    common(sp)
    sp.add_argument("--name", default=None)
    sp = sub.add_parser("preflight", help="check risky stages before a long render")
    sp.add_argument("--mode", choices=["light", "blender", "voice", "all"], default="light")
    sp.add_argument("--out", default="reports")
    sp.add_argument("--config", default=None)
    a = p.parse_args(argv)

    if a.cmd == "preflight":
        from .preflight import run_preflight
        return run_preflight(a.mode, a.out, load_config(a.config))
    wd = a.workdir or f"work/{Path(a.script).stem}"
    cfg = _cfg(a)
    if a.cmd == "plan":
        plan = pipeline.stage_plan(a.script, wd, a.plan)
        print(json.dumps(plan["meta"]))
        return 0
    pipeline.make(a.script, wd, cfg, a.plan, a.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
