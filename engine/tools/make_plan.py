"""Script -> engine plan.json (the single file that drives src/engine/Short.tsx).

    python tools/make_plan.py script.txt --out plan.json [--voice silent|chatterbox] [--ref-voice clip.wav]

Reuses the repo's planner (shots, sizes, camera moves, expressions, sfx) and voice/timeline code (package `stuff`,
installed with `pip install -e ..` from the repo root), then maps everything to frames and engine vocabulary.
"""
import argparse, json, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "src"))
from stuff.align import build_timeline
from stuff.config import load_config
from stuff.planner import build_plan
from stuff.tts import synthesize_plan

LIGHT = {"day": "day", "dawn": "golden", "dusk": "golden", "night": "golden"}
EXPR = {"neutral": "neutral", "angry": "stern", "rage": "stern", "happy": "grin", "shocked": "shock", "worried": "nervous", "smug": "smile_closed"}
SPREAD = {"close": 0.3, "medium_low": 0.5, "medium": 0.8, "wide": 1.6}
SCALE = {"wide": 1.8}
OUTFIT = {"hero": "hero", "rival": "tycoon", "extra": "citizen"}


def map_chars(shot, fps):
    size, kit = shot["shot_size"], shot["kit"]
    sp, sc = SPREAD.get(size, 0.8), SCALE.get(size)
    out = []
    for c in shot.get("characters", []):
        role = c["role"]
        outfit = OUTFIT.get(role, "citizen")
        if role == "rival" and kit == "fortress":
            outfit = "commander"
        if role == "extra" and kit == "fortress":
            outfit = "soldier"
        x = {"left": sp, "right": -sp, "center": 0.0}.get(c["side"], 0.0)   # camera looks toward +z: screen-left is +x
        ch = {"outfit": outfit, "expr": EXPR.get(c["expression"], "neutral"), "x": x}
        if sc:
            ch["scale"] = sc
        out.append(ch)
        if role == "extra":  # a small crowd behind the lead
            for k, dx in enumerate((-1.4, 1.5, 0.2)):
                out.append({"outfit": outfit, "expr": "shock", "x": dx * (sp / 0.8 + 0.5), "z": 1.6 + 0.6 * k, **({"scale": sc} if sc else {})})
    return out


def make(script, out_path, voice="chatterbox", ref=None, fps=30):
    cfg = load_config(overrides={"voice": {"backend": voice, "reference_wav": ref}})
    plan = build_plan(open(script, encoding="utf-8").read(), os.path.splitext(os.path.basename(script))[0])
    wd = os.path.join(os.path.dirname(os.path.abspath(out_path)) or ".", "voice_work")
    os.makedirs(wd, exist_ok=True)
    tl = build_timeline(plan, synthesize_plan(plan, wd, cfg), cfg)
    shots, words = [], []
    for s in tl["shots"]:
        a = round(s["start"] * fps)
        b = round((s["start"] + s["duration"]) * fps)
        shots.append({
            "id": s["id"] + 1, "a": a, "b": b, "set": s["kit"], "light": LIGHT.get(s["tod"], "day"),
            "size": s["shot_size"], "move": s["camera_move"], "chars": map_chars(s, fps),
            "props": s.get("props", []), "fx": ["burst" if f == "explosion" else f for f in s.get("fx", [])],
            **({"xfade": 8} if s["transition"] == "dissolve" and s["id"] > 0 else {}),
        })
        for w in s["words"]:
            words.append({"w": w["word"], "s": round(s["start"] + w["start"], 3), "e": round(s["start"] + w["end"], 3)})
    shots[-1]["b"] = round(tl["total_seconds"] * fps)
    total = shots[-1]["b"]
    out = {"fps": fps, "total": total, "flashAt": shots[0]["b"] if len(shots) > 2 else None, "captions": True, "shots": shots, "words": words,
           "voice": {"wavs": [s["voice_wav"] for s in tl["shots"]], "starts": [s["start"] + s["voice_offset"] for s in tl["shots"]]},
           "sfx": [[e["name"], round(s["start"] + e.get("at", 0.0), 3), e.get("gain", 1.0)] for s in tl["shots"] for e in s.get("sfx", [])]}
    json.dump(out, open(out_path, "w"), indent=1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("--out", default="plan.json")
    ap.add_argument("--voice", default="chatterbox", choices=["chatterbox", "silent"]); ap.add_argument("--ref-voice", dest="ref")
    a = ap.parse_args()
    r = make(a.script, a.out, a.voice, a.ref)
    print(f"plan: {len(r['shots'])} shots, {r['total']} frames ({r['total'] / r['fps']:.1f}s), {len(r['words'])} words -> {a.out}")
