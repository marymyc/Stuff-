"""Script -> everything the hybrid pipeline needs, with NO rendering:
public/plan.json (shots, camera, cast, zones), public/audio/words.json, voice.wav and mix.wav.

    python tools/make_hybrid_plan.py script.txt [--voice chatterbox|silent] [--ref-voice clip.wav] [--no-validate]

Reuses the repo's planner and voice code (package `stuff`, installed with `pip install -e ..` from the repo root).
"""
import argparse, json, math, os, re, subprocess, sys
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "src"))
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from stuff.align import build_timeline
from stuff.config import load_config
from stuff.planner import build_plan
from stuff.sfx import SR, render_track
from stuff.tts import synthesize_plan

FPS, W, H = 30, 1080, 1920
EXPR = {"neutral": "neutral", "angry": "stern", "rage": "furious", "happy": "grin", "shocked": "shock", "worried": "nervous", "smug": "smug"}
SPREAD = {"close": 0.3, "medium_low": 0.5, "medium": 0.8, "wide": 1.6}
OUTFIT = {"hero": "hero", "rival": "tycoon", "extra": "citizen"}
LIGHT = {"day": "day", "dawn": "golden", "dusk": "golden", "night": "night"}
GROUND_Y = {"canyon": 0.36}
# [distance, height, fov, focus height] - identical to src/scene/story.ts
SIZE = {"wide_aerial": (38, 16, 52, 1.0), "wide": (15, 2.4, 46, 1.3), "medium": (6.2, 1.15, 40, 1.15),
        "medium_low": (5.2, 0.8, 42, 1.35), "close": (3.1, 1.1, 34, 1.45), "macro": (1.8, 0.8, 30, 0.9)}
FOCUS = (1.15, 0.5, 30, 0.22)


def smoother(t):
    u = max(0.0, min(1.0, t))
    return u * u * u * (u * (u * 6 - 15) + 10)


def cam_at(s, f):
    gy = GROUND_Y.get(s["set"], 0)
    r, h0b, fov, fy0 = FOCUS if s.get("focus") else SIZE[s["size"]]
    h, fy = h0b + gy, fy0 + gy
    n = max(1, s["b"] - s["a"])
    u = smoother((f - s["a"]) / max(18, n * 0.8))
    creep = 1 - 0.0018 * max(0, f - s["a"] - n * 0.5)
    az0 = (1 if s["id"] % 2 else -1) * (0.12 if s["size"] == "close" else 0.3)
    r0 = r1 = r; h0 = h1 = h; a0 = a1 = az0; dx = lz = 0.0
    mv = s["move"]
    if mv == "fly_forward": r1, h1, lz = r * 0.42, h * 0.28, 5
    elif mv == "pull_back": r0, r1, h0, h1 = r * 0.6, r * 1.05, h * 0.7, h * 1.1
    elif mv == "orbit_slow": a0, a1 = az0 - 0.4, az0 + 0.4
    elif mv == "push_in": r1 = r * 0.62
    elif mv == "push_in_low": r1, h1 = r * 0.55, h * 0.5
    elif mv == "slide": dx = 1.6
    elif mv == "dutch_push": r1 = r * 0.6
    L = lambda a, b: a + (b - a) * u
    rad, hh, az = L(r0, r1) * creep, max(0.45 + gy, L(h0, h1)), L(a0, a1)
    look = [L(-dx, dx) if dx else 0.0, fy, -150 * s["zone"] - (L(0, lz) if lz else 0)]
    pos = [look[0] + math.sin(az) * rad, hh, look[2] + math.cos(az) * rad]
    return [round(v, 3) for v in pos], [round(v, 3) for v in look], fov


