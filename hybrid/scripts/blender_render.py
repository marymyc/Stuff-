#!/usr/bin/env python3
"""
Blender 5.2 Stage-2 GPU Final Renderer for ricks-clips-animation v2.
Builds PBR 3D worlds from plan.json (plus optional --scene-module custom sets) with:
  - Physical sky (ShaderNodeTexSky SINGLE_SCATTERING) + dynamic per-shot light presets
  - Soft raytraced shadows + directional fill + compositor Fog Glow + thin-lens DOF
  - Manifest-driven transparent 2D cartoon sprite PNG cards (--cards out/cards)
  - Fast JPEG_95 (~0.38s/frame at 1080x1920 EEVEE) or lossless PNG frame output

Usage:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python-exit-code 1 -P scripts/blender_render.py -- ^
      --plan public/plan.json --cards out/cards --out out/blender_frames --engine EEVEE --smoke
"""
import argparse
import importlib.util
import json
import math
import os
import random
import sys
import bpy
from mathutils import Euler, Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="Render Stage-2 Blender 5.2 frames from plan.json")
    ap.add_argument("--plan", default="public/plan.json")
    ap.add_argument("--cards", default="", help="Dir containing manifest.json + transparent card PNGs")
    ap.add_argument("--scene-module", default="", help="Optional Python module defining build_scene/update_frame (auto-loads scripts/blender_scene.py if present)")
    ap.add_argument("--no-scene-module", action="store_true", help="Disable auto-loading scripts/blender_scene.py")
    ap.add_argument("--ink", action="store_true", help="Enable optional 3D world Inverted-Hull outlines (off by default to match clean @RicksClips3000 PBR 3D worlds)")
    ap.add_argument("--ink-radius", type=float, default=0.011, help="3D Inverted-Hull ink offset in meters when --ink is set")
    ap.add_argument("--out", default="out/blender_frames")
    ap.add_argument("--engine", default="EEVEE", choices=["EEVEE", "CYCLES"])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--format", default="JPEG", choices=["JPEG", "PNG"])
    ap.add_argument("--no-rt", action="store_true", help="Disable EEVEE screen-space raytracing for ~1.5-2x speed")
    ap.add_argument("--volumetrics", action="store_true", help="Enable Principled Volume domain")
    ap.add_argument("--frame", type=int, default=-1, help="Render single frame index")
    ap.add_argument("--frames", default="", help="Optional range start-end inclusive")
    ap.add_argument("--frames-list", default="", help="Comma-separated frame indices (e.g. 0,240,600,1400)")
    ap.add_argument("--smoke", action="store_true", help="Render frame 0 fast")
    return ap.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def srgb_hex(hex_str: str) -> tuple[float, float, float, float]:
    """Convert #RRGGBB sRGB hex string to Blender linear RGBA."""
    h = hex_str.lstrip("#")
    vals = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        lin = c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        vals.append(lin)
    return (vals[0], vals[1], vals[2], 1.0)


