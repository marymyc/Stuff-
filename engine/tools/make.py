"""One command: script -> final MP4 with the new engine.

    python tools/make.py script.txt --name demo [--voice chatterbox|silent] [--ref-voice clip.wav] [--scale 1] [--gl egl|angle|swangle]

plan (shots, camera, cast) -> voice (Chatterbox) -> SFX + mix -> Remotion/three.js render -> mux.  Needs a GPU for speed
(software GL takes minutes per frame); run `tools/gpu_probe.py` first.
"""
import argparse, json, os, subprocess, sys
from math import gcd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from stuff.sfx import SR, render_track
from make_plan import make


def mix(plan, out_wav, volume=0.45):
    total = plan["total"] / plan["fps"]
    voice = np.zeros(int(SR * total) + SR, dtype=np.float32)
    for wav, start in zip(plan["voice"]["wavs"], plan["voice"]["starts"]):
        x, sr = sf.read(wav, dtype="float32")
        x = x.mean(axis=1) if x.ndim > 1 else x
        if sr != SR:
            g = gcd(sr, SR); x = resample_poly(x, SR // g, sr // g).astype(np.float32)
        i = int(start * SR); voice[i:i + len(x)] += x[: len(voice) - i]
    m = voice[: int(SR * total)] + render_track([tuple(e) for e in plan["sfx"]], total, volume)[: int(SR * total)]
    pk = float(np.max(np.abs(m))) or 1.0
    sf.write(out_wav, m / pk * 0.89 if pk > 0.89 else m, SR)


def run(cmd, env=None):
    print(">", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("--name", default="short")
    ap.add_argument("--voice", default="chatterbox", choices=["chatterbox", "silent"]); ap.add_argument("--ref-voice")
    ap.add_argument("--scale", default="1"); ap.add_argument("--gl", default=os.environ.get("REMOTION_GL", "angle"))
    ap.add_argument("--frames", help="e.g. 0-90 to render only a range (preview)")
    a = ap.parse_args()
    out = os.path.join(ROOT, "out", a.name); os.makedirs(out, exist_ok=True)
    plan_path = os.path.join(out, "plan.json")
    plan = make(os.path.abspath(a.script), plan_path, a.voice, a.ref_voice)
    print(f"plan: {len(plan['shots'])} shots, {plan['total'] / plan['fps']:.1f}s")
    wav = os.path.join(out, "mix.wav"); mix(plan, wav)
    env = dict(os.environ); tmp = os.path.abspath(env.get("REMOTION_TMP", os.path.join(ROOT, "remotion-tmp"))); os.makedirs(tmp, exist_ok=True)
    env["TEMP"] = env["TMP"] = env["TMPDIR"] = tmp
    video, final = os.path.join(out, "video.mp4"), os.path.join(out, "final.mp4")
    cmd = ["npx", "remotion", "render", "src/index.ts", "Short", video, f"--props={plan_path}", "--codec", "h264", "--crf", "16",
           "--scale", a.scale, f"--gl={a.gl}"] + ([f"--frames={a.frames}"] if a.frames else [])
    if env.get("CHROME_PATH"): cmd += ["--browser-executable", env["CHROME_PATH"]]
    run(cmd, env)
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", wav, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
         "-ar", "48000", "-shortest", "-movflags", "+faststart", final])
    print("DONE ->", final)