def map_chars(shot):
    size, kit = shot["shot_size"], shot["kit"]
    sp = SPREAD.get(size, 0.8)
    sc = 1.8 if size == "wide" else None
    out = []
    for c in shot.get("characters", []):
        role = c["role"]
        outfit = OUTFIT.get(role, "citizen")
        if role == "rival" and kit == "fortress": outfit = "commander"
        if role == "extra" and kit == "fortress": outfit = "soldier"
        x = {"left": -sp, "right": sp, "center": 0.0}.get(c["side"], 0.0)       # camera looks toward -z: screen-right is +x
        ch = {"outfit": outfit, "expr": EXPR.get(c["expression"], "neutral"), "x": x}
        if sc: ch["scale"] = sc
        out.append(ch)
        if role == "extra":
            for k, dx in enumerate((-1.4, 1.5, 0.2)):
                out.append({"outfit": outfit, "expr": "shock", "x": dx * (sp / 0.8 + 0.5), "z": 1.6 + 0.6 * k, **({"scale": sc} if sc else {})})
    act = shot.get("action")
    if act and out:
        pick = next((c for c in out if c["outfit"] in ("tycoon", "commander")), out[0]) if act == "point" else out[0]
        pick["action"] = act
    return out


def resample(x, sr):
    if sr == SR:
        return x
    g = gcd(sr, SR)
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


