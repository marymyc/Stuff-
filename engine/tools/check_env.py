"""Check that everything the pipeline needs is installed. Usage: python tools/check_env.py"""
import importlib, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, load_env

load_env()
ok = True
PIP = "pip install -r requirements.txt"
NPM = "run: npm install"


def row(state, name, note=""):
    global ok
    mark = {"ok": "[ OK ]", "warn": "[WARN]", "fail": "[FAIL]"}[state]
    if state == "fail":
        ok = False
    print(f"{mark} {name}" + (f"  - {note}" if note else ""))


def ver(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
    except Exception:
        return ""


for exe in ("node", "npx", "ffmpeg", "ffprobe"):
    p = shutil.which(exe)
    row("ok" if p else "fail", exe, ver([exe, "-version" if exe.startswith("ff") else "--version"]) if p else "not found on PATH")

row("ok" if sys.version_info >= (3, 9) else "fail", "python", sys.version.split()[0])
for mod, need, hint in (("numpy", True, PIP), ("scipy", True, PIP), ("PIL", True, PIP),
                        ("requests", False, "needed for ElevenLabs/OpenAI voice"),
                        ("faster_whisper", False, "needed for automatic word timings (or openai-whisper)"),
                        ("kokoro", False, "only for the free local voice engine")):
    try:
        importlib.import_module(mod)
        row("ok", f"python: {mod}")
    except Exception:
        row("fail" if need else "warn", f"python: {mod}", hint)

nm = os.path.join(ROOT, "node_modules")
for pkg in ("remotion", "@remotion/three", "@remotion/renderer", "three", "@react-three/fiber", "postprocessing", "@react-three/postprocessing"):
    have = os.path.isdir(os.path.join(nm, pkg))
    row("ok" if have else "fail", f"npm: {pkg}", "" if have else NPM)

world = open(os.path.join(ROOT, "src/videos/bridge/world.ts"), encoding="utf-8").read()
names = re.findall(r'"([^"]+)"', re.search(r"const KENNEY = \[(.*?)\];", world, re.S).group(1))
have = [n for n in names if os.path.exists(os.path.join(ROOT, "public/bridge/kenney", n + ".glb"))]
row("ok" if len(have) == len(names) else "warn", f"Kenney props {len(have)}/{len(names)}",
    "" if len(have) == len(names) else "see public/bridge/kenney/README.md (renders still work, town is emptier)")

eng = os.environ.get("TTS_ENGINE", "elevenlabs")
key = {"elevenlabs": "ELEVENLABS_API_KEY", "openai": "OPENAI_API_KEY"}.get(eng)
row("ok" if (not key or os.environ.get(key)) else "warn", f"voice engine: {eng}",
    f"{key} missing in .env" if key and not os.environ.get(key) else "")

print("\nREADY" if ok else "\nNOT READY: fix the [FAIL] lines first")
sys.exit(0 if ok else 1)
