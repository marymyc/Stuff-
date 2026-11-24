// Generic 3D sets (painted textures + the look pipeline's ink/blur/grade make even simple geometry read in-style).
// Every set is built around the origin (where the cast stands); ground at y = 0; camera sits on the -z side.
import * as THREE from "three";
import { Batch, boxGeo, V, lam, house } from "../videos/bridge/build";
import { grassHD, cobbleHD, stoneHD, planks, beamHD, roofHD, ctex } from "../videos/bridge/paint";

const M = {
  grass: () => lam("grassHD", () => ({ map: grassHD() })),
  cobble: () => lam("cobbleHD", () => ({ map: cobbleHD() })),
  stone: () => lam("wallHD", () => ({ map: stoneHD("wallHD", ["#c9bcaa", "#bfb19f", "#d1c5b4", "#b8aa97"], "#958776") })),
  planks: () => lam("planksFloor", () => ({ map: planks() })),
  wood: () => lam("beamHD", () => ({ map: beamHD() })),
  roof: () => lam("roofRedHD", () => ({ map: roofHD("#b5483a") })),
  sand: () => lam("sandHD", () => ({ map: sandTex() })),
  cliff: () => lam("cliffHD", () => ({ map: cliffTex() })),
  iron: () => lam("ironC", () => ({ color: "#3d414c" })),
  steel: () => lam("steelC", () => ({ color: "#8a8d96" })),
  gravel: () => lam("gravelC", () => ({ color: "#b59d86" })),
  plaster: () => lam("plasterC", () => ({ color: "#e6d3b0" })),
  dark: () => lam("darkC", () => ({ color: "#26212b" })),
  leaf: (k: number) => lam(`leaf${k}`, () => ({ color: ["#5aa845", "#4f9a42", "#6bb64f"][k % 3] })),
  hill: () => lam("hillC", () => ({ color: "#6fae56" })),
  mount: () => lam("mountC", () => ({ color: "#7f93bd" })),
  cloth: (hex: string) => lam(`cloth${hex}`, () => ({ color: hex, side: THREE.DoubleSide })),
  gold: () => lam("goldC", () => ({ color: "#e8b730" })),
  paper: () => lam("paperC", () => ({ color: "#f6f1e4", side: THREE.DoubleSide })),
  red: () => lam("redC", () => ({ color: "#c8352f" })),
  green: () => lam("boxGreenC", () => ({ color: "#2f8a4f" })),
  brown: () => lam("bagC", () => ({ color: "#8d5a2b" })),
  parch: () => lam("parchC", () => ({ color: "#e3c58d", side: THREE.DoubleSide })),
  orange: () => lam("orangeC", () => ({ color: "#f08a24" })),
  glass: () => lam("glassC", () => ({ color: "#cfe8ff", emissive: "#9fc8f0", emissiveIntensity: 0.9 })),
};

const sandTex = () => ctex("sandHD", 512, 512, (g, r) => {
  g.fillStyle = "#e3b67c"; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 3200; i++) {
    g.globalAlpha = 0.45; g.fillStyle = r() < 0.5 ? "#d49c62" : "#f0cb98";
    g.beginPath(); g.arc(r() * 512, r() * 512, 1 + r() * 3.2, 0, 6.283); g.fill();
  }
  g.globalAlpha = 1;
});
const cliffTex = () => ctex("cliffBands", 512, 512, (g, r) => {
  const cols = ["#a63c2e", "#d9682f", "#e9944a", "#b84a6a", "#7d3a52", "#f2b35c", "#c24f36"];
  let y = 0;
  while (y < 512) { const h = 16 + r() * 46; g.fillStyle = cols[Math.floor(r() * cols.length)]; g.fillRect(0, y, 512, h); y += h; }
  for (let i = 0; i < 90; i++) { g.globalAlpha = 0.22; g.fillStyle = r() < 0.5 ? "#40201f" : "#ffd9a0"; g.fillRect(r() * 512, r() * 512, 2 + r() * 5, 20 + r() * 90); }
  g.globalAlpha = 1;
});