def make_mat(name: str, color: tuple[float, float, float, float], roughness=0.68, metallic=0.0, bump_scale=0.0, bump_strength=0.25):
    m = bpy.data.materials.new(name=name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if bump_scale > 0.0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def make_emissive_mat(name: str, color: tuple[float, float, float, float], strength=6.0):
    m = bpy.data.materials.new(name=name)
    if m.node_tree is None:
        m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def make_image_mat(name: str, img_path: str, roughness=0.55, emit_strength=0.0):
    m = bpy.data.materials.new(name=name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.extension = "EXTEND"
    tex.image = bpy.data.images.load(os.path.abspath(img_path), check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if emit_strength > 0.0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


def plan_to_blender(pt: list[float]) -> Vector:
    """Convert Three.js/plan [x, y_up, z_to_cam] to Blender [x, -z, y_up]."""
    return Vector((float(pt[0]), -float(pt[2]), float(pt[1])))


def add_box(name: str, aabb: list[float], mat, bevel_width=0.04):
    cx = (aabb[0] + aabb[3]) * 0.5
    cy = (aabb[2] + aabb[5]) * 0.5
    cz = (aabb[1] + aabb[4]) * 0.5
    sx = max(0.03, aabb[3] - aabb[0])
    sy = max(0.03, aabb[5] - aabb[2])
    sz = max(0.03, aabb[4] - aabb[1])
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, -cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    obj.data.materials.append(mat)
    if bevel_width > 0:
        bev = obj.modifiers.new("Bevel", "BEVEL")
        bev.width = bevel_width
        bev.segments = 2
    return obj


def setup_lighting_rig(use_volumetrics: bool):
    scene = bpy.context.scene
    w = bpy.data.worlds.new("ShortWorld")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "SINGLE_SCATTERING"
    sky.sun_disc = False

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "B_SPLINE"
    el0 = ramp.color_ramp.elements[0]
    el0.position = 0.0
    el1 = ramp.color_ramp.elements[1]
    el1.position = 0.26
    el_mid = ramp.color_ramp.elements.new(0.09)
    _ = el_mid

    sky_mix = nt.nodes.new("ShaderNodeMix")
    sky_mix.data_type = "RGBA"
    sky_mix.inputs["Factor"].default_value = 0.80

    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(sky.outputs["Color"], sky_mix.inputs[6])
    nt.links.new(ramp.outputs["Color"], sky_mix.inputs[7])
    nt.links.new(sky_mix.outputs[2], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    vol_node = None
    if use_volumetrics:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 20, 6))
        vol_box = bpy.context.active_object
        vol_box.name = "AtmosphereHaze"
        vol_box.scale = (50, 80, 24)
        vm = bpy.data.materials.new("HazeMat")
        if vm.node_tree is None:
            vm.use_nodes = True
        vnt = vm.node_tree
        vnt.nodes.clear()
        vout = vnt.nodes.new("ShaderNodeOutputMaterial")
        vol_node = vnt.nodes.new("ShaderNodeVolumePrincipled")
        vol_node.inputs["Color"].default_value = (0.78, 0.87, 1.0, 1.0)
        vol_node.inputs["Density"].default_value = 0.0014
        vol_node.inputs["Anisotropy"].default_value = 0.65
        vnt.links.new(vol_node.outputs["Volume"], vout.inputs["Volume"])
        vol_box.data.materials.append(vm)

    bpy.ops.object.light_add(type="SUN", location=(12, -10, 14))
    sun = bpy.context.active_object
    sun.name = "HeroSun"

    bpy.ops.object.light_add(type="AREA", location=(-6, -4, 6))
    fill = bpy.context.active_object
    fill.name = "CoolFill"
    fill.data.size = 7.5

    return {"sky": sky, "bg": bg, "sun": sun, "fill": fill, "vol": vol_node, "ramp": ramp, "sky_mix": sky_mix, "base_exp": 0.14}


def apply_light_preset(rig: dict, preset: str):
    sky = rig["sky"]
    bg = rig["bg"]
    sun = rig["sun"]
    fill = rig["fill"]
    vol = rig["vol"]
    ramp = rig["ramp"]
    sky_mix = rig["sky_mix"]
    scene = bpy.context.scene

    els = ramp.color_ramp.elements
    if preset == "golden":
        els[0].color = srgb_hex("#ffaa48")
        els[1].color = srgb_hex("#c86878")
        els[2].color = srgb_hex("#4b3e7c")
        sky_mix.inputs["Factor"].default_value = 0.96
        sky.sun_elevation = math.radians(6.5)
        sky.sun_rotation = math.radians(32.0)
        sky.air_density = 1.35
        sky.aerosol_density = 1.9
        bg.inputs["Strength"].default_value = 0.80
        sun.data.energy = 5.2
        sun.data.color = srgb_hex("#ffad58")[:3]
        sun.data.angle = math.radians(2.0)
        sun.rotation_euler = (math.radians(74), 0.0, math.radians(-42))
        fill.data.energy = 32.0
        fill.data.color = srgb_hex("#8d8cf2")[:3]
        if vol:
            vol.inputs["Density"].default_value = 0.0018
        rig["base_exp"] = 0.16
    elif preset == "interior":
        els[0].color = srgb_hex("#3c466b")
        els[1].color = srgb_hex("#2a3250")
        els[2].color = srgb_hex("#1d233a")
        sky_mix.inputs["Factor"].default_value = 0.90
        sky.sun_elevation = math.radians(10.0)
        sky.sun_rotation = math.radians(48.0)
        sky.air_density = 1.0
        sky.aerosol_density = 1.0
        bg.inputs["Strength"].default_value = 0.28
        sun.data.energy = 1.5
        sun.data.color = srgb_hex("#dce8ff")[:3]
        sun.data.angle = math.radians(3.5)
        sun.rotation_euler = (math.radians(52), 0.0, math.radians(-55))
        fill.data.energy = 28.0
        fill.data.color = srgb_hex("#9cb6f5")[:3]
        if vol:
            vol.inputs["Density"].default_value = 0.0018
        rig["base_exp"] = 0.44
    elif preset == "night":
        els[0].color = srgb_hex("#2d4782")
        els[1].color = srgb_hex("#1b2b58")
        els[2].color = srgb_hex("#101736")
        sky_mix.inputs["Factor"].default_value = 0.92
        sky.sun_elevation = math.radians(2.0)
        sky.air_density = 1.0
        sky.aerosol_density = 0.8
        bg.inputs["Strength"].default_value = 0.24
        sun.data.energy = 0.75
        sun.data.color = srgb_hex("#84abff")[:3]
        sun.data.angle = math.radians(2.0)
        sun.rotation_euler = (math.radians(58), 0.0, math.radians(30))
        fill.data.energy = 16.0
        fill.data.color = srgb_hex("#6a8ee0")[:3]
        rig["base_exp"] = 0.16
    else:  # day
        els[0].color = srgb_hex("#76bcff")
        els[1].color = srgb_hex("#2d82f2")
        els[2].color = srgb_hex("#0d52d4")
        sky_mix.inputs["Factor"].default_value = 0.98
        sky.sun_elevation = math.radians(28.0)
        sky.sun_rotation = math.radians(42.0)
        sky.air_density = 1.0
        sky.aerosol_density = 0.55
        bg.inputs["Strength"].default_value = 0.74
        sun.data.energy = 4.4
        sun.data.color = srgb_hex("#fff7e4")[:3]
        sun.data.angle = math.radians(1.6)
        sun.rotation_euler = (math.radians(60), 0.0, math.radians(-38))
        fill.data.energy = 38.0
        fill.data.color = srgb_hex("#88b8ff")[:3]
        if vol:
            vol.inputs["Density"].default_value = 0.0009
        rig["base_exp"] = 0.02
    scene.view_settings.exposure = rig["base_exp"]


def setup_compositor_52():
    scene = bpy.context.scene
    ng = bpy.data.node_groups.new("ShortComp", "CompositorNodeTree")
    scene.compositing_node_group = ng
    ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")

    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "Medium"
    glare.inputs["Threshold"].default_value = 0.95
    glare.inputs["Strength"].default_value = 0.42
    out = ng.nodes.new("NodeGroupOutput")

    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs["Image"], out.inputs["Image"])


def smoother(t: float) -> float:
    u = max(0.0, min(1.0, t))
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


def lerp3(a: Vector, b: Vector, u: float) -> Vector:
    return a.lerp(b, u)


def shot_at_frame(shots: list[dict], fr: int) -> dict:
    for s in shots:
        if int(s["a"]) <= fr < int(s["b"]):
            return s
    return shots[-1]


def cam_eval(shots: list[dict], fr: int) -> tuple[Vector, Vector, float, dict]:
    s = shot_at_frame(shots, fr)
    f0 = int(s["a"])
    land = s.get("landFrames", [int(s["b"]) - 4, int(s["b"])])
    glide_end = max(f0 + 1, int(land[0]))
    u = smoother((fr - f0) / float(glide_end - f0))
    p0 = plan_to_blender(s["camStart"])
    p1 = plan_to_blender(s["camEnd"])
    lk0 = plan_to_blender(s.get("lookAtStart", s["lookAt"]))
    lk1 = plan_to_blender(s.get("lookAtEnd", s["lookAt"]))
    return lerp3(p0, p1, u), lerp3(lk0, lk1, u), float(s.get("fov", 40.0)), s


def make_card_plane(name: str, height_m: float, aspect_w_over_h: float, cam_obj, mat):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, 0.0))
    pl = bpy.context.active_object
    pl.name = name
    # Shift pivot to bottom center (y_local = 0..1) and keep card strictly upright (yaw-only toward camera XY)
    for v in pl.data.vertices:
        v.co.y += 0.5
    pl.scale = (height_m * aspect_w_over_h, height_m, 1.0)
    pl.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    pl.data.materials.append(mat)
    return pl


