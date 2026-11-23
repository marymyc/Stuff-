"""Modular 3D environment kits for Blender (bpy). Each kit builds a stylised, low-poly world and returns
{"focus": (x, y, z)}. Add a kit by writing a function and registering it in KITS.
Runs inside Blender (pip `bpy` or `blender -b -P`)."""
import math

import bpy
from mathutils import noise, Vector



def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


class Geo:
    """Accumulates boxes/frustums into one mesh (cheap, flat-shaded, stylised)."""

    def __init__(self):
        self.v, self.f = [], []

    def box(self, c, s, rz=0.0):
        cx, cy, cz = c
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        pts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
               (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        co, si = math.cos(rz), math.sin(rz)
        b = len(self.v)
        for x, y, z in pts:
            self.v.append((cx + x * co - y * si, cy + x * si + y * co, cz + z))
        for a, b2, c2, d in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append((b + a, b + b2, b + c2, b + d))

    def cone(self, c, r1, r2, h, seg=10, axis="z"):
        cx, cy, cz = c
        r2 = max(r2, 1e-4)

        def m(lx, ly, lz):
            if axis == "x":
                return (cx + lz, cy + ly, cz + lx)
            if axis == "y":
                return (cx + lx, cy + lz, cz + ly)
            return (cx + lx, cy + ly, cz + lz)

        b = len(self.v)
        for r, z in ((r1, 0), (r2, h)):
            for i in range(seg):
                a = 2 * math.pi * i / seg
                self.v.append(m(r * math.cos(a), r * math.sin(a), z))
        for i in range(seg):
            j = (i + 1) % seg
            self.f.append((b + i, b + j, b + seg + j, b + seg + i))
        self.f.append(tuple(b + i for i in reversed(range(seg))))
        self.f.append(tuple(b + seg + i for i in range(seg)))

    def build(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        ob = bpy.data.objects.new(name, me)
        if mat:
            ob.data.materials.append(mat)
        return link(ob)


# ---------- materials ----------
def _principled(m):
    m.use_nodes = True
    return m.node_tree.nodes["Principled BSDF"]


def mat_solid(name, rgb, rough=0.9, emit=0.0):
    m = bpy.data.materials.new(name)
    b = _principled(m)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def _ramp(nt, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[1][0], (*stops[1][1], 1)
    for pos, col in stops[2:]:
        e = els.new(pos)
        e.color = (*col, 1)
    return r


def mat_noise(name, stops, scale=4.0, rough=0.95):
    m = bpy.data.materials.new(name)
    b = _principled(m)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    r = _ramp(nt, stops)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def mat_stone(name="stone"):
    """3D Voronoi edge-distance: reads as mortar lines on any face orientation."""
    m = bpy.data.materials.new(name)
    b = _principled(m)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.voronoi_dimensions = "3D"
    v.feature = "DISTANCE_TO_EDGE"
    v.inputs["Scale"].default_value = 1.6
    r = _ramp(nt, [(0.0, (0.2, 0.2, 0.22)), (0.07, (0.62, 0.62, 0.6)), (1.0, (0.72, 0.72, 0.7))])
    nt.links.new(tc.outputs["Object"], v.inputs["Vector"])
    nt.links.new(v.outputs["Distance"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    return m


def mat_bands(name, stops, scale=2.5, distortion=6.0):
    m = bpy.data.materials.new(name)
    b = _principled(m)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = "BANDS"
    w.bands_direction = "Z"
    w.inputs["Scale"].default_value = scale
    w.inputs["Distortion"].default_value = distortion
    r = _ramp(nt, stops)
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    nt.links.new(w.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    return m


def grid_mesh(name, nx, ny, sx, sy, zfunc, mat, origin=(0, 0, 0), plane="xy"):
    """Regular grid; plane 'xy' = ground, 'yz' = wall facing x (zfunc returns x offset)."""
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u = (i / nx - 0.5) * sx
            v = (j / ny - 0.5) * sy
            if plane == "xy":
                verts.append((origin[0] + u, origin[1] + v, origin[2] + zfunc(u, v)))
            else:
                verts.append((origin[0] + zfunc(u, v), origin[1] + u, origin[2] + (v + sy / 2)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    return link(ob)


def _n(x, y, z=0.0, s=0.08):
    return noise.noise(Vector((x * s, y * s, z)))


# ---------- shared pieces ----------
def ground(green=True, size=170, flat_r=9.0, hill=2.2):
    stops = [(0.0, (0.16, 0.5, 0.12)), (0.5, (0.3, 0.7, 0.18)), (1.0, (0.5, 0.82, 0.25))] if green else \
        [(0.0, (0.62, 0.3, 0.16)), (0.55, (0.82, 0.48, 0.24)), (1.0, (0.9, 0.62, 0.34))]

    def z(u, v):
        d = math.hypot(u, v)
        fade = max(0.0, min(1.0, (d - flat_r) / 25.0))
        return _n(u, v) * hill * fade * 2.0

    return grid_mesh("ground", 56, 56, size, size, z, mat_noise("ground", stops, 5.0))


def trees(rng, count=16, rmin=14, rmax=60):
    g, g2 = Geo(), Geo()
    for _ in range(count):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(rmin, rmax)
        x, y, h = math.cos(a) * r, math.sin(a) * r, rng.uniform(3.5, 6)
        g.cone((x, y, 0), 0.25, 0.2, h * 0.35, 6)
        g2.cone((x, y, h * 0.3), h * 0.28, 0.05, h * 0.75, 7)
    g.build("trunks", mat_solid("trunk", (0.35, 0.2, 0.1)))
    g2.build("leaves", mat_solid("leaves", (0.1, 0.45, 0.15)))


def mountains(rng, ring=95, count=7, tint=(0.35, 0.45, 0.55)):
    g = Geo()
    for i in range(count):
        a = math.radians(-70 + i * 140 / max(1, count - 1)) + math.pi / 2
        g.cone((math.cos(a) * ring, math.sin(a) * ring + 20, -2), rng.uniform(14, 24), 1.5, rng.uniform(20, 36), 7)
    g.build("mountains", mat_solid("mountain", tint, 1.0))


def grass(rng, count=380, radius=9.0):
    g = Geo()
    for _ in range(count):
        a, r = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.random())
        g.cone((math.cos(a) * r, math.sin(a) * r, 0), 0.07, 0.01, rng.uniform(0.25, 0.55), 4)
    g.build("grass", mat_solid("grass", (0.35, 0.8, 0.2), 1.0))


# ---------- props ----------
def add_prop(name, pos):
    x, y, z = pos
    g = Geo()
    if name == "cart":
        g.box((x, y, z + 0.75), (2.2, 1.3, 0.12))
        g.box((x, y, z + 1.0), (2.1, 0.12, 0.5))
        for sx in (-0.8, 0.8):
            for sy in (-0.7, 0.7):
                g.cone((x + sx, y + sy - 0.04, z + 0.5), 0.5, 0.5, 0.08, 10, axis="y")
        g.build("cart", mat_solid("wood", (0.45, 0.28, 0.14)))
    elif name == "crate":
        g.box((x, y, z + 0.4), (0.8, 0.8, 0.8))
        g.build("crate", mat_solid("crate", (0.6, 0.4, 0.2)))
    elif name == "barrel":
        g.cone((x, y, z), 0.4, 0.4, 0.9, 10)
        g.build("barrel", mat_solid("barrel", (0.5, 0.3, 0.15)))
    elif name == "umbrella":
        g.cone((x, y, z), 0.04, 0.04, 2.0, 5)
        g.cone((x, y, z + 2.0), 1.3, 0.05, 0.5, 10)
        g.build("umbrella", mat_solid("umbrella", (0.95, 0.75, 0.15)))
    elif name == "lamp":
        g.cone((x, y, z), 0.05, 0.05, 1.8, 5)
        g.build("lamp_pole", mat_solid("pole", (0.1, 0.1, 0.12)))
        g2 = Geo()
        g2.box((x, y, z + 1.9), (0.3, 0.3, 0.3))
        g2.build("lamp_glow", mat_solid("glow", (1.0, 0.75, 0.35), emit=12.0))
    elif name == "table":
        g.box((x, y, z + 0.75), (2.0, 1.0, 0.1))
        for sx in (-0.9, 0.9):
            for sy in (-0.4, 0.4):
                g.box((x + sx, y + sy, z + 0.37), (0.1, 0.1, 0.75))
        g.build("table", mat_solid("table", (0.5, 0.32, 0.18)))


# ---------- kits ----------
def kit_field(scene, rng, tod):
    ground(True)
    trees(rng)
    mountains(rng)
    grass(rng)
    return {"focus": (0.0, 0.0, 1.0)}


def kit_fortress(scene, rng, tod):
    ground(True)
    mountains(rng)
    grass(rng, 260)
    stone = mat_stone()
    g = Geo()
    g.box((0, 7, 2.5), (26, 1.6, 5))
    for x in range(-12, 13, 2):
        g.box((x, 7, 5.35), (1.0, 1.6, 0.7))
    for sx in (-14, 14):
        g.cone((sx, 7, 0), 2.2, 2.0, 8.5, 12)
    g.build("walls", stone)
    gate = Geo()
    gate.box((0, 6.1, 1.5), (3.2, 0.2, 3.0))
    gate.build("gate", mat_solid("gate", (0.08, 0.06, 0.05)))
    roofs = Geo()
    for sx in (-14, 14):
        roofs.cone((sx, 7, 8.5), 2.7, 0.05, 3.0, 12)
    roofs.build("roofs", mat_solid("roof", (0.7, 0.12, 0.1)))
    ban = Geo()
    for bx in (-5, 5):
        ban.box((bx, 6.1, 3.6), (0.9, 0.05, 1.8))
    ban.build("banners", mat_solid("banner", (0.1, 0.25, 0.8)))
    return {"focus": (0.0, 0.0, 1.0)}


def kit_canyon(scene, rng, tod):
    ground(False, flat_r=14)
    bands = mat_bands("cliff", [(0.0, (0.55, 0.12, 0.1)), (0.35, (0.9, 0.38, 0.12)), (0.65, (0.8, 0.2, 0.45)),
                                (1.0, (1.0, 0.7, 0.25))])
    for side, w in ((1, 15.0), (-1, 28.0)):
        grid_mesh("cliff", 40, 14, 140, 24 if side > 0 else 14,
                  lambda u, v, s=side: _n(u, v, 3.0, 0.12) * 3.0 * s, bands, origin=(side * w, 20, 0), plane="yz")
    ballast = Geo()
    ballast.box((0, 20, 0.08), (3.0, 140, 0.16))
    ballast.build("ballast", mat_solid("ballast", (0.5, 0.42, 0.38)))
    sl = Geo()
    for y in range(-48, 90):
        sl.box((0, y * 0.7, 0.2), (2.4, 0.22, 0.1))
    sl.build("sleepers", mat_solid("sleeper", (0.28, 0.17, 0.1)))
    rails = Geo()
    for rx in (-0.6, 0.6):
        rails.box((rx, 20, 0.3), (0.09, 140, 0.12))
    rails.build("rails", mat_solid("steel", (0.6, 0.62, 0.66), 0.35))
    poles = Geo()
    for y in range(-20, 80, 12):
        poles.cone((3.2, y, 0), 0.08, 0.06, 5.5, 5)
        poles.box((3.2, y, 5.3), (1.4, 0.08, 0.08))
    poles.build("poles", mat_solid("pole", (0.25, 0.17, 0.1)))
    return {"focus": (0.0, 0.0, 1.0)}


def kit_interior(scene, rng, tod):
    floor = Geo()
    floor.box((0, 4, -0.05), (16, 16, 0.1))
    floor.build("floor", mat_solid("floor", (0.45, 0.3, 0.18)))
    walls = Geo()
    walls.box((0, 12, 2.0), (16, 0.3, 4.0))
    walls.box((-8, 4, 2.0), (0.3, 16, 4.0))
    walls.box((8, 4, 2.0), (0.3, 16, 4.0))
    walls.build("walls", mat_solid("wall", (0.85, 0.72, 0.55)))
    win = Geo()
    win.box((3.5, 11.8, 2.3), (3.0, 0.1, 1.8))
    win.build("window", mat_solid("window", (0.8, 0.92, 1.0), emit=6.0))
    add_prop("table", (-2.5, 6.5, 0))
    add_prop("lamp", (-5, 8, 0))
    room = bpy.data.lights.new("room", "POINT")      # interiors need their own light (sun is blocked by the walls)
    room.energy, room.color = 1800, (1.0, 0.85, 0.65)
    ro = bpy.data.objects.new("room", room)
    ro.location = (0, 2, 3.6)
    link(ro)
    return {"focus": (0.0, 0.0, 1.0)}


KITS = {"field": kit_field, "fortress": kit_fortress, "canyon": kit_canyon, "interior": kit_interior}


def fx_explosion(loc, frames):
    """Fireball (front, biggest glow), hot core, and smoke behind/above it; keyframed growth."""
    layers = [  # rgb, emission, final scale, delay, offset (x, y, z)
        ((0.12, 0.1, 0.1), 0.0, 3.0, 5, (0.0, 1.8, 3.2)),     # smoke: behind and higher
        ((1.0, 0.4, 0.06), 5.0, 3.6, 0, (0.0, 0.0, 1.6)),   # fireball
        ((1.0, 0.8, 0.3), 8.0, 1.9, 2, (0.0, -0.6, 1.5)),  # core, nearest the camera
    ]
    for k, (rgb, em, s1, delay, off) in enumerate(layers):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0,
                                              location=(loc[0] + off[0], loc[1] + off[1], loc[2] + off[2]))
        ob = bpy.context.active_object
        ob.data.materials.append(mat_solid(f"fx{k}", rgb, 0.9, em))
        ob.scale = (0.05, 0.05, 0.05)
        ob.keyframe_insert("scale", frame=1 + delay)
        ob.scale = (s1, s1, s1)
        ob.keyframe_insert("scale", frame=max(2 + delay, min(frames, 1 + delay + 14)))
