"""NO-RENDER check: builds every set, prop and insert object of scripts/blender_scene.py in Blender (bpy) and flips visibility per frame.
Catches API errors early. Never calls render. Needs `pip install bpy==4.2.0` (Python 3.11) or run inside Blender."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import bpy
import blender_scene as bs

SETS = ["field", "fortress", "canyon", "interior", "town"]
FOCUS = ["coin", "paper", "calendar", "newspaper", "caliper", "thermometer", "moneybag", "map", "clock", "marble"]
PROPS = ["cart", "crate", "barrel", "table", "lamp", "umbrella", "tree"]

shots, a = [], 0
for i, st in enumerate(SETS):
    for k in range(2):
        shots.append({"id": len(shots) + 1, "a": a, "b": a + 30, "set": st, "zone": i, "props": PROPS if k == 0 else [], "focus": FOCUS[(i * 2 + k) % len(FOCUS)] if k == 1 else None})
        a += 30
plan = {"shots": shots}
cam, target = bpy.data.objects.new("cam", None), bpy.data.objects.new("target", None)
state = bs.build_scene(plan, "", cam, target, {})
assert len(state["zones"]) == len(SETS), state["zones"]
# every focus object must exist as geometry
for name in FOCUS:
    s = {"id": 100, "a": 0, "b": 1, "set": "canyon", "zone": 0, "props": [], "focus": name}
    col = bpy.data.collections.new(f"probe_{name}")
    bs.build_focus(col, 0.0, 0.0, name)
    assert len(col.objects) >= 1, f"focus object {name} built nothing"
for fr in (0, 31, 62, 95, 140, 199, 280):
    bs.update_frame(fr, bpy.context.scene, cam, target, state)
    cur = next(s for s in shots if s["a"] <= fr < s["b"])
    visible = [zi for zi, c in state["zones"].items() if not c.hide_render]
    assert visible == [cur["zone"]], (fr, visible, cur["zone"])
n_obj = len(bpy.data.objects)
n_mat = len(bpy.data.materials)
print(json.dumps({"ok": True, "zones": len(state["zones"]), "shot_collections": len(state["shot_cols"]), "objects": n_obj, "materials": n_mat,
                  "blender": bpy.app.version_string}))