/** horizontal quad facing up, x0..x1, z0..z1 (z0 < z1) */
const flat = (x0: number, x1: number, z0: number, z1: number, y: number, u: number, v: number) => {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([x0, y, z1, x1, y, z1, x1, y, z0, x0, y, z1, x1, y, z0, x0, y, z0], 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute([0, 0, u, 0, u, v, 0, 0, u, v, 0, v], 2));
  return g;
};
const hash = (i: number, s = 0) => { const v = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return v - Math.floor(v); };
const T = (x: number, y: number, z: number) => new THREE.Matrix4().makeTranslation(x, y, z);

const tree = (b: Batch, x: number, z: number, h: number, k: number) => {
  const w = 0.16 * h / 4;
  b.add(boxGeo(V(x - w, 0, z - w), V(x + w, h * 0.42, z + w)), M.wood());
  b.add(new THREE.ConeGeometry(h * 0.26, h * 0.62, 8), M.leaf(k), T(x, h * 0.42 + h * 0.31, z));
  b.add(new THREE.ConeGeometry(h * 0.19, h * 0.46, 8), M.leaf(k + 1), T(x, h * 0.42 + h * 0.62, z));
};
const trees = (b: Batch, n: number, r0: number, r1: number, seed = 1, clearX = 0) => {
  for (let i = 0; i < n; i++) {
    const a = hash(i, seed) * 6.283, d = r0 + hash(i, seed + 3) * (r1 - r0);
    const x = Math.cos(a) * d, z = Math.sin(a) * d;
    if (Math.abs(x) < clearX) continue;
    tree(b, x, z, 4.5 + hash(i, seed + 7) * 4, i);
  }
};
const hills = (b: Batch, ring = 190, n = 9) => {
  for (let i = 0; i < n; i++) {
    const a = (i / n) * 6.283 + 0.4, d = ring + hash(i, 5) * 60, r = 55 + hash(i, 6) * 40;
    b.add(new THREE.ConeGeometry(r, 26 + hash(i, 8) * 22, 9), i % 3 ? M.hill() : M.mount(), T(Math.cos(a) * d, 12, Math.sin(a) * d));
  }
};

const field = (b: Batch) => {
  b.add(flat(-700, 700, -700, 700, 0, 350, 350), M.grass());
  b.add(flat(-2.4, 2.4, -60, 160, 0.02, 1.2, 80), M.cobble());   // a path through the meadow
  trees(b, 46, 14, 120, 1, 4);
  hills(b);
};

const fortress = (b: Batch) => {
  b.add(flat(-700, 700, -700, 700, 0, 350, 350), M.grass());
  b.add(flat(-16, 16, -20, 14, 0.02, 8, 17), M.cobble());        // courtyard
  const stone = M.stone();
  b.add(boxGeo(V(-34, 0, 14), V(34, 6.4, 15.8), 2), stone);       // curtain wall
  for (let x = -33.4; x < 33; x += 2.2) b.add(boxGeo(V(x, 6.4, 14.1), V(x + 1.2, 7.3, 15.7), 2), stone);
  for (const sx of [-34, 34]) {
    b.add(new THREE.CylinderGeometry(3.4, 3.7, 12, 16), stone, T(sx, 6, 15));
    b.add(new THREE.ConeGeometry(4.3, 5.2, 16), M.roof(), T(sx, 14.6, 15));
  }
  b.add(boxGeo(V(-1.9, 0, 13.7), V(1.9, 4.2, 14.2)), M.dark());   // gate
  b.add(boxGeo(V(-2.3, 4.2, 13.6), V(2.3, 5.0, 15.9), 2), stone);
  for (const bx of [-9, -3.6, 3.6, 9]) {
    b.add(boxGeo(V(bx - 0.7, 2.2, 13.55), V(bx + 0.7, 5.6, 13.62)), M.cloth("#1f4fc2"));
    b.add(boxGeo(V(bx - 0.28, 3.5, 13.5), V(bx + 0.28, 4.6, 13.54)), M.cloth("#f3f1e6"));
  }
  trees(b, 22, 40, 120, 4, 8);
  hills(b, 200, 8);
};

