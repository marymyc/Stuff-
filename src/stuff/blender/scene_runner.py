"""Runs inside Blender. Usage: `blender -b -P scene_runner.py -- job.json` or `import bpy; scene_runner.run(job)`."""
import json
import math
import os
import random
import sys

import bpy

try:
    from . import kits
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import kits

TOD = {
    "day": dict(top=(0.16, 0.42, 0.95), hor=(0.75, 0.88, 1.0), sun=4.0, col=(1, 0.96, 0.88), elev=55, az=40, amb=1.0),
    "dawn": dict(top=(0.35, 0.4, 0.75), hor=(1.0, 0.72, 0.5), sun=3.0, col=(1, 0.7, 0.45), elev=10, az=120, amb=0.8),
    "dusk": dict(top=(0.28, 0.22, 0.55), hor=(1.0, 0.55, 0.35), sun=2.5, col=(1, 0.55, 0.35), elev=7, az=250, amb=0.7),
    "night": dict(top=(0.02, 0.03, 0.12), hor=(0.08, 0.1, 0.25), sun=0.35, col=(0.5, 0.6, 1.0), elev=35, az=40, amb=0.25),
}
BASE = {  # radius, height, azimuth, vertical fov (deg)
    "wide_aerial": (38, 16, 0.5, 70), "wide": (14, 2.5, 0.4, 62), "medium": (6.5, 1.1, 0.3, 55),
    "medium_low": (5.5, 0.35, 0.2, 60), "close": (3.6, 0.9, 0.15, 48), "macro": (1.9, 0.15, 0.2, 45),
}
SPRITE_ASPECT = 600 / 1100


