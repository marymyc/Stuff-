import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { ctex, facadeHD, rep, rng, roofHD, stoneHD } from "./paint";
import { twoTone } from "./shade";

export const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

const mats = new Map<string, THREE.Material>();
export const lam = (key: string, make: () => THREE.MeshLambertMaterialParameters) => {
  let m = mats.get(key) as THREE.MeshLambertMaterial | undefined;
  if (!m) {
    m = twoTone(new THREE.MeshLambertMaterial(make()));
    mats.set(key, m);
  }
  return m;
};

const f32 = (a: THREE.BufferAttribute | THREE.InterleavedBufferAttribute) => {
  const out = new Float32Array(a.count * a.itemSize);
  for (let i = 0; i < a.count; i++) for (let k = 0; k < a.itemSize; k++) out[i * a.itemSize + k] = a.getComponent(i, k);
  return new THREE.Float32BufferAttribute(out, a.itemSize);
};

export const quad = (
  a: THREE.Vector3,
  b: THREE.Vector3,
  c: THREE.Vector3,
  d: THREE.Vector3,
  u1 = 1,
  v1 = 1,
  u0 = 0,
  v0 = 0
) => {
  const g = new THREE.BufferGeometry();
  const n = new THREE.Vector3().subVectors(b, a).cross(new THREE.Vector3().subVectors(d, a)).normalize();
  g.setAttribute("position", new THREE.Float32BufferAttribute([a, b, c, a, c, d].flatMap((v) => [v.x, v.y, v.z]), 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 2, 3, 4, 5].flatMap(() => [n.x, n.y, n.z]), 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute([u0, v0, u1, v0, u1, v1, u0, v0, u1, v1, u0, v1], 2));
  return g;
};

export const tri = (a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3) => {
  const g = new THREE.BufferGeometry();
  const n = new THREE.Vector3().subVectors(b, a).cross(new THREE.Vector3().subVectors(c, a)).normalize();
  g.setAttribute("position", new THREE.Float32BufferAttribute([a, b, c].flatMap((v) => [v.x, v.y, v.z]), 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 2].flatMap(() => [n.x, n.y, n.z]), 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute([0, 0, 1, 0, 0.5, 1], 2));
  return g;
};

export const boxGeo = (min: THREE.Vector3, max: THREE.Vector3, tile = 0, bottom = false) => {
  const [x0, y0, z0] = [min.x, min.y, min.z];
  const [x1, y1, z1] = [max.x, max.y, max.z];
  const t = (a: number) => (tile ? a / tile : 1);
  const w = x1 - x0;
  const h = y1 - y0;
  const d = z1 - z0;
  const faces = [
    quad(V(x0, y0, z1), V(x1, y0, z1), V(x1, y1, z1), V(x0, y1, z1), t(w), t(h)),
    quad(V(x1, y0, z0), V(x0, y0, z0), V(x0, y1, z0), V(x1, y1, z0), t(w), t(h)),
    quad(V(x0, y0, z0), V(x0, y0, z1), V(x0, y1, z1), V(x0, y1, z0), t(d), t(h)),
    quad(V(x1, y0, z1), V(x1, y0, z0), V(x1, y1, z0), V(x1, y1, z1), t(d), t(h)),
    quad(V(x0, y1, z1), V(x1, y1, z1), V(x1, y1, z0), V(x0, y1, z0), t(w), t(d)),
  ];
  if (bottom) faces.push(quad(V(x0, y0, z0), V(x1, y0, z0), V(x1, y0, z1), V(x0, y0, z1), t(w), t(d)));
  return mergeGeometries(faces, false);
};

export class Batch {
  private g = new Map<THREE.Material, THREE.BufferGeometry[]>();
  add(geo: THREE.BufferGeometry, mat: THREE.Material, m?: THREE.Matrix4) {
    const src = geo.index ? geo.toNonIndexed() : geo;
    const x = new THREE.BufferGeometry();
    x.setAttribute("position", f32(src.attributes.position));
    if (src.attributes.normal) x.setAttribute("normal", f32(src.attributes.normal));
    else x.computeVertexNormals();
    x.setAttribute(
      "uv",
      src.attributes.uv ? f32(src.attributes.uv) : new THREE.Float32BufferAttribute(new Float32Array(src.attributes.position.count * 2), 2)
    );
    if (m) x.applyMatrix4(m);
    const l = this.g.get(mat);
    if (l) l.push(x);
    else this.g.set(mat, [x]);
  }
  build(parent: THREE.Object3D, cast = true) {
    for (const [mat, list] of this.g) {
      const mesh = new THREE.Mesh(mergeGeometries(list, false), mat);
      mesh.castShadow = cast;
      mesh.receiveShadow = true;
      mesh.matrixAutoUpdate = false;
      parent.add(mesh);
    }
    this.g.clear();
  }
}