def orient_card_upright(pl, cam_pos: Vector, rot_deg=0.0, pitch_deg=0.0, yaw_deg=0.0):
    dx = cam_pos.x - pl.location.x
    dy = cam_pos.y - pl.location.y
    yaw = math.atan2(dx, -dy) + math.radians(yaw_deg)
    q_upright = Euler((math.radians(90.0 - pitch_deg), 0.0, yaw), "XYZ").to_quaternion()
    pl.rotation_mode = "QUATERNION"
    if abs(rot_deg) > 1e-4:
        q_tilt = Euler((0.0, 0.0, math.radians(rot_deg)), "XYZ").to_quaternion()
        pl.rotation_quaternion = q_upright @ q_tilt
    else:
        pl.rotation_quaternion = q_upright


def build_card_mat(name: str, img_path: str, emit_mix=0.50):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.92
    bsdf.inputs["Specular IOR Level"].default_value = 0.02
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.extension = "CLIP"
    tex.image = bpy.data.images.load(os.path.abspath(img_path), check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    if emit_mix > 0.0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit_mix
    return m, tex


def setup_world_ink(ink_radius: float):
    """Attach world-space Geometry Nodes Inverted-Hull ink outlines that obey 3D depth occlusion behind alpha cards."""
    ink_m = bpy.data.materials.new("WorldInkHullMat")
    ink_m.use_nodes = True
    nt = ink_m.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    em_n = nt.nodes.new("ShaderNodeEmission")
    em_n.inputs["Color"].default_value = srgb_hex("#17111e")
    em_n.inputs["Strength"].default_value = 0.25
    nt.links.new(em_n.outputs["Emission"], out_n.inputs["Surface"])
    ink_m.use_backface_culling = True

    ng = bpy.data.node_groups.new("WorldInkHullGN", "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    n_in = ng.nodes.new("NodeGroupInput")
    n_out = ng.nodes.new("NodeGroupOutput")
    n_self = ng.nodes.new("GeometryNodeSelfObject")
    n_oinfo = ng.nodes.new("GeometryNodeObjectInfo")
    n_abs = ng.nodes.new("ShaderNodeVectorMath")
    n_abs.operation = "ABSOLUTE"
    n_max = ng.nodes.new("ShaderNodeVectorMath")
    n_max.operation = "MAXIMUM"
    n_max.inputs[1].default_value = (0.05, 0.05, 0.05)
    n_norm = ng.nodes.new("GeometryNodeInputNormal")
    n_div1 = ng.nodes.new("ShaderNodeVectorMath")
    n_div1.operation = "DIVIDE"
    n_normz = ng.nodes.new("ShaderNodeVectorMath")
    n_normz.operation = "NORMALIZE"
    n_scale = ng.nodes.new("ShaderNodeVectorMath")
    n_scale.operation = "SCALE"
    n_scale.inputs["Scale"].default_value = max(0.005, float(ink_radius) * 1.15)
    n_div2 = ng.nodes.new("ShaderNodeVectorMath")
    n_div2.operation = "DIVIDE"
    n_setp = ng.nodes.new("GeometryNodeSetPosition")
    n_flip = ng.nodes.new("GeometryNodeFlipFaces")
    n_setm = ng.nodes.new("GeometryNodeSetMaterial")
    n_setm.inputs["Material"].default_value = ink_m
    n_join = ng.nodes.new("GeometryNodeJoinGeometry")

    ng.links.new(n_self.outputs["Self Object"], n_oinfo.inputs["Object"])
    ng.links.new(n_oinfo.outputs["Scale"], n_abs.inputs[0])
    ng.links.new(n_abs.outputs["Vector"], n_max.inputs[0])
    ng.links.new(n_norm.outputs["Normal"], n_div1.inputs[0])
    ng.links.new(n_max.outputs["Vector"], n_div1.inputs[1])
    ng.links.new(n_div1.outputs["Vector"], n_normz.inputs[0])
    ng.links.new(n_normz.outputs["Vector"], n_scale.inputs[0])
    ng.links.new(n_scale.outputs["Vector"], n_div2.inputs[0])
    ng.links.new(n_max.outputs["Vector"], n_div2.inputs[1])
    ng.links.new(n_in.outputs[0], n_setp.inputs["Geometry"])
    ng.links.new(n_div2.outputs["Vector"], n_setp.inputs["Offset"])
    ng.links.new(n_setp.outputs["Geometry"], n_flip.inputs["Mesh"])
    ng.links.new(n_flip.outputs["Mesh"], n_setm.inputs["Geometry"])
    ng.links.new(n_in.outputs[0], n_join.inputs[0])
    ng.links.new(n_setm.outputs["Geometry"], n_join.inputs[0])
    ng.links.new(n_join.outputs["Geometry"], n_out.inputs[0])

    exclude_tokens = (
        "Card_", "Cloud", "Haze", "Pebble", "Steam", "Icosphere", "Blueprint", "Sign",
        "Boulevard", "Lawn", "Curb", "Platform", "Ballast", "Floor", "Wall", "Glow", "Firebox", "Win", "Rail", "Plane",
    )
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.visible_shadow:
            continue
        if any(tok in obj.name for tok in exclude_tokens):
            continue
        if min(abs(v) for v in obj.scale) < 0.025:
            continue
        mod = obj.modifiers.new("InkHull", "NODES")
        mod.node_group = ng
    return ng


def add_actor_proxy(pos: list[float]):
    px, py, pz = pos[0], -pos[2], pos[1]
    ink_m = make_mat("InkMat", srgb_hex("#241726"), roughness=0.9)
    skin_m = make_mat("SkinMat", srgb_hex("#ffe2c2"), roughness=0.55)
    coat_m = make_mat("CoatMat", srgb_hex("#365f9e"), roughness=0.6)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.72, location=(px, py, pz + 0.96))
    bpy.context.active_object.data.materials.append(coat_m)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.27, location=(px, py, pz + 1.56))
    h = bpy.context.active_object
    h.scale = (1.0, 0.82, 0.96)
    h.data.materials.append(skin_m)
    bpy.ops.object.shade_smooth()
    for s in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.032, location=(px + s * 0.08, py - 0.21, pz + 1.59))
        bpy.context.active_object.data.materials.append(ink_m)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.032, depth=0.62, location=(px + s * 0.09, py, pz + 0.31))
        bpy.context.active_object.data.materials.append(ink_m)


