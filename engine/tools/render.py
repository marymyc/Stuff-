"""Final render + mux + QA for one short.
Usage: python tools/render.py <name> [--scale 1.3333] [--skip-render]
  1. npx remotion render -> out/<name>/video.mp4   (2K vertical 1440x2560 at --scale 1.3333; ~4 fps, ~10 min for 67 s)
  2. mux projects/<name>/audio/mix.wav -> out/<name>/final.mp4  (Remotion writes a silent track: -map 0:v:0 -map 1:a:0)
  3. shots.json + frame-by-frame QA -> out/<name>/qa/  (black / white / frozen / pop frames, loudness, contact sheets)"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, check_name, comp_id, load_env, project_dir

load_env()
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
name = check_name(args[0])
scale = args[args.index("--scale") + 1] if "--scale" in args else "1.3333"
out = os.path.join(ROOT, "out", name)
os.makedirs(out, exist_ok=True)
video, final = os.path.join(out, "video.mp4"), os.path.join(out, "final.mp4")
mix = os.path.join(project_dir(name), "audio", "mix.wav")
env = dict(os.environ)
tmp = os.path.abspath(env.get("REMOTION_TMP", os.path.join(ROOT, "remotion-tmp")))
os.makedirs(tmp, exist_ok=True)
env["TEMP"] = env["TMP"] = env["TMPDIR"] = tmp
sh = os.name == "nt"


def run(cmd):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT, env=env, shell=sh)


if "--skip-render" not in args:
    cmd = ["npx", "remotion", "render", "src/index.ts", comp_id(name), video, "--codec", "h264", "--crf", "16",
           "--scale", scale, f"--gl={env.get('REMOTION_GL', 'angle')}"]
    if env.get("CHROME_PATH"):
        cmd += ["--browser-executable", env["CHROME_PATH"]]
    run(cmd)
if not os.path.exists(mix):
    sys.exit(f"no {mix}: run the sound pipeline first (python projects/{name}/audio/mix.py)")
run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", mix, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", final])
run([sys.executable, "tools/shots.py", name])
run([sys.executable, "tools/short_qa.py", final, os.path.join(out, "qa"), os.path.join(out, "shots.json")])
print("\nDONE ->", final, "\nRead the QA output above; fix every flagged frame, then re-run.")