const canyon = (b: Batch) => {
  b.add(flat(-700, 700, -300, 400, 0, 120, 120), M.sand());
  b.add(boxGeo(V(-1.75, 0, -80), V(1.75, 0.24, 260)), M.gravel());                       // ballast
  for (let z = -78; z < 258; z += 0.72) b.add(boxGeo(V(-1.25, 0.24, z), V(1.25, 0.36, z + 0.26), 1), M.wood());
  for (const rx of [-0.74, 0.74]) b.add(boxGeo(V(rx - 0.05, 0.36, -80), V(rx + 0.05, 0.5, 260)), M.steel());
  for (let z = -60; z < 250; z += 26) {                                                    // telegraph poles
    b.add(boxGeo(V(3.6, 0, z), V(3.78, 6.2, z + 0.18)), M.wood());
    b.add(boxGeo(V(2.7, 5.7, z - 0.04), V(4.7, 5.85, z + 0.22)), M.wood());
  }
  const cl = M.cliff();
  b.add(boxGeo(V(16, 0, -120), V(70, 30, 300), 9), cl);
  b.add(boxGeo(V(-90, 0, -120), V(-26, 16, 300), 9), cl);
  for (let i = 0; i < 6; i++) b.add(boxGeo(V(-300 + i * 120, 0, 380 + hash(i) * 60), V(-230 + i * 120, 40 + hash(i, 2) * 40, 440 + hash(i) * 60), 9), cl);
};

const interior = (b: Batch) => {
  b.add(flat(-9, 9, -9, 9, 0, 9, 9), M.planks());
  const w = M.plaster();
  b.add(boxGeo(V(-9, 0, 7), V(9, 4.6, 7.4)), w);
  b.add(boxGeo(V(-9.4, 0, -9), V(-9, 4.6, 7.4)), w);
  b.add(boxGeo(V(9, 0, -9), V(9.4, 4.6, 7.4)), w);
  b.add(boxGeo(V(-9, 0, 6.9), V(9, 1.1, 7.0)), M.wood());                       // wainscot
  b.add(boxGeo(V(2.6, 1.5, 6.88), V(6.4, 3.7, 6.95)), M.glass());               // window
  b.add(boxGeo(V(2.45, 1.4, 6.82), V(2.6, 3.8, 6.9)), M.wood());
  b.add(boxGeo(V(6.4, 1.4, 6.82), V(6.55, 3.8, 6.9)), M.wood());
  b.add(boxGeo(V(-6.5, 0, 6.2), V(-3.5, 3.2, 6.9)), M.wood());                  // shelf unit
};

const town = (b: Batch) => {
  b.add(flat(-700, 700, -700, 700, 0, 350, 350), M.grass());
  b.add(flat(-5, 5, -70, 120, 0.02, 2.5, 95), M.cobble());
  for (let k = 0; k < 9; k++) for (const s of [-1, 1]) {
    const z = -26 + k * 9.5 + hash(k, s) * 2, w = 6.5 + hash(k, s + 4) * 2.5, h = 6 + hash(k, s + 8) * 3;
    house(b, s * (9.5 + hash(k, s + 2) * 1.2), z, s > 0 ? -Math.PI / 2 : Math.PI / 2, w, 6, h, k + (s > 0 ? 3 : 0), 0);
  }
  trees(b, 18, 45, 130, 6, 14);
  hills(b, 210, 7);
};

const SETS: Record<string, (b: Batch) => void> = { field, fortress, canyon, interior, town };

export const buildSet = (name: string): THREE.Group => {
  const g = new THREE.Group(), b = new Batch();
  (SETS[name] ?? SETS.field)(b);
  b.build(g);
  return g;
};

