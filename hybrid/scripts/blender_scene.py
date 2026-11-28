"""Generic Blender set library for the hybrid pipeline (loaded automatically by blender_render.py).

build_scene(plan, cards_dir, cam, target, rig) builds one ZONE per location set (150 m apart along Blender +Y, = plan z * -1) and one
SHOT collection per shot for its props / insert object. update_frame() shows only the current shot's zone and props.
Plan space [x, y_up, z] -> Blender [x, -z, y]: the camera sits on -Y of the zone origin and looks toward +Y; the cast stands at the origin.
Sets: field, fortress, canyon (rails), interior, town. Insert objects: coin paper calendar newspaper caliper thermometer moneybag map clock marble.
"""
import math

import bpy
from mathutils import Vector, noise

ZONE_DZ = 150.0


# ------------------------------------------------------------------ geometry
class Geo:
    """Accumulates boxes / frustums / spheres into one mesh (flat shaded, stylised)."""

    def __init__(self):
        self.v, self.f = [], []

    def box(self, c, s, rz=0.0, ry=0.0):
        cx, cy, cz = c
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        pts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        cy_, sy_, cz_, sz_ = math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
        b = len(self.v)
        for x, y, z in pts:
            x2, z2 = x * cy_ + z * sy_, -x * sy_ + z * cy_             # tilt about Y (sheets leaning in the XZ plane)
            self.v.append((cx + x2 * cz_ - y * sz_, cy + x2 * sz_ + y * cz_, cz + z2))
        for a, b2, c2, d in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append((b + a, b + b2, b + c2, b + d))

    def cone(self, c, r1, r2, h, seg=10, axis="z"):
        """frustum with its base centre at c, extending +h along `axis`"""
        cx, cy, cz = c
        r2 = max(r2, 1e-4)

        def m(lx, ly, lz):
            if axis == "x": return (cx + lz, cy + ly, cz + lx)
            if axis == "y": return (cx + lx, cy + lz, cz + ly)
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

    def sphere(self, c, r, seg=14, rings=8):
        cx, cy, cz = c
        b = len(self.v)
        for j in range(rings + 1):
            th = math.pi * j / rings
            for i in range(seg):
                a = 2 * math.pi * i / seg
                self.v.append((cx + r * math.sin(th) * math.cos(a), cy + r * math.sin(th) * math.sin(a), cz + r * math.cos(th)))
        for j in range(rings):
            for i in range(seg):
                k = (i + 1) % seg
                self.f.append((b + j * seg + i, b + j * seg + k, b + (j + 1) * seg + k, b + (j + 1) * seg + i))

    def prism_roof(self, x0, x1, y0, y1, z0, z1):
        """gable roof along X: ridge at the middle of y0..y1, eave height z0, ridge height z1"""
        ym = (y0 + y1) / 2
        b = len(self.v)
        self.v += [(x0, y0, z0), (x1, y0, z0), (x1, ym, z1), (x0, ym, z1), (x0, y1, z0), (x1, y1, z0)]
        self.f += [(b, b + 1, b + 2, b + 3), (b + 3, b + 2, b + 5, b + 4), (b, b + 3, b + 4), (b + 1, b + 5, b + 2)]

    def build(self, name, mat, col, oy=0.0):
        me = bpy.data.meshes.new(name)
        me.from_pydata([(x, y + oy, z) for x, y, z in self.v], [], self.f)
        me.update()
        ob = bpy.data.objects.new(name, me)
        if mat:
            ob.data.materials.append(mat)
        col.objects.link(ob)
        return ob


# ------------------------------------------------------------------ materials (PBR-ish: roughness + bump)
def _bsdf(m):
    m.use_nodes = True
    return m.node_tree.nodes["Principled BSDF"]


def _bump(nt, b, src, strength=0.25, dist=0.05):
    bu = nt.nodes.new("ShaderNodeBump")
    bu.inputs["Strength"].default_value, bu.inputs["Distance"].default_value = strength, dist
    nt.links.new(src, bu.inputs["Height"])
    nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])