// ---------------- Cartoon vegetation (painted spheres + tapered trunks) ----------------
const LEAF = ["#5aa83c", "#4c9a37", "#69b545", "#55a243", "#3f8f3c"];
const leafTex = (i: number) =>
  ctex("leafHD_" + i, 256, 128, (g, r) => {
    const base = new THREE.Color(LEAF[i % LEAF.length]);
    const top = base.clone().offsetHSL(0.012, 0.03, 0.08);
    const bot = base.clone().offsetHSL(-0.015, 0, -0.08);
    const gr = g.createLinearGradient(0, 0, 0, 128);
    gr.addColorStop(0, "#" + top.getHexString());
    gr.addColorStop(0.42, "#" + base.getHexString());
    gr.addColorStop(1, "#" + bot.getHexString());
    g.fillStyle = gr;
    g.fillRect(0, 0, 256, 128);
    for (let k = 0; k < 42; k++) {
      const x = r() * 256;
      const y = 10 + r() * 108;
      const rad = 5 + r() * 9;
      const light = y < 64 ? r() < 0.7 : r() < 0.25;
      for (const ox of [-256, 0, 256]) {
        g.strokeStyle = light ? "rgba(225,255,170,0.22)" : "rgba(20,70,30,0.2)";
        g.lineWidth = 2.5;
        g.lineCap = "round";
        g.beginPath();
        g.arc(x + ox, y + rad * 0.6, rad, Math.PI * 1.15, Math.PI * 1.85);
        g.stroke();
      }
    }
  });

const lobeGeoCache: THREE.BufferGeometry[] = [];
const lobeGeo = (q: number) => {
  if (!lobeGeoCache[q]) {
    lobeGeoCache[q] = new THREE.SphereGeometry(1, [18, 12][q], [12, 8][q]);
  }
  return lobeGeoCache[q];
};
let trunkGeoCache: THREE.BufferGeometry | null = null;
const trunkGeo = () => (trunkGeoCache ??= new THREE.CylinderGeometry(0.55, 1, 1, 10, 1, true).translate(0, 0.5, 0));

export type TreeKind = "round" | "tall" | "bush";
export const addCartoonVeg = (b: Batch, kind: TreeKind, x: number, y: number, z: number, h: number, seed: number, q = 0) => {
  const r = rng(Math.abs(Math.floor(seed)) % 200000 + 13);
  const U = (a: number, c: number) => a + (c - a) * r();
  const leaf = lam("leafHD" + (Math.floor(r() * 4) % 4), () => ({ map: leafTex(Math.floor(r() * 4)) }));
  const bark = lam("barkHD", () => ({ color: "#8f5d3b" }));
  const lobe = lobeGeo(q);
  const yaw = r() * Math.PI * 2;
  const put = (px: number, py: number, pz: number, rad: number, sy = 0.9) =>
    b.add(
      lobe,
      leaf,
      new THREE.Matrix4().compose(
        V(x + px, y + py, z + pz),
        new THREE.Quaternion().setFromAxisAngle(V(0, 1, 0), r() * Math.PI * 2),
        V(rad, rad * sy, rad)
      )
    );
  const trunk = (th: number, tr: number) =>
    b.add(
      trunkGeo(),
      bark,
      new THREE.Matrix4().compose(V(x, y - 0.1, z), new THREE.Quaternion().setFromAxisAngle(V(0, 1, 0), yaw), V(tr, th + 0.1, tr))
    );

  if (kind === "bush") {
    put(0, 0.44 * h, 0, 0.48 * h);
    for (let i = 0; i < 3; i++) {
      const a = yaw + (i * Math.PI * 2) / 3;
      put(Math.cos(a) * 0.38 * h, 0.3 * h, Math.sin(a) * 0.38 * h, 0.34 * h);
    }
    return;
  }
  if (kind === "tall") {
    trunk(0.36 * h, 0.048 * h);
    put(0, 0.5 * h, 0, 0.18 * h, 1.3);
    put(U(-0.04, 0.04) * h, 0.68 * h, U(-0.04, 0.04) * h, 0.15 * h, 1.3);
    put(0, 0.84 * h, 0, 0.11 * h, 1.2);
    return;
  }
  trunk(0.46 * h, 0.055 * h);
  const cy = 0.64 * h;
  put(0, cy, 0, 0.27 * h);
  for (let i = 0; i < 4; i++) {
    const a = yaw + (i * Math.PI * 2) / 4 + U(-0.3, 0.3);
    const dd = 0.19 * h * U(0.88, 1.12);
    put(Math.cos(a) * dd, cy - 0.05 * h + U(-0.04, 0.04) * h, Math.sin(a) * dd, U(0.17, 0.21) * h);
  }
  put(U(-0.04, 0.04) * h, cy + 0.17 * h, U(-0.04, 0.04) * h, 0.18 * h);
};