const PROP_SPOTS: [number, number][] = [[-3.4, 2.6], [3.6, 2.2], [-2.0, 4.6], [2.4, 5.2], [-5.2, 5.6]];
export const buildProps = (names: string[]): THREE.Group => {
  const g = new THREE.Group(), b = new Batch();
  names.forEach((n, k) => {
    const [x, z] = PROP_SPOTS[k % PROP_SPOTS.length];
    switch (n) {
      case "crate": b.add(boxGeo(V(x - 0.45, 0, z - 0.45), V(x + 0.45, 0.9, z + 0.45), 1), M.wood()); break;
      case "barrel": b.add(new THREE.CylinderGeometry(0.42, 0.42, 1.0, 12), M.wood(), T(x, 0.5, z)); break;
      case "table": b.add(boxGeo(V(x - 1, 0.7, z - 0.5), V(x + 1, 0.8, z + 0.5), 1), M.wood());
        for (const dx of [-0.9, 0.9]) for (const dz of [-0.4, 0.4]) b.add(boxGeo(V(x + dx - 0.05, 0, z + dz - 0.05), V(x + dx + 0.05, 0.7, z + dz + 0.05)), M.wood()); break;
      case "cart": b.add(boxGeo(V(x - 1.1, 0.6, z - 0.65), V(x + 1.1, 0.78, z + 0.65), 1), M.wood());
        b.add(boxGeo(V(x - 1.1, 0.78, z - 0.65), V(x + 1.1, 1.2, z - 0.55), 1), M.wood());
        for (const dx of [-0.7, 0.7]) for (const dz of [-0.72, 0.72]) b.add(new THREE.CylinderGeometry(0.46, 0.46, 0.1, 14), M.wood(), new THREE.Matrix4().makeRotationX(Math.PI / 2).setPosition(x + dx, 0.46, z + dz)); break;
      case "lamp": b.add(boxGeo(V(x - 0.04, 0, z - 0.04), V(x + 0.04, 2.0, z + 0.04)), M.iron());
        b.add(boxGeo(V(x - 0.16, 2.0, z - 0.16), V(x + 0.16, 2.35, z + 0.16)), M.glass()); break;
      case "umbrella": b.add(boxGeo(V(x - 0.03, 0, z - 0.03), V(x + 0.03, 2.1, z + 0.03)), M.iron());
        b.add(new THREE.ConeGeometry(1.35, 0.55, 12), M.cloth("#e8b53a"), T(x, 2.35, z)); break;
      case "tree": tree(b, x, z + 3, 5.5, k); break;
      default: b.add(boxGeo(V(x - 0.4, 0, z - 0.4), V(x + 0.4, 0.8, z + 0.4), 1), M.wood());
    }
  });
  b.build(g);
  return g;
};

const RZ = (a: number, x: number, y: number, z: number) => new THREE.Matrix4().makeRotationZ(a).setPosition(x, y, z);
const bx = (w: number, h: number, d: number) => new THREE.BoxGeometry(w, h, d);