def _ramp(nt, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[1][0], (*stops[1][1], 1)
    for pos, c in stops[2:]:
        e = els.new(pos)
        e.color = (*c, 1)
    return r


def hexrgb(h):
    h = h.lstrip("#")
    lin = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


_cache = {}


def cached(key, fn):
    if key not in _cache or _cache[key].name not in bpy.data.materials:
        _cache[key] = fn()
    return _cache[key]


def mat_solid(name, hexcol, rough=0.7, emit=0.0, metal=0.0):
    def make():
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        b.inputs["Base Color"].default_value = (*hexrgb(hexcol), 1)
        b.inputs["Roughness"].default_value, b.inputs["Metallic"].default_value = rough, metal
        if emit > 0:
            b.inputs["Emission Color"].default_value = (*hexrgb(hexcol), 1)
            b.inputs["Emission Strength"].default_value = emit
        return m
    return cached(name, make)


def mat_glass(name="glassBall"):
    def make():
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        b.inputs["Base Color"].default_value = (0.75, 0.9, 1.0, 1)
        b.inputs["Roughness"].default_value = 0.05
        for k, v in (("Transmission Weight", 1.0), ("IOR", 1.45)):
            try:
                b.inputs[k].default_value = v
            except KeyError:
                pass
        return m
    return cached(name, make)


def mat_noise(name, stops, scale=4.0, rough=0.95, bump=0.25):
    def make():
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        nt = m.node_tree
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        r = _ramp(nt, stops)
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
        nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = rough
        _bump(nt, b, n.outputs["Fac"], bump)
        return m
    return cached(name, make)


def mat_stone(name="stoneWall"):
    def make():
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        nt = m.node_tree
        tc = nt.nodes.new("ShaderNodeTexCoord")
        v = nt.nodes.new("ShaderNodeTexVoronoi")
        v.voronoi_dimensions, v.feature = "3D", "DISTANCE_TO_EDGE"
        v.inputs["Scale"].default_value = 1.6
        r = _ramp(nt, [(0.0, (0.2, 0.2, 0.22)), (0.07, (0.62, 0.62, 0.6)), (1.0, (0.72, 0.72, 0.7))])
        nt.links.new(tc.outputs["Object"], v.inputs["Vector"])
        nt.links.new(v.outputs["Distance"], r.inputs["Fac"])
        nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.9
        _bump(nt, b, v.outputs["Distance"], 0.6, 0.08)
        return m
    return cached(name, make)


def mat_bands(name, stops, scale=2.5, distortion=6.0):
    def make():
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        nt = m.node_tree
        tc = nt.nodes.new("ShaderNodeTexCoord")
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type, w.bands_direction = "BANDS", "Z"
        w.inputs["Scale"].default_value, w.inputs["Distortion"].default_value = scale, distortion
        r = _ramp(nt, stops)
        nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
        nt.links.new(w.outputs["Fac"], r.inputs["Fac"])
        nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.9
        _bump(nt, b, w.outputs["Fac"], 0.3)
        return m
    return cached(name, make)


def M(name):
    t = {
        "wood": lambda: mat_solid("wood", "#7a4a26", 0.75), "iron": lambda: mat_solid("iron", "#3d414c", 0.45, metal=0.8),
        "steel": lambda: mat_solid("steel", "#9a9da6", 0.3, metal=1.0), "gravel": lambda: mat_solid("gravel", "#b59d86", 0.95),
        "plaster": lambda: mat_solid("plaster", "#e6d3b0", 0.9), "dark": lambda: mat_solid("dark", "#26212b", 0.8),
        "roof": lambda: mat_solid("roofRed", "#b5483a", 0.8), "trunk": lambda: mat_solid("trunk", "#59381d", 0.9),
        "leaf0": lambda: mat_solid("leaf0", "#5aa845", 0.85), "leaf1": lambda: mat_solid("leaf1", "#4f9a42", 0.85),
        "leaf2": lambda: mat_solid("leaf2", "#6bb64f", 0.85), "hill": lambda: mat_solid("hill", "#6fae56", 0.95),
        "mount": lambda: mat_solid("mount", "#7f93bd", 0.95), "gold": lambda: mat_solid("gold", "#e8b730", 0.28, metal=1.0),
        "paper": lambda: mat_solid("paper", "#f6f1e4", 0.9), "red": lambda: mat_solid("red", "#c8352f", 0.5),
        "green": lambda: mat_solid("boxGreen", "#2f8a4f", 0.6), "brown": lambda: mat_solid("bag", "#8d5a2b", 0.85),
        "parch": lambda: mat_solid("parch", "#e3c58d", 0.9), "orange": lambda: mat_solid("orange", "#f08a24", 0.5),
        "blue": lambda: mat_solid("blueCloth", "#1f4fc2", 0.8), "white": lambda: mat_solid("whiteCloth", "#f3f1e6", 0.8),
        "umbrella": lambda: mat_solid("umbrella", "#e8b53a", 0.7), "glassWin": lambda: mat_solid("glassWin", "#cfe8ff", 0.2, emit=3.0),
        "lampGlow": lambda: mat_solid("lampGlow", "#ffbf59", 0.3, emit=12.0), "wall": lambda: mat_solid("wallPaint", "#d8c2a6", 0.8),
        "grass": lambda: mat_noise("grass", [(0.0, (0.1, 0.34, 0.07)), (0.5, (0.2, 0.52, 0.11)), (1.0, (0.36, 0.66, 0.18))], 5.0),
        "grassDark": lambda: mat_noise("grassDark", [(0.0, (0.07, 0.25, 0.05)), (1.0, (0.2, 0.45, 0.1))], 6.0),
        "sand": lambda: mat_noise("sand", [(0.0, (0.62, 0.32, 0.17)), (0.55, (0.8, 0.5, 0.26)), (1.0, (0.9, 0.64, 0.36))], 5.0),
        "cobble": lambda: mat_noise("cobble", [(0.0, (0.28, 0.27, 0.3)), (0.5, (0.5, 0.48, 0.5)), (1.0, (0.62, 0.6, 0.58))], 14.0, 0.8, 0.6),
        "planks": lambda: mat_noise("planks", [(0.0, (0.28, 0.16, 0.08)), (1.0, (0.55, 0.34, 0.18))], 8.0, 0.65, 0.2),
        "stone": mat_stone,
        "cliff": lambda: mat_bands("cliff", [(0.0, (0.55, 0.12, 0.1)), (0.35, (0.9, 0.38, 0.12)), (0.65, (0.8, 0.2, 0.45)), (1.0, (1.0, 0.7, 0.25))]),
    }
    return t[name]()


def _n(x, y, z=0.0, s=0.08):
    return noise.noise(Vector((x * s, y * s, z)))


def _hash(i, s=0):
    v = math.sin(i * 127.1 + s * 311.7) * 43758.5453
    return v - math.floor(v)


def grid_mesh(name, nx, ny, sx, sy, zfunc, mat, col, origin=(0, 0, 0), plane="xy"):
    """ground ('xy', zfunc -> height) or a wall facing X ('yz', zfunc -> x offset)"""
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = (i / nx - 0.5) * sx, (j / ny - 0.5) * sy
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
    col.objects.link(ob)
    return ob


# ------------------------------------------------------------------ shared pieces
def ground(col, oy, mat, size=170, flat_r=9.0, hill=2.2):
    def z(u, v):
        d = math.hypot(u, v)
        return _n(u, v) * hill * max(0.0, min(1.0, (d - flat_r) / 25.0)) * 2.0
    grid_mesh("ground", 56, 56, size, size, z, mat, col, origin=(0, oy, 0))


def trees(col, oy, n, r0, r1, seed=1, clear_x=0.0):
    trunks, leaves = Geo(), [Geo(), Geo(), Geo()]
    for i in range(n):
        a, d = _hash(i, seed) * 6.283, r0 + _hash(i, seed + 3) * (r1 - r0)
        x, y = math.cos(a) * d, math.sin(a) * d
        if abs(x) < clear_x:
            continue
        h = 4.5 + _hash(i, seed + 7) * 4
        trunks.cone((x, y, 0), 0.25, 0.2, h * 0.42, 6)
        leaves[i % 3].cone((x, y, h * 0.3), h * 0.28, 0.05, h * 0.75, 7)
    trunks.build("trunks", M("trunk"), col, oy)
    for k, g in enumerate(leaves):
        g.build(f"leaves{k}", M(f"leaf{k}"), col, oy)


def hills(col, oy, ring=190, n=9):
    g, g2 = Geo(), Geo()
    for i in range(n):
        a, d, r = (i / n) * 6.283 + 0.4, ring + _hash(i, 5) * 60, 55 + _hash(i, 6) * 40
        (g if i % 3 else g2).cone((math.cos(a) * d, math.sin(a) * d, -3), r, 2, 26 + _hash(i, 8) * 22, 9)
    g.build("hills", M("hill"), col, oy)
    g2.build("mountains", M("mount"), col, oy)


def grass_tufts(col, oy, n=380, radius=9.0):
    g = Geo()
    for i in range(n):
        a, r = _hash(i, 11) * 6.283, radius * math.sqrt(_hash(i, 12))
        g.cone((math.cos(a) * r, math.sin(a) * r, 0), 0.07, 0.01, 0.25 + _hash(i, 13) * 0.3, 4)
    g.build("tufts", M("leaf2"), col, oy)


def house(g_wall, g_roof, g_trim, x, y, w, d, h, side):
    g_wall.box((x, y, h / 2), (w, d, h))
    g_roof.prism_roof(x - w / 2 - 0.3, x + w / 2 + 0.3, y - d / 2 - 0.3, y + d / 2 + 0.3, h, h + 2.2)
    g_trim.box((x - side * (w / 2 + 0.02), y, 1.0), (0.06, 1.0, 2.0))      # door facing the street
    for k in (-1, 1):
        g_trim.box((x - side * (w / 2 + 0.02), y + k * d * 0.3, h * 0.62), (0.06, 0.9, 1.0))


# ------------------------------------------------------------------ sets
def set_field(col, oy):
    ground(col, oy, M("grass"))
    path = Geo()
    path.box((0, 50, 0.02), (4.8, 220, 0.04))
    path.build("path", M("cobble"), col, oy)
    trees(col, oy, 46, 14, 120, 1, 4)
    hills(col, oy)
    grass_tufts(col, oy)


def set_fortress(col, oy):
    ground(col, oy, M("grass"))
    courtyard = Geo()
    courtyard.box((0, -3, 0.02), (32, 34, 0.04))
    courtyard.build("courtyard", M("cobble"), col, oy)
    wall, towers, roofs, gate, ban = Geo(), Geo(), Geo(), Geo(), Geo()
    wall.box((0, 14.9, 3.2), (68, 1.8, 6.4))
    for x in range(-33, 34, 2):
        wall.box((x, 14.9, 6.85), (1.2, 1.6, 0.9))
    for sx in (-34, 34):
        towers.cone((sx, 15, 0), 3.7, 3.4, 12, 16)
        roofs.cone((sx, 15, 12), 4.3, 0.05, 5.2, 16)
    gate.box((0, 14.0, 2.1), (3.8, 0.5, 4.2))
    wall.box((0, 14.9, 5.0), (4.6, 2.2, 0.8))
    for bx in (-9, -3.6, 3.6, 9):
        ban.box((bx, 13.95, 3.9), (1.4, 0.07, 3.4))
    wall.build("walls", M("stone"), col, oy)
    towers.build("towers", M("stone"), col, oy)
    roofs.build("roofs", M("roof"), col, oy)
    gate.build("gate", M("dark"), col, oy)
    ban.build("banners", M("blue"), col, oy)
    trees(col, oy, 22, 40, 120, 4, 8)
    hills(col, oy, 200, 8)


def set_canyon(col, oy):
    ground(col, oy, M("sand"), flat_r=14)
    bands = M("cliff")
    for side, w, hgt in ((1, 15.0, 26), (-1, 28.0, 14)):
        grid_mesh("cliff", 40, 14, 140, hgt, lambda u, v, s=side: _n(u, v, 3.0, 0.12) * 3.0 * s, bands, col, origin=(side * w, oy + 20, 0), plane="yz")
    ballast, sl, rails, poles = Geo(), Geo(), Geo(), Geo()
    ballast.box((0, 20, 0.12), (3.5, 140, 0.24))
    for yy in range(-48, 90):
        sl.box((0, yy * 0.7, 0.3), (2.5, 0.26, 0.12))
    for rx in (-0.74, 0.74):
        rails.box((rx, 20, 0.43), (0.1, 140, 0.14))
    for yy in range(-20, 80, 12):
        poles.box((3.7, yy, 3.1), (0.18, 0.18, 6.2))
        poles.box((3.7, yy, 5.8), (2.0, 0.14, 0.15))
    ballast.build("ballast", M("gravel"), col, oy)
    sl.build("sleepers", M("wood"), col, oy)
    rails.build("rails", M("steel"), col, oy)
    poles.build("poles", M("wood"), col, oy)
    mesas = Geo()
    for i in range(6):
        x0 = -300 + i * 120
        mesas.box((x0, 400 + _hash(i) * 60, 20 + _hash(i, 2) * 20), (70, 60, 40 + _hash(i, 2) * 40))
    mesas.build("mesas", M("cliff"), col, oy)


def set_interior(col, oy):
    floor, walls, wains, win, shelf = Geo(), Geo(), Geo(), Geo(), Geo()
    floor.box((0, 0, -0.05), (18, 18, 0.1))
    floor.build("floor", M("planks"), col, oy)
    walls.box((0, 7.2, 2.3), (18, 0.4, 4.6))
    walls.box((-9.2, 0, 2.3), (0.4, 18, 4.6))
    walls.box((9.2, 0, 2.3), (0.4, 18, 4.6))
    walls.build("walls", M("plaster"), col, oy)
    wains.box((0, 6.95, 0.55), (18, 0.12, 1.1))
    wains.build("wainscot", M("wood"), col, oy)
    win.box((4.5, 6.92, 2.6), (3.8, 0.1, 2.2))
    win.build("window", M("glassWin"), col, oy)
    shelf.box((-5.0, 6.5, 1.6), (3.0, 0.7, 3.2))
    shelf.build("shelf", M("wood"), col, oy)
    light = bpy.data.lights.new("roomLight", "POINT")      # the sun is blocked by the walls; the room carries its own light
    light.energy, light.color = 2200, (1.0, 0.85, 0.65)
    ob = bpy.data.objects.new("roomLight", light)
    ob.location = (0, oy - 1.0, 3.8)
    col.objects.link(ob)


def set_town(col, oy):
    ground(col, oy, M("grass"))
    street = Geo()
    street.box((0, 25, 0.02), (10, 190, 0.04))
    street.build("street", M("cobble"), col, oy)
    wall, roof, trim = Geo(), Geo(), Geo()
    for k in range(9):
        for s in (-1, 1):
            house(wall, roof, trim, s * (9.5 + _hash(k, s + 2) * 1.2), -26 + k * 9.5 + _hash(k, s) * 2, 6.5 + _hash(k, s + 4) * 2.5, 6.0, 6 + _hash(k, s + 8) * 3, s)
    wall.build("houses", M("wall"), col, oy)
    roof.build("roofs", M("roof"), col, oy)
    trim.build("trim", M("dark"), col, oy)
    trees(col, oy, 18, 45, 130, 6, 14)
    hills(col, oy, 210, 7)


SETS = {"field": set_field, "fortress": set_fortress, "canyon": set_canyon, "interior": set_interior, "town": set_town}
GROUND_Y = {"canyon": 0.36}


# ------------------------------------------------------------------ props + insert objects (per shot)
SPOTS = [(-3.4, 2.6), (3.6, 2.2), (-2.0, 4.6), (2.4, 5.2), (-5.2, 5.6)]


def build_props(col, oy, gy, names):
    for k, n in enumerate(names):
        x, y = SPOTS[k % len(SPOTS)]
        g = Geo()
        if n == "crate":
            g.box((x, y, gy + 0.45), (0.9, 0.9, 0.9), rz=0.2); mat = "wood"
        elif n == "barrel":
            g.cone((x, y, gy), 0.42, 0.42, 1.0, 12); mat = "wood"
        elif n == "table":
            g.box((x, y, gy + 0.75), (2.0, 1.0, 0.1))
            for dx in (-0.9, 0.9):
                for dy in (-0.4, 0.4):
                    g.box((x + dx, y + dy, gy + 0.37), (0.1, 0.1, 0.75))
            mat = "wood"
        elif n == "cart":
            g.box((x, y, gy + 0.7), (2.2, 1.3, 0.16), rz=0.3); g.box((x, y - 0.6, gy + 1.0), (2.2, 0.1, 0.5), rz=0.3)
            for dx in (-0.7, 0.7):
                for dy in (-0.72, 0.72):
                    g.cone((x + dx, y + dy - 0.05, gy + 0.46), 0.46, 0.46, 0.1, 14, axis="y")
            mat = "wood"
        elif n == "lamp":
            g.box((x, y, gy + 1.0), (0.08, 0.08, 2.0))
            g2 = Geo(); g2.box((x, y, gy + 2.15), (0.32, 0.32, 0.4)); g2.build(f"lampGlow{k}", M("lampGlow"), col, oy)
            mat = "iron"
        elif n == "umbrella":
            g.box((x, y, gy + 1.05), (0.06, 0.06, 2.1)); g2 = Geo(); g2.cone((x, y, gy + 2.1), 1.35, 0.05, 0.55, 12)
            g2.build(f"umb{k}", M("umbrella"), col, oy); mat = "iron"
        elif n == "tree":
            g.cone((x, y + 3, gy), 0.25, 0.2, 2.3, 6); g2 = Geo(); g2.cone((x, y + 3, gy + 1.6), 1.6, 0.05, 4.2, 8)
            g2.build(f"treeTop{k}", M("leaf0"), col, oy); mat = "trunk"
        else:
            g.box((x, y, gy + 0.4), (0.8, 0.8, 0.8)); mat = "wood"
        g.build(f"prop_{n}_{k}", M(mat), col, oy)


def build_focus(col, oy, gy, name):
    """insert-shot objects at the zone origin, seen from -Y; z is height above the surface (gy)"""
    def put(builder, mat):
        g = Geo(); builder(g); g.build(f"focus_{name}_{mat}", M(mat), col, oy)
    z0 = gy
    if name == "coin":
        def coins(g):
            for k in range(3): g.cone((k * 0.05, 0.04 * k, z0 + 0.003 + k * 0.037), 0.22, 0.22, 0.035, 28)
            g.cone((0.42, -0.1, z0 + 0.003), 0.22, 0.22, 0.035, 28)
        put(coins, "gold")
    elif name == "paper":
        put(lambda g: g.box((0, 0, z0 + 0.37), (0.5, 0.012, 0.72), ry=0.05), "paper")
    elif name == "calendar":
        put(lambda g: g.box((0, 0, z0 + 0.4), (0.62, 0.12, 0.8)), "green")
        put(lambda g: g.box((0, -0.07, z0 + 0.43), (0.5, 0.02, 0.56)), "paper")
        put(lambda g: g.box((0, -0.075, z0 + 0.64), (0.5, 0.025, 0.13)), "red")
    elif name == "newspaper":
        put(lambda g: g.box((0, 0, z0 + 0.42), (0.95, 0.012, 0.68), ry=-0.04), "paper")
        def cols(g):
            g.box((0, -0.01, z0 + 0.66), (0.8, 0.014, 0.1), ry=-0.04)
            for k in range(4): g.box((0.2 if k % 2 else -0.2, -0.01, z0 + 0.5 - (k // 2) * 0.1), (0.38, 0.014, 0.02), ry=-0.04)
        put(cols, "dark")
    elif name == "caliper":
        def jaws(g):
            g.box((0, 0, z0 + 0.55), (0.8, 0.04, 0.05)); g.box((-0.13, 0, z0 + 0.28), (0.045, 0.04, 0.5)); g.box((0.13, 0, z0 + 0.28), (0.045, 0.04, 0.5))
        put(jaws, "steel")
        put(lambda g: g.box((0.13, 0, z0 + 0.55), (0.14, 0.07, 0.11)), "iron")
    elif name == "thermometer":
        put(lambda g: g.cone((0, 0, z0 + 0.1), 0.05, 0.05, 0.9, 12), "paper")
        def liquid(g):
            g.cone((0, -0.01, z0 + 0.1), 0.028, 0.028, 0.6, 12); g.sphere((0, 0, z0 + 0.1), 0.1)
        put(liquid, "red")
        put(lambda g: [g.box((0.09, -0.04, z0 + 0.3 + k * 0.12), (0.09, 0.012, 0.012)) for k in range(6)], "dark")
    elif name == "moneybag":
        def bag(g):
            g.sphere((0, 0, z0 + 0.38), 0.38); g.cone((0, 0, z0 + 0.67), 0.2, 0.1, 0.22, 12)
        put(bag, "brown")
        def gold(g):
            g.box((0, 0, z0 + 0.7), (0.3, 0.3, 0.05)); g.cone((0.55, -0.15, z0 + 0.003), 0.16, 0.16, 0.03, 20)
        put(gold, "gold")
    elif name == "map":
        put(lambda g: g.box((0, 0, z0 + 0.42), (1.0, 0.012, 0.7), ry=0.03), "parch")
        put(lambda g: [g.box((0.1, -0.01, z0 + 0.4), (0.4, 0.014, 0.05), ry=0.03 + s * math.pi / 4) for s in (1, -1)], "red")
    elif name == "clock":
        put(lambda g: g.cone((0, 0.02, z0 + 0.5), 0.44, 0.44, 0.07, 28, axis="y"), "iron")
        put(lambda g: g.cone((0, -0.05, z0 + 0.5), 0.39, 0.39, 0.07, 28, axis="y"), "paper")
        put(lambda g: [g.box((0.0, -0.1, z0 + 0.58), (0.03, 0.02, 0.26), ry=0.5), g.box((0.07, -0.105, z0 + 0.52), (0.03, 0.02, 0.34), ry=-1.1)], "dark")
    elif name == "marble":
        put(lambda g: g.sphere((0, 0, z0 + 0.18), 0.18, 20, 12), "glass")
        put(lambda g: g.box((0.6, 0.4, z0 + 0.15), (0.3, 0.3, 0.3)), "orange")
    else:
        put(lambda g: g.box((0, 0, z0 + 0.3), (0.6, 0.6, 0.6)), "wood")


# ------------------------------------------------------------------ module API used by blender_render.py
def build_scene(plan, cards_dir, cam, target, rig):
    shots = plan["shots"]
    zones, shot_cols = {}, {}
    root = bpy.context.scene.collection
    zone_of = {}
    for s in shots:
        zone_of.setdefault(s["set"], s["zone"])
    for name, zi in zone_of.items():
        col = bpy.data.collections.new(f"Zone_{zi}_{name}")
        root.children.link(col)
        zones[zi] = col
        SETS.get(name, set_field)(col, ZONE_DZ * zi)
    for s in shots:
        if not (s.get("props") or s.get("focus")):
            continue
        zi, col = s["zone"], bpy.data.collections.new(f"Shot_{s['id']}")
        zones[zi].children.link(col)
        shot_cols[s["id"]] = col
        gy = GROUND_Y.get(s["set"], 0.0)
        build_props(col, ZONE_DZ * zi, gy, s.get("props", []))
        if s.get("focus"):
            build_focus(col, ZONE_DZ * zi, gy, s["focus"])
    return {"zones": zones, "shot_cols": shot_cols, "shots": shots, "last": None}


def update_frame(fr, scene, cam, target, state):
    cur = next((s for s in state["shots"] if s["a"] <= fr < s["b"]), state["shots"][-1])
    key = cur["id"]
    if state["last"] == key:
        return
    state["last"] = key
    for zi, col in state["zones"].items():
        col.hide_render = col.hide_viewport = (zi != cur["zone"])
    for sid, col in state["shot_cols"].items():
        col.hide_render = col.hide_viewport = (sid != key)