def make(script, voice="chatterbox", ref=None, validate=True):
    pub = os.path.join(ROOT, "public"); aud = os.path.join(pub, "audio")
    os.makedirs(aud, exist_ok=True)
    cfg = load_config(overrides={"voice": {"backend": voice, "reference_wav": ref}})
    text = open(script, encoding="utf-8").read()
    base = build_plan(text, os.path.splitext(os.path.basename(script))[0])
    tl = build_timeline(base, synthesize_plan(base, os.path.join(ROOT, "out", "voice_work"), cfg), cfg)
    shots, words, lines, zones = [], [], {}, {}
    for s in tl["shots"]:
        zones.setdefault(s["kit"], len(zones))
        a, b = round(s["start"] * FPS), round((s["start"] + s["duration"]) * FPS)
        st = {"id": s["id"] + 1, "a": a, "b": b, "set": s["kit"], "zone": zones[s["kit"]], "size": s["shot_size"], "move": s["camera_move"],
              "light": "interior" if s["kit"] == "interior" else LIGHT.get(s["tod"], "day"),
              "chars": map_chars(s), "props": s.get("props", []), "fx": ["burst" if f == "explosion" else f for f in s.get("fx", [])]}
        if s.get("focus"): st["focus"] = s["focus"]
        ps, pe, fv = cam_at(st, a), cam_at(st, b - 1), None
        st.update(camStart=ps[0], camEnd=pe[0], lookAt=ps[1], fov=ps[2], landFrames=[max(a + 1, b - 9), b])
        last = re.sub(r"[^a-z0-9']", "", s["words"][-1]["word"].lower()) if s["words"] else "end"
        st["punchWords"] = [last or "end"]
        shots.append(st)
        for w in s["words"]:
            ws, we = round(s["start"] + w["start"], 3), round(s["start"] + w["end"], 3)
            words.append({"w": w["word"], "s": ws, "e": we, "startMs": round(ws * 1000), "endMs": round(we * 1000), "line": f"s{st['id']}"})
        lines[f"s{st['id']}"] = {"s": round(s["start"], 3), "e": round(s["start"] + s["duration"], 3), "f0": a, "f1": b}
    # peak "meme" faces on the 1-3 strongest beats (the style budgets 1-4 of them)
    memes = 0
    for st in shots:
        for c in st["chars"]:
            if memes < 3 and c["expr"] in ("shock", "furious") and not c.get("z"):
                c["expr"] = "meme_shock" if c["expr"] == "shock" else "meme_fume"; memes += 1; break
    # the story turn shifts the light (day -> golden) when the script gave no time-of-day change
    if len({st["light"] for st in shots}) < 2 and len(shots) >= 6:
        for st in shots[int(len(shots) * 0.62):]:
            if st["light"] == "day": st["light"] = "golden"
    shots[-1]["b"] = total = round(tl["total_seconds"] * FPS)
    shots[-1]["landFrames"] = [max(shots[-1]["a"] + 1, total - 9), total]
    first_face = next((s["a"] / FPS for s in shots if s["chars"]), 0.0)
    roles = {}
    for s in shots:
        for c in s["chars"][:1] if False else s["chars"]:
            if c.get("z"): continue
            roles.setdefault(c["outfit"], []).append((s["a"], c["expr"], c.get("action") or "stand"))
    xs = {}
    for s_ in shots:
        for c in s_["chars"]:
            if not c.get("z"): xs.setdefault(c["outfit"], c["x"])
    used = []
    for role in list(xs):
        while any(abs(xs[role] - u) < 0.9 for u in used): xs[role] += 1.2
        used.append(xs[role])
    actors = [{"id": role, "firstFaceSec": round(first_face, 2), "pos": [round(xs.get(role, 0.0), 2), 0.0, 0.0], "radius": 0.35, "height": 1.95, "grounded": True,
               "poseTransitions": [{"frame": a, "expr": e, "mode": "sit" if m == "sit" else "stand", "note": m} for a, e, m in v], "blinkFrames": []}
              for role, v in roles.items()] or [{"id": "hero", "firstFaceSec": 0.0, "pos": [0, 0, 0], "radius": 0.35, "height": 1.95, "grounded": True, "poseTransitions": [], "blinkFrames": []}]
    first_sentence = re.split(r"(?<=[.!?])\s+", text.strip())[0]
    lights = [s["light"] for s in shots]
    plan = {"schemaVersion": 2, "title": " ".join(re.sub(r"[^A-Za-z0-9' ]", "", first_sentence).split()[:7]).title(),
            "description": (first_sentence + " " + "A short animated explainer.")[:200], "hashtags": ["#shorts", "#story", "#history", "#animation"],
            "fps": FPS, "width": W, "height": H, "totalFrames": total, "flashAt": shots[0]["b"] if len(shots) > 2 else -1,
            "voice": {"provider": "chatterbox", "model": "chatterbox-tts", "seed": cfg["voice"]["seed"]},
            "lightingChanges": sum(1 for x, y in zip(lights, lights[1:]) if x != y),
            "shots": shots, "actors": actors, "props": [],
            "flags": {"poseSnapNoIdleBounce": True, "staticBeatFaces": True, "noBlinkWhileSpeaking": True, "postGrainMax": 0.006, "noInkCards": True}}
    json.dump(plan, open(os.path.join(pub, "plan.json"), "w"), indent=1)
    json.dump({"voice": "chatterbox", "model": "chatterbox-tts", "durationSec": round(total / FPS, 3), "totalFrames": total, "lines": lines, "words": words},
              open(os.path.join(aud, "words.json"), "w"), indent=1)
    # audio: voice.wav (absolute placement) + procedural SFX -> mix.wav at -15 LUFS
    n = int(SR * total / FPS)
    voice_track = np.zeros(n + SR, dtype=np.float32)
    for s in tl["shots"]:
        x, sr = sf.read(s["voice_wav"], dtype="float32")
        x = resample(x.mean(axis=1) if x.ndim > 1 else x, sr)
        i = int((s["start"] + s["voice_offset"]) * SR)
        voice_track[i:i + len(x)] += x[: len(voice_track) - i]
    voice_track = voice_track[:n]
    sf.write(os.path.join(aud, "voice.wav"), voice_track, SR)
    ev = [(e["name"], s["start"] + e.get("at", 0.0), e.get("gain", 1.0)) for s in tl["shots"] for e in s.get("sfx", [])]
    raw = voice_track + render_track(ev, total / FPS, cfg["sfx"]["volume"])[:n]
    pk = float(np.max(np.abs(raw))) or 1.0
    sf.write(os.path.join(aud, "mix_raw.wav"), raw / pk * 0.89 if pk > 0.89 else raw, SR)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(aud, "mix_raw.wav"), "-af", "loudnorm=I=-15:TP=-1.2:LRA=11", "-ar", "48000",
                    os.path.join(aud, "mix.wav")], check=True)
    os.remove(os.path.join(aud, "mix_raw.wav"))
    print(f"plan: {len(shots)} shots, {len(zones)} zones {list(zones)}, {total} frames ({total / FPS:.1f}s), {len(words)} words")
    if validate:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "validate_plan.py"), os.path.join(pub, "plan.json"), os.path.join(aud, "words.json")],
                           capture_output=True, text=True, cwd=ROOT)
        print("validator (advisory, tuned for the original 12-shot style):\n" + "\n".join(r.stdout.strip().splitlines()[-8:]))
    return plan


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("--voice", default="chatterbox", choices=["chatterbox", "silent"])
    ap.add_argument("--ref-voice", dest="ref"); ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()
    make(os.path.abspath(a.script), a.voice, a.ref, not a.no_validate)
