"""Copy the Kenney GLB props the world needs into public/bridge/kenney/.
Usage: python tools/import_kenney.py <folder containing the unzipped Kenney Nature Kit / Fantasy Town Kit>"""
import os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT

if len(sys.argv) < 2:
    sys.exit(__doc__)
src = sys.argv[1]
world = open(os.path.join(ROOT, "src/videos/bridge/world.ts"), encoding="utf-8").read()
names = re.findall(r'"([^"]+)"', re.search(r"const KENNEY = \[(.*?)\];", world, re.S).group(1))
found = {}
for d, _, files in os.walk(src):
    for f in files:
        if f.lower().endswith(".glb"):
            found.setdefault(f[:-4], os.path.join(d, f))
dst = os.path.join(ROOT, "public/bridge/kenney")
os.makedirs(dst, exist_ok=True)
miss = []
for n in names:
    if n in found:
        shutil.copy2(found[n], os.path.join(dst, n + ".glb"))
        print("copied", n)
    else:
        miss.append(n)
print(f"\n{len(names) - len(miss)}/{len(names)} props copied." + (f" Missing: {', '.join(miss)}" if miss else ""))
