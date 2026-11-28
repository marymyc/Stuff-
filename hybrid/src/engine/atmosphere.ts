import * as THREE from "three";
import { Batch, lam } from "./buildHelper";
import { NOINK } from "./ink";

const makeMoteTex = () => {
  const cv = document.createElement("canvas");
  cv.width = cv.height = 64;
  const g = cv.getContext("2d")!;
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 30);
  gr.addColorStop(0, "rgba(255,250,230,0.95)");
  gr.addColorStop(0.45, "rgba(255,244,210,0.45)");
  gr.addColorStop(1, "rgba(255,240,200,0)");
  g.fillStyle = gr;
  g.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
};

/**
 * Floating ambient dust / pollen / warm ember motes placed on NOINK layer.
 * Uses deterministic seeded oscillation so frames are 100% reproducible.
 */
export class DustField {
  points: THREE.Points;
  private base: Float32Array;
  private phases: Float32Array;
  private count: number;

  constructor(
    parent: THREE.Object3D,
    opts: { count?: number; center?: [number, number, number]; span?: [number, number, number]; color?: string; size?: number; seed?: number } = {}
  ) {
    const count = opts.count ?? 90;
    const [cx, cy, cz] = opts.center ?? [0, 2.2, 0];
    const [sx, sy, sz] = opts.span ?? [14, 4.5, 16];
    const seed = opts.seed ?? 7;

    this.count = count;
    this.base = new Float32Array(count * 3);
    this.phases = new Float32Array(count);
    const pos = new Float32Array(count * 3);

    const rnd = (i: number, k: number) => {
      const v = Math.sin((i + 1) * 78.233 + seed * 19.7 + k * 41.3) * 43758.5453;
      return v - Math.floor(v);
    };

    for (let i = 0; i < count; i++) {
      const x = cx + (rnd(i, 0) - 0.5) * sx;
      const y = cy + (rnd(i, 1) - 0.5) * sy;
      const z = cz + (rnd(i, 2) - 0.5) * sz;
      this.base[i * 3] = pos[i * 3] = x;
      this.base[i * 3 + 1] = pos[i * 3 + 1] = y;
      this.base[i * 3 + 2] = pos[i * 3 + 2] = z;
      this.phases[i] = rnd(i, 3) * Math.PI * 2;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      map: makeMoteTex(),
      color: opts.color ?? "#fff3cc",
      size: opts.size ?? 0.12,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    this.points = new THREE.Points(geo, mat);
    this.points.layers.set(NOINK);
    this.points.frustumCulled = false;
    parent.add(this.points);
  }

  update(tSec: number, visible = true) {
    this.points.visible = visible;
    if (!visible) return;
    const attr = this.points.geometry.getAttribute("position") as THREE.BufferAttribute;
    const arr = attr.array as Float32Array;
    for (let i = 0; i < this.count; i++) {
      const ph = this.phases[i];
      arr[i * 3] = this.base[i * 3] + 0.14 * Math.sin(tSec * 0.65 + ph);
      arr[i * 3 + 1] = this.base[i * 3 + 1] + 0.18 * Math.sin(tSec * 0.48 + ph * 1.3);
      arr[i * 3 + 2] = this.base[i * 3 + 2] + 0.12 * Math.cos(tSec * 0.55 + ph * 0.8);
    }
    attr.needsUpdate = true;
  }
}

/** Soft low-angle sunlight shaft cones placed on NOINK layer for volumetric atmosphere. */
export class LightShafts {
  group = new THREE.Group();
  private mats: THREE.MeshBasicMaterial[] = [];

  constructor(
    parent: THREE.Object3D,
    specs: { pos: [number, number, number]; rot: [number, number, number]; length?: number; radius?: number; color?: string; opacity?: number }[]
  ) {
    for (const s of specs) {
      const len = s.length ?? 9;
      const rad = s.radius ?? 1.4;
      const geo = new THREE.ConeGeometry(rad, len, 18, 1, true);
      geo.translate(0, -len * 0.5, 0);
      const mat = new THREE.MeshBasicMaterial({
        color: s.color ?? "#ffe0a8",
        transparent: true,
        opacity: s.opacity ?? 0.085,
        depthWrite: false,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(...s.pos);
      mesh.rotation.set(...s.rot);
      mesh.layers.set(NOINK);
      mesh.frustumCulled = false;
      this.group.add(mesh);
      this.mats.push(mat);
    }
    parent.add(this.group);
  }

  setVisible(visible: boolean, intensity = 1) {
    this.group.visible = visible;
    for (const m of this.mats) {
      m.opacity = 0.085 * intensity;
    }
  }
}

/** Deterministic faceted 3D gravel pebbles & tuft scatter so terrain reads richly up close. */
export function addGroundScatter(
  batch: Batch,
  opts: { count?: number; xRange?: [number, number]; zRange?: [number, number]; y?: number; colors?: string[]; scale?: number; seed?: number } = {}
) {
  const count = opts.count ?? 60;
  const [x0, x1] = opts.xRange ?? [-12, 12];
  const [z0, z1] = opts.zRange ?? [-28, 12];
  const yBase = opts.y ?? 0;
  const cols = opts.colors ?? ["#7e6d5d", "#66594c", "#8f7d68", "#576846"];
  const baseScale = opts.scale ?? 1.0;
  const seed = opts.seed ?? 13;

  const rnd = (i: number, k: number) => {
    const v = Math.sin((i + 1) * 91.7 + seed * 37.3 + k * 17.9) * 43758.5453;
    return v - Math.floor(v);
  };

  const mats = cols.map((col, idx) => lam(`pebble_${seed}_${idx}`, () => ({ color: col })));
  const rockGeo = new THREE.DodecahedronGeometry(0.11 * baseScale, 0);

  for (let i = 0; i < count; i++) {
    const x = x0 + rnd(i, 0) * (x1 - x0);
    const z = z0 + rnd(i, 1) * (z1 - z0);
    const sx = 0.7 + 1.2 * rnd(i, 2);
    const sy = 0.45 + 0.55 * rnd(i, 3);
    const sz = 0.7 + 1.1 * rnd(i, 4);
    const ry = rnd(i, 5) * Math.PI * 2;
    const g = rockGeo.clone();
    g.scale(sx, sy, sz);
    g.rotateY(ry);
    g.translate(x, yBase + 0.03 * baseScale * sy, z);
    batch.add(g, mats[i % mats.length]);
  }
}
