// Plan-driven story: shots, camera, light and flash all come from public/plan.json (written by tools/make_hybrid_plan.py).
// Coordinates are plan space [x, y_up, z]; Blender maps them to [x, -z, y]. Camera sits on +z and looks toward -z.
// Each location set lives in its own zone, 150 m apart along -z, so one Blender scene holds the whole short.
import plan from "../../public/plan.json";

export const FPS: number = (plan as { fps?: number }).fps ?? 30;
export const TOTAL: number = (plan as { totalFrames: number }).totalFrames;
export const FLASH_AT: number = (plan as { flashAt?: number }).flashAt ?? -1;
export const ENABLE_AUDIO = true;
export const SHOW_CAPTIONS = true;
export const ZONE_DZ = 150;

export type Light = "day" | "golden" | "interior" | "night";
export type ShotDef = { id: number; a: number; b: number; light: Light };
export type PlanShot = ShotDef & {
  set: string; zone: number; size: string; move: string; focus?: string;
  chars: { outfit: string; expr: string; x: number; z?: number; scale?: number; action?: string }[];
  props: string[]; fx: string[];
};
export const PLAN_SHOTS = (plan as unknown as { shots: PlanShot[] }).shots;
export const SHOTS: ShotDef[] = PLAN_SHOTS.map(({ id, a, b, light }) => ({ id, a, b, light }));
export const XFADE: { from: number; to: number; a: number; b: number }[] = [];

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (t: number) => { const u = clamp01(t); return u * u * (3 - 2 * u); };
export const smoother = (t: number) => { const u = clamp01(t); return u * u * u * (u * (u * 6 - 15) + 10); };
export const easeOut = (t: number) => 1 - (1 - clamp01(t)) ** 3;

export type V3 = [number, number, number];
export type CamSpec = { pos: V3; look: V3; fov: number; roll: number };

// [distance, height, vertical fov, focus height]. Wide framing (30-52 deg), camera >= 0.4 m above ground.
const SIZE: Record<string, [number, number, number, number]> = {
  wide_aerial: [38, 16, 52, 1.0], wide: [15, 2.4, 46, 1.3], medium: [6.2, 1.15, 40, 1.15],
  medium_low: [5.2, 0.8, 42, 1.35], close: [3.1, 1.1, 34, 1.45], macro: [1.8, 0.8, 30, 0.9],
};
const FOCUS: [number, number, number, number] = [1.15, 0.5, 30, 0.22];   // insert shots: tight, low, on an object at the zone origin
const GROUND_Y: Record<string, number> = { canyon: 0.36 };
const DOF_BY_SIZE: Record<string, number> = { wide_aerial: 0, wide: 3, medium: 6, medium_low: 6, close: 7, macro: 9 };

const shotOf = (id: number) => PLAN_SHOTS.find((s) => s.id === id) ?? PLAN_SHOTS[0];
const shotAtFrame = (f: number) => PLAN_SHOTS.find((s) => f >= s.a && f < s.b) ?? PLAN_SHOTS[PLAN_SHOTS.length - 1];
export const zoneZ = (zone: number) => -ZONE_DZ * zone;
export const groundY = (set: string) => GROUND_Y[set] ?? 0;

const kickAt = (f: number, f0: number, amp = 1) => {
  const k = f - f0;
  if (k < 0 || k > 7) return 0;
  return Math.cos(k * Math.PI * 0.9) * (1 - k / 7) * amp;
};

export const camAt = (id: number, f: number): CamSpec => {
  const s = shotOf(id), gy = groundY(s.set), z0 = zoneZ(s.zone);
  const [r, h0b, fov, fy0] = (s.focus ? FOCUS : SIZE[s.size]) ?? SIZE.medium;
  const h = h0b + gy, fy = fy0 + gy;
  const n = Math.max(1, s.b - s.a), u = smoother(clamp01((f - s.a) / Math.max(18, n * 0.8)));
  const creep = 1 - 0.0018 * Math.max(0, f - s.a - n * 0.5);
  const az0 = (s.id % 2 ? 1 : -1) * (s.size === "close" ? 0.12 : 0.3);
  let r0 = r, r1 = r, h0 = h, h1 = h, a0 = az0, a1 = az0, dx = 0, lz = 0, roll = 0;
  switch (s.move) {
    case "fly_forward": r1 = r * 0.42; h1 = h * 0.28; lz = 5; break;
    case "pull_back": r0 = r * 0.6; r1 = r * 1.05; h0 = h * 0.7; h1 = h * 1.1; break;
    case "orbit_slow": a0 = az0 - 0.4; a1 = az0 + 0.4; break;
    case "push_in": r1 = r * 0.62; break;
    case "push_in_low": r1 = r * 0.55; h1 = h * 0.5; break;
    case "slide": dx = 1.6; break;
    case "dutch_push": r1 = r * 0.6; roll = 0.085; break;
  }
  const L = (a: number, b: number) => a + (b - a) * u;
  const rad = L(r0, r1) * creep, hh = Math.max(0.45 + gy, L(h0, h1)), az = L(a0, a1), sx = dx ? L(-dx, dx) : 0;
  const look: V3 = [sx, fy, z0 - (lz ? L(0, lz) : 0)];
  const cur: CamSpec = { pos: [look[0] + Math.sin(az) * rad, hh, look[2] + Math.cos(az) * rad], look, fov, roll: roll * u };
  const ka = s.id > 1 ? kickAt(f, s.a, 1.2) : 0;           // tiny camera kick right after every cut
  if (!ka) return cur;
  const dxl = cur.look[0] - cur.pos[0], dzl = cur.look[2] - cur.pos[2];
  const dist = Math.hypot(dxl, cur.look[1] - cur.pos[1], dzl) || 1, horiz = Math.hypot(dxl, dzl) || 1;
  const m = 0.0042 * Math.tan((cur.fov * Math.PI) / 360) * dist * ka;
  return { ...cur, look: [cur.look[0] - (dzl / horiz) * m, cur.look[1] + 0.65 * m, cur.look[2] + (dxl / horiz) * m], roll: cur.roll + ka * 0.008 };
};

export const dofAt = (f: number): { cInf: number } => {
  const s = shotAtFrame(f);
  return { cInf: s.focus ? 9 : DOF_BY_SIZE[s.size] ?? 5 };
};
export const focusAt = (id: number, f: number): V3 => camAt(id, f).look;
export const flashLevelAt = (f: number): number =>
  FLASH_AT >= 0 && f >= FLASH_AT && f < FLASH_AT + 4 ? Math.sin(((f - FLASH_AT + 0.5) / 4) * Math.PI) : 0;
export const layersAt = (f: number): { id: number; alpha: number }[] => [{ id: shotAtFrame(f).id, alpha: 1 }];
export const lightAt = (f: number): Light => shotAtFrame(f).light;