def build_default_world(plan: dict):
    ground_m = make_mat("GroundDirt", srgb_hex("#b87042"), roughness=0.88, bump_scale=28.0)
    road_m = make_mat("RoadAsphalt", srgb_hex("#3a404c"), roughness=0.72, bump_scale=18.0)
    bldg_m = make_mat("WallPaint", srgb_hex("#d8c2a6"), roughness=0.75, bump_scale=6.0)
    pebble_m = make_mat("PebbleRock", srgb_hex("#6a584a"), roughness=0.85, bump_scale=12.0)

    bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0, 0, -0.01))
    bpy.context.active_object.data.materials.append(ground_m)

    rng = random.Random(42)
    for _ in range(55):
        rx = rng.uniform(-8.0, 8.0)
        ry = rng.uniform(-12.0, 22.0)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rng.uniform(0.04, 0.11), location=(rx, ry, 0.02))
        st = bpy.context.active_object
        st.scale = (rng.uniform(0.8, 1.5), rng.uniform(0.8, 1.4), rng.uniform(0.4, 0.8))
        st.data.materials.append(pebble_m)

    for idx, p in enumerate(plan.get("props", [])):
        pid = p.get("id", f"prop_{idx}")
        aabb = p.get("aabb", [0] * 6)
        mat = road_m if "road" in pid else bldg_m
        add_box(pid, aabb, mat, bevel_width=0.05 if "road" not in pid else 0.0)