// ---------------- Chicago lakefront / park townhouses & apartments ----------------
const CITY_STYLES = [
  { wall: "#ecdab2", shutter: "#3f6fb5", roof: "#d27a62", brick: true },
  { wall: "#d8a95f", shutter: "#2f6a43", roof: "#b8644f" },
  { wall: "#c47a5c", shutter: "#2f5f6a", roof: "#8f97a8", brick: true },
  { wall: "#e2c49a", shutter: "#8c3b4a", roof: "#c9775a" },
  { wall: "#cc9a6c", shutter: "#3f6fb5", roof: "#8e7aa0", brick: true },
];

export const addTownBuilding = (
  b: Batch,
  x: number,
  y: number,
  z: number,
  yaw: number,
  w: number,
  d: number,
  h: number,
  si: number
) => {
  const st = CITY_STYLES[si % CITY_STYLES.length];
  const m = new THREE.Matrix4().makeRotationY(yaw).setPosition(x, y, z);
  const front = lam(`cf_${si}_${w}_${h}`, () => ({ map: facadeHD(`cf_${si}_${w}_${h}`, w, h, { ...st, door: true }) }));
  const side = lam(`cs_${si}_${d}_${h}`, () => ({ map: facadeHD(`cs_${si}_${d}_${h}`, d, h, st) }));
  const hw = w / 2;
  const hd = d / 2;
  b.add(quad(V(-hw, 0, hd), V(hw, 0, hd), V(hw, h, hd), V(-hw, h, hd)), front, m);
  b.add(quad(V(hw, 0, -hd), V(-hw, 0, -hd), V(-hw, h, -hd), V(hw, h, -hd)), side, m);
  b.add(quad(V(-hw, 0, -hd), V(-hw, 0, hd), V(-hw, h, hd), V(-hw, h, -hd)), side, m);
  b.add(quad(V(hw, 0, hd), V(hw, 0, -hd), V(hw, h, -hd), V(hw, h, hd)), side, m);

  // Architectural stone cornice, plinth, and pitched/parapet roof
  const trim = lam("bldgTrim", () => ({ map: stoneHD("copeHD") }));
  const roof = lam("bldgRoof_" + st.roof, () => ({ map: roofHD(st.roof, st.roof === "#8f97a8"), side: THREE.DoubleSide }));
  b.add(boxGeo(V(-hw - 0.16, h - 0.18, -hd - 0.16), V(hw + 0.16, h + 0.28, hd + 0.16), 2, true), trim, m);
  b.add(boxGeo(V(-hw - 0.1, 0, -hd - 0.1), V(hw + 0.1, 0.55, hd + 0.1), 2, false), trim, m);
  // Hip cap roof on city mid-rises
  const rh = Math.min(3.4, d * 0.28);
  b.add(quad(V(-hw, h + 0.28, hd), V(hw, h + 0.28, hd), V(hw * 0.78, h + 0.28 + rh, 0), V(-hw * 0.78, h + 0.28 + rh, 0), 2, 1), roof, m);
  b.add(quad(V(hw, h + 0.28, -hd), V(-hw, h + 0.28, -hd), V(-hw * 0.78, h + 0.28 + rh, 0), V(hw * 0.78, h + 0.28 + rh, 0), 2, 1), roof, m);
  b.add(
    boxGeo(V(-hw * 0.6, h + 0.28, -hd * 0.3), V(-hw * 0.6 + 0.85, h + 0.28 + rh + 0.9, -hd * 0.3 + 0.85), 2),
    lam("bldgChim", () => ({ map: rep(stoneHD("wallHD"), 1, 1) })),
    m
  );
};
