"""Look-match sandboxes: one copy of a short per owner, so parallel agents (or passes) never edit the same file.
Usage:
  python tools/sandbox.py make  <name> [cam,world,mat,char,post]   create/refresh src/videos/<name>_<box> + entries
  python tools/sandbox.py merge <name> [cam,world,mat,char,post]   back up main, copy each box's OWNED files to main
  python tools/sandbox.py sync  <name>                             re-copy main into every sandbox (after a merge)
Render a sandbox: ENTRY=src/sandboxes/<name>_<box>/index.tsx node tools/stills.mjs <CompId> out/<name>/<box>/x_ 100,400"""
import filecmp, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, check_name, comp_id, video_dir

OWN = {
    "cam": ["story.ts"],
    "world": ["world.ts", "lights.ts", "shade.ts", "grade.ts"],
    "mat": ["paint.ts", "build.ts"],
    "char": ["toon.ts", "cast.ts", "cardshade.ts"],
    "post": ["ink.ts", "Bridge.tsx", "lensblur.ts"],
}
if len(sys.argv) < 3:
    sys.exit(__doc__)
cmd, name = sys.argv[1], check_name(sys.argv[2])
boxes = sys.argv[3].split(",") if len(sys.argv) > 3 else list(OWN)
main = video_dir(name)
cid = comp_id(name)

if cmd in ("make", "sync"):
    for b in boxes:
        d = f"{main}_{b}"
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(main, d)
        e = os.path.join(ROOT, "src", "sandboxes", f"{name}_{b}")
        os.makedirs(e, exist_ok=True)
        open(os.path.join(e, "index.tsx"), "w", encoding="utf-8").write(
            f'// sandbox "{b}" of {name}: owns {", ".join(OWN[b])}\n'
            'import React from "react";\nimport { Composition, registerRoot } from "remotion";\n'
            f'import {{ BridgeShort, BRIDGE_FRAMES }} from "../../videos/{name}_{b}/Bridge";\n\n'
            f'const Root: React.FC = () => <Composition id="{cid}" component={{BridgeShort}} durationInFrames={{BRIDGE_FRAMES}} '
            'fps={30} width={1080} height={1920} />;\nregisterRoot(Root);\n')
        print(f"{cmd}: src/videos/{name}_{b}  (entry src/sandboxes/{name}_{b}/index.tsx)")
elif cmd == "merge":
    bak = os.path.join(ROOT, "backup", time.strftime(f"{name}_%Y%m%d_%H%M%S"))
    shutil.copytree(main, bak)
    print("backup ->", bak)
    for b in boxes:
        for f in OWN[b]:
            a, m = os.path.join(f"{main}_{b}", f), os.path.join(main, f)
            if not os.path.exists(a):
                print(f"  {b}: {f} missing in sandbox (skipped)")
            elif os.path.exists(m) and filecmp.cmp(a, m, shallow=False):
                print(f"  {b}: {f} unchanged")
            else:
                shutil.copy2(a, m)
                print(f"  {b}: {f} -> main")
    print("next: npx tsc --noEmit, then python tools/sandbox.py sync", name)
else:
    sys.exit(__doc__)