def configure_render(engine: str, samples: int, scale: float, fmt: str, use_rt: bool = True):
    scene = bpy.context.scene
    scene.render.resolution_x = int(round(1080 * scale))
    scene.render.resolution_y = int(round(1920 * scale))
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.render.image_settings.file_format = fmt
    scene.render.image_settings.color_mode = "RGB"
    if fmt == "JPEG":
        scene.render.image_settings.quality = 95
    else:
        scene.render.image_settings.compression = 1

    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        prefs = bpy.context.preferences.addons.get("cycles")
        if prefs:
            for dev_type in ("OPTIX", "CUDA"):
                devs = prefs.preferences.get_devices_for_type(dev_type)
                if any(d.type != "CPU" for d in devs):
                    prefs.preferences.compute_device_type = dev_type
                    for d in devs:
                        d.use = (d.type != "CPU")
                    scene.cycles.device = "GPU"
                    break
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = samples
        scene.eevee.use_raytracing = use_rt


def aim_camera_with_roll(cam, cam_pos: Vector, lk_pos: Vector, roll_rad: float):
    fwd = lk_pos - cam_pos
    if fwd.length < 1e-5:
        fwd = Vector((0.0, 1.0, 0.0))
    q_aim = fwd.normalized().to_track_quat("-Z", "Y")
    q_roll = Euler((0.0, 0.0, roll_rad), "XYZ").to_quaternion()
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = q_aim @ q_roll


