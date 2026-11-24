"""Write out/<name>/shots.json (shot ranges, crossfades, flash, planned cuts and kicks) from story.ts, for short_qa.py.
Usage: python tools/shots.py <name>"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, check_name, video_dir

if len(sys.argv) < 2:
    sys.exit(__doc__)
name = check_name(sys.argv[1])
src = open(os.path.join(video_dir(name), "story.ts"), encoding="utf-8").read()
fps = int(re.search(r"FPS = (\d+)", src).group(1)) if re.search(r"FPS = (\d+)", src) else 30
total = int(re.search(r"TOTAL = (\d+)", src).group(1))
shots = [{"id": int(i), "a": int(a), "b": int(b) if b != "TOTAL" else total}
         for i, a, b in re.findall(r"\{ id: (\d+), a: (\d+), b: (\w+),", src)]
m = re.search(r"XFADE[^=]*= \{([^}]*)\}", src)
xf = {int(k): int(v) for k, v in re.findall(r"(\d+): (\d+)", m.group(1))} if m else {}
fm = re.search(r"FLASH_AT = (\d+)", src)
xfade = [[s["a"] - xf[s["id"]] // 2, s["a"] + xf[s["id"]] // 2] for s in shots if s["id"] in xf]
cuts = [[int(f), int(f)] for f in re.findall(r"\{ f: (\d+), cut: true", src)]
consts = {k: float(v) for k, v in re.findall(r"\b([A-Z][A-Z0-9_]*) = ([\d.]+)\b", src)}
kicks = []
km = re.search(r"const KICKS[^=]*= \[(.*?)\];", src, re.S)
if km:
    for t0, _ in re.findall(r"\[([\w.]+), ([\d.]+)\]", km.group(1)):
        try:
            f0 = round((consts[t0] if t0 in consts else float(t0)) * fps)
            kicks.append([f0, f0 + 8])
        except ValueError:
            print("  (skipped kick with non-numeric time:", t0, ")")
meta = {"shots": shots, "xfade": xfade, "planned": cuts + kicks}
if fm:
    meta["flash"] = [int(fm.group(1)), int(fm.group(1)) + 4]
os.makedirs(os.path.join(ROOT, "out", name), exist_ok=True)
p = os.path.join(ROOT, "out", name, "shots.json")
json.dump(meta, open(p, "w"), indent=1)
print(len(shots), "shots ->", p)