/** insert-shot objects: sit on the ground at the origin, ~0.3-0.9 m, built to be seen from the -z side */
export const buildFocus = (name: string): THREE.Group => {
  const g = new THREE.Group(), b = new Batch();
  switch (name) {
    case "coin":
      for (let k = 0; k < 3; k++) b.add(new THREE.CylinderGeometry(0.22, 0.22, 0.035, 28), M.gold(), T(k * 0.05, 0.02 + k * 0.037, 0.04 * k));
      b.add(new THREE.CylinderGeometry(0.22, 0.22, 0.035, 28), M.gold(), T(0.42, 0.02, -0.1));
      break;
    case "paper": b.add(bx(0.5, 0.72, 0.012), M.paper(), RZ(0.05, 0, 0.37, 0)); break;
    case "calendar":
      b.add(bx(0.62, 0.8, 0.12), M.green(), T(0, 0.4, 0));
      b.add(bx(0.5, 0.56, 0.02), M.paper(), T(0, 0.43, -0.07));
      b.add(bx(0.5, 0.13, 0.025), M.red(), T(0, 0.64, -0.075));
      break;
    case "newspaper": {
      b.add(bx(0.95, 0.68, 0.012), M.paper(), RZ(-0.04, 0, 0.42, 0));
      b.add(bx(0.8, 0.1, 0.014), M.dark(), RZ(-0.04, 0, 0.66, -0.01));
      for (let k = 0; k < 4; k++) b.add(bx(0.38, 0.02, 0.014), M.dark(), RZ(-0.04, (k % 2 ? 0.2 : -0.2), 0.5 - Math.floor(k / 2) * 0.1, -0.01));
      break;
    }
    case "caliper":
      b.add(bx(0.8, 0.05, 0.04), M.steel(), T(0, 0.55, 0));
      b.add(bx(0.045, 0.5, 0.04), M.steel(), T(-0.13, 0.28, 0));
      b.add(bx(0.045, 0.5, 0.04), M.steel(), T(0.13, 0.28, 0));
      b.add(bx(0.14, 0.11, 0.07), M.iron(), T(0.13, 0.55, 0));
      break;
    case "thermometer":
      b.add(new THREE.CylinderGeometry(0.05, 0.05, 0.9, 12), M.paper(), T(0, 0.55, 0));
      b.add(new THREE.CylinderGeometry(0.028, 0.028, 0.6, 12), M.red(), T(0, 0.4, -0.01));
      b.add(new THREE.SphereGeometry(0.1, 14, 10), M.red(), T(0, 0.1, 0));
      for (let k = 0; k < 6; k++) b.add(bx(0.09, 0.012, 0.012), M.dark(), T(0.09, 0.3 + k * 0.12, -0.04));
      break;
    case "moneybag":
      b.add(new THREE.SphereGeometry(0.38, 16, 12), M.brown(), T(0, 0.38, 0));
      b.add(new THREE.CylinderGeometry(0.1, 0.2, 0.22, 12), M.brown(), T(0, 0.78, 0));
      b.add(bx(0.3, 0.05, 0.3), M.gold(), T(0, 0.7, 0));
      b.add(new THREE.CylinderGeometry(0.16, 0.16, 0.03, 20), M.gold(), T(0.55, 0.02, -0.15));
      break;
    case "map":
      b.add(bx(1.0, 0.7, 0.012), M.parch(), RZ(0.03, 0, 0.42, 0));
      b.add(bx(0.4, 0.05, 0.014), M.red(), RZ(0.03 + Math.PI / 4, 0.1, 0.4, -0.01));
      b.add(bx(0.4, 0.05, 0.014), M.red(), RZ(0.03 - Math.PI / 4, 0.1, 0.4, -0.01));
      break;
    case "clock":
      b.add(new THREE.CylinderGeometry(0.44, 0.44, 0.07, 28), M.iron(), new THREE.Matrix4().makeRotationX(Math.PI / 2).setPosition(0, 0.5, 0.02));
      b.add(new THREE.CylinderGeometry(0.39, 0.39, 0.07, 28), M.paper(), new THREE.Matrix4().makeRotationX(Math.PI / 2).setPosition(0, 0.5, -0.02));
      b.add(bx(0.03, 0.26, 0.02), M.dark(), RZ(0.5, 0, 0.58, -0.06));
      b.add(bx(0.03, 0.34, 0.02), M.dark(), RZ(-1.1, 0.07, 0.52, -0.065));
      break;
    case "marble":
      b.add(new THREE.SphereGeometry(0.18, 20, 14), M.glass(), T(0, 0.18, 0));
      b.add(bx(0.3, 0.3, 0.3), M.orange(), T(0.6, 0.15, 0.4));
      break;
    default: b.add(bx(0.6, 0.6, 0.6), M.wood(), T(0, 0.3, 0));
  }
  b.build(g);
  return g;
};