def main():
    args = parse_args()
    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    clear_scene()
    shots = plan.get("shots", [])
    rig = setup_lighting_rig(args.volumetrics)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1.35))
    target = bpy.context.active_object
    target.name = "CamTarget"

    bpy.ops.object.camera_add(location=(0, -6.0, 1.8))
    cam = bpy.context.active_object
    cam.name = "ShortCam"
    bpy.context.scene.camera = cam
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 24.0
    cam.data.dof.use_dof = False
    cam.data.dof.aperture_fstop = 4.2

    scene_mod_path = args.scene_module
    if not scene_mod_path and not args.no_scene_module:
        cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_scene.py")
        if os.path.exists(cand):
            scene_mod_path = cand

    scene_mod = None
    scene_state = None
    if scene_mod_path:
        spec = importlib.util.spec_from_file_location("custom_blender_scene", os.path.abspath(scene_mod_path))
        scene_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scene_mod)
        scene_state = scene_mod.build_scene(plan, args.cards, cam, target, rig)
    else:
        build_default_world(plan)

    cards_col = bpy.data.collections.new("ActorCards")
    bpy.context.scene.collection.children.link(cards_col)

    # Load card manifest & optional per-frame camPath
    card_planes = {}
    placements = []
    cam_path = []
    if args.cards:
        man_path = os.path.join(args.cards, "manifest.json")
        if os.path.exists(man_path):
            with open(man_path, encoding="utf-8") as mf:
                manifest = json.load(mf)
            placements = manifest.get("placements", [])
            cam_path = manifest.get("camPath", [])
            card_meta = manifest.get("cards", {})
            by_id: dict[str, list[dict]] = {}
            for p in placements:
                by_id.setdefault(p["id"], []).append(p)
            for pid, items in by_id.items():
                first = items[0]
                cname = first["card"]
                img_file = os.path.join(args.cards, f"{cname}.png")
                meta = card_meta.get(cname, {})
                cw = float(meta.get("width", 900))
                ch = float(meta.get("height", 1500))
                mat, tex_node = build_card_mat(f"CardMat_{pid}", img_file, emit_mix=float(first.get("emit", 0.50)))
                pl = make_card_plane(f"Card_{pid}", float(first.get("heightM", 1.9)), cw / max(1.0, ch), cam, mat)
                for old_c in list(pl.users_collection):
                    old_c.objects.unlink(pl)
                cards_col.objects.link(pl)
                pl.visible_shadow = bool(first.get("shadow", True))
                card_planes[pid] = {"obj": pl, "tex": tex_node, "mat": mat, "items": items, "last_card": cname}
    else:
        actors = plan.get("actors", [])
        if actors:
            add_actor_proxy(actors[0].get("pos", [0.0, 0.0, 0.0]))

    if args.ink:
        setup_world_ink(args.ink_radius)

    setup_compositor_52()
    configure_render(args.engine, args.samples, args.scale, args.format, use_rt=not args.no_rt)
    os.makedirs(args.out, exist_ok=True)

    if args.smoke:
        render_list = [0]
    elif args.frames_list:
        render_list = [int(x.strip()) for x in args.frames_list.split(",") if x.strip()]
    elif args.frame >= 0:
        render_list = [args.frame]
    elif "-" in args.frames:
        a, b = args.frames.split("-", 1)
        render_list = list(range(int(a), int(b) + 1))
    else:
        render_list = list(range(0, int(plan.get("totalFrames", 150))))

    scene = bpy.context.scene
    ext = "jpg" if args.format == "JPEG" else "png"
    last_preset = None

    for fr in render_list:
        if 0 <= fr < len(cam_path):
            cp = cam_path[fr]
            cam_pos = plan_to_blender(cp["pos"])
            lk_pos = plan_to_blender(cp["look"])
            fov_deg = float(cp.get("fov", 40.0))
            roll_rad = float(cp.get("roll", 0.0))
            preset = cp.get("light", "day")
            c_inf = float(cp.get("cInf", 0.0))
            focus_bl = plan_to_blender(cp.get("focus", cp["look"]))
        else:
            cam_pos, lk_pos, fov_deg, shot = cam_eval(shots, fr)
            roll_rad = 0.0
            preset = shot.get("light", "day")
            c_inf = 0.0
            focus_bl = lk_pos

        cam.location = cam_pos
        target.location = lk_pos
        aim_camera_with_roll(cam, cam_pos, lk_pos, roll_rad)
        cam.data.lens = 12.0 / math.tan(0.5 * math.radians(fov_deg))
        if c_inf > 0.2:
            cam.data.dof.use_dof = True
            cam.data.dof.focus_distance = max(0.75, (focus_bl - cam_pos).length)
            cam.data.dof.aperture_fstop = max(1.8, 10.5 - c_inf)
        else:
            cam.data.dof.use_dof = False

        if preset != last_preset:
            apply_light_preset(rig, preset)
            last_preset = preset
        flash_k = float(cp.get("flash", 0.0)) if (0 <= fr < len(cam_path)) else 0.0
        scene.view_settings.exposure = rig.get("base_exp", 0.14) + flash_k * 4.5

        for pid, slot in card_planes.items():
            active = None
            for item in slot["items"]:
                if int(item["a"]) <= fr < int(item["b"]):
                    active = item
                    break
            pl = slot["obj"]
            if active is None:
                pl.hide_render = True
            else:
                pl.hide_render = False
                pos_bl = plan_to_blender(active["pos"])
                jitter = active.get("jitter")
                if jitter:
                    jx = float(jitter) * math.sin(fr * 2.4 + hash(pid) % 7)
                    jz = float(jitter) * 0.6 * math.cos(fr * 3.1)
                    pos_bl = Vector((pos_bl.x + jx, pos_bl.y, pos_bl.z + jz))
                pl.location = pos_bl
                h_m = float(active.get("heightM", 1.9))
                cname = active["card"]
                if cname != slot["last_card"]:
                    img_file = os.path.join(args.cards, f"{cname}.png")
                    slot["tex"].image = bpy.data.images.load(os.path.abspath(img_file), check_existing=True)
                    slot["last_card"] = cname
                img = slot["tex"].image
                aspect = (img.size[0] / max(1, img.size[1])) if img and img.size[1] else 0.6
                sx = float(active.get("scaleX", 1.0))
                sy = float(active.get("scaleY", 1.0))
                pl.scale = (h_m * aspect * sx, h_m * sy, 1.0)
                orient_card_upright(
                    pl,
                    cam_pos,
                    float(active.get("rotDeg", 0.0)),
                    float(active.get("pitchDeg", 0.0)),
                    float(active.get("yawDeg", 0.0)),
                )
                bsdf = slot["mat"].node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs["Emission Strength"].default_value = float(active.get("emit", 0.50))

        if scene_mod and hasattr(scene_mod, "update_frame"):
            scene_mod.update_frame(fr, scene, cam, target, scene_state)

        scene.frame_set(fr)

        out_path = os.path.abspath(os.path.join(args.out, f"frame_{fr:04d}.{ext}"))
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"BLENDER_FRAME_OK {fr} -> {out_path}")


if __name__ == "__main__":
    main()