def set_world(scene, tod):
    t = TOD.get(tod, TOD["day"])
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mp = nt.nodes.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value, mp.inputs["From Max"].default_value = 0.0, 0.8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*t["hor"], 1)
    ramp.color_ramp.elements[1].color = (*t["top"], 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mp.inputs["Value"])
    nt.links.new(mp.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = t["amb"]
    scene.world = w
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy, sun.color = t["sun"], t["col"]
    ob = bpy.data.objects.new("sun", sun)
    ob.rotation_euler = (math.radians(90 - t["elev"]), 0, math.radians(t["az"]))
    kits.link(ob)
    if tod == "night":
        for x in (-4, 4):
            L = bpy.data.lights.new("lamp", "POINT")
            L.energy, L.color = 900, (1, 0.7, 0.4)
            lo = bpy.data.objects.new("lamp", L)
            lo.location = (x, 1.5, 2.2)
            kits.link(lo)


def sprite_material(path):
    m = bpy.data.materials.new(os.path.basename(path))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def add_sprite(path, pos, cam, height=1.85, scale=1.0):
    h = height * scale
    me = bpy.data.meshes.new("sprite")
    me.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UV")
    for i, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = (u, v)
    ob = bpy.data.objects.new("char", me)
    ob.data.materials.append(sprite_material(path))
    ob.location = (pos[0], pos[1], pos[2] + h / 2)
    ob.scale = (h * SPRITE_ASPECT, h, 1)
    c = ob.constraints.new("COPY_ROTATION")
    c.target = cam
    kits.link(ob)
    blob = kits.Geo()
    blob.cone((pos[0], pos[1], pos[2] + 0.01), 0.7 * scale, 0.7 * scale, 0.01, 16)
    bo = blob.build("blob", None)
    m = bpy.data.materials.new("blob")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Alpha"].default_value = 0.35
    bo.data.materials.append(m)
    bo.scale = (1, 0.45, 1)
    return ob


def camera_plan(shot, focus, rng):
    r, h, a, fov = BASE[shot["shot_size"]]
    a = a * rng.choice([-1, 1])
    fx, fy, fz = focus

    def pos(rad, hh, az):
        return (fx + math.sin(az) * rad, fy - math.cos(az) * rad, fz + hh)

    mv = shot["camera_move"]
    s, e = pos(r, h, a), pos(r, h, a)
    fs, fe, fov_e, roll_e = focus, focus, fov, 0.0
    if mv == "fly_forward":
        s, e, fe = pos(r, h, a), pos(r * 0.45, h * 0.35, a), (fx, fy + 6, fz)
    elif mv == "pull_back":
        s, e = pos(r * 0.55, h * 0.6, a), pos(r * 1.1, h * 1.1, a)
    elif mv == "orbit_slow":
        s, e = pos(r, h, a - 0.35), pos(r, h, a + 0.35)
    elif mv == "push_in":
        s, e = pos(r, h, a), pos(r * 0.6, h, a)
    elif mv == "push_in_low":
        s, e = pos(r, h, a), pos(r * 0.55, h * 0.5, a)
    elif mv == "slide":
        s, e = pos(r, h, a), pos(r, h, a)
        s = (s[0] - 0.9, s[1], s[2])
        e = (e[0] + 0.9, e[1], e[2])
        fs, fe = (fx - 0.9, fy, fz), (fx + 0.9, fy, fz)
    elif mv == "dutch_push":
        s, e, roll_e = pos(r, h, a), pos(r * 0.6, h, a), 0.22
    return dict(s=s, e=e, fs=fs, fe=fe, fov_s=fov, fov_e=fov_e, roll_e=roll_e)


def add_camera(scene, shot, focus, rng, frames):
    cp = camera_plan(shot, focus, rng)
    target = bpy.data.objects.new("focus", None)
    kits.link(target)
    rig = bpy.data.objects.new("rig", None)
    kits.link(rig)
    con = rig.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cd.clip_end = 400
    cam = bpy.data.objects.new("cam", cd)
    cam.parent = rig
    kits.link(cam)
    scene.camera = cam
    for f, key in ((1, "s"), (frames, "e")):
        rig.location = cp[key]
        rig.keyframe_insert("location", frame=f)
        target.location = cp["fs" if key == "s" else "fe"]
        target.keyframe_insert("location", frame=f)
        fov = math.radians(cp["fov_s" if key == "s" else "fov_e"])
        cd.lens = (cd.sensor_height / 2.0) / math.tan(fov / 2.0)   # vertical FOV via lens ('angle' is not animatable)
        cd.keyframe_insert("lens", frame=f)
        cam.rotation_euler = (0, 0, 0 if key == "s" else cp["roll_e"])
        cam.keyframe_insert("rotation_euler", frame=f)
    return cam


def setup_render(scene, job, out_dir, frames):
    r = scene.render
    r.engine = job.get("engine", "CYCLES")
    r.resolution_x, r.resolution_y, r.resolution_percentage = job["width"], job["height"], 100
    r.fps = job["fps"]
    r.image_settings.file_format = "PNG"
    r.filepath = os.path.join(out_dir, "f_")
    scene.frame_start, scene.frame_end = 1, frames
    scene.view_settings.view_transform = "Standard"
    if r.engine == "CYCLES":
        scene.cycles.samples = int(job.get("samples", 24))
        scene.cycles.use_denoising = bool(job.get("denoise", True))
        scene.cycles.device = "CPU"
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for t in ("OPTIX", "CUDA", "HIP", "METAL"):
                prefs.compute_device_type = t
                prefs.get_devices()
                devs = [d for d in prefs.devices if d.type == t]
                if devs:
                    for d in prefs.devices:
                        d.use = d.type == t
                    scene.cycles.device = "GPU"
                    break
        except Exception:
            pass


def build_shot(shot, job, out_dir, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rng = random.Random(shot.get("seed", shot["id"]) * 7919 + 13)
    tod = shot.get("tod", "day")
    info = kits.KITS.get(shot["kit"], kits.KITS["field"])(scene, rng, tod)
    set_world(scene, tod)
    cam = add_camera(scene, shot, info["focus"], rng, frames)
    xs = {"left": -0.9, "right": 0.9, "center": 0.0}
    chars = shot.get("characters", [])
    for i, c in enumerate(chars):
        path = os.path.join(job["sprite_dir"], f"{c['role']}_{c['expression']}.png")
        add_sprite(path, (xs.get(c["side"], 0) * (1.0 + 0.2 * (len(chars) > 1)), 0.8 * (c["side"] == "center"), 0), cam)
    for j, p in enumerate(shot.get("props", [])):
        kits.add_prop(p, (-3.0 + 2.0 * j, 3.0, 0))
    if "explosion" in shot.get("fx", []):
        kits.fx_explosion((0, 6, 0), frames)
    setup_render(scene, job, out_dir, frames)
    return scene


def run(job):
    done = []
    for shot in job["shots"]:
        frames = int(shot.get("frames_override") or max(2, round(shot["render_seconds"] * job["fps"])))
        out_dir = os.path.join(job["out_dir"], f"shot_{shot['id']:03d}")
        os.makedirs(out_dir, exist_ok=True)
        build_shot(shot, job, out_dir, frames)
        bpy.ops.render.render(animation=True)
        done.append({"id": shot["id"], "dir": out_dir, "frames": frames})
    with open(os.path.join(job["out_dir"], "done.json"), "w") as f:
        json.dump(done, f)
    return done


if __name__ == "__main__":
    jp = sys.argv[sys.argv.index("--") + 1]
    run(json.load(open(jp)))
