// Plan-driven camera in the measured grammar: ease-out glide (fast start, soft landing), holds creep in 0.2 %/f,
// low heights, dutch roll only on the punch. Characters stand around (0, 0, 0) and the camera sits on the -z side.
import { Cam, glide, clamp01 } from "../videos/bridge/story";
import { GROUND_Y, PlanShot } from "./plan";

// [distance, height, vertical fov, focus height]
const SIZE: Record<string, [number, number, number, number]> = {
  wide_aerial: [38, 16, 52, 1.0], wide: [15, 2.4, 46, 1.3], medium: [6.2, 1.15, 40, 1.15],
  medium_low: [5.2, 0.8, 42, 1.35], close: [3.1, 1.1, 34, 1.45], macro: [1.8, 0.8, 30, 0.9],
};

// insert shots: tight, low, looking at an object that sits on the ground at the origin
const FOCUS: [number, number, number, number] = [1.15, 0.5, 30, 0.22];

export const camAt = (s: PlanShot, f: number): Cam => {
  const [r, h0b, fov, fy0] = (s.focus ? FOCUS : SIZE[s.size]) ?? SIZE.medium, gy = GROUND_Y[s.set] ?? 0, h = h0b + gy, fy = fy0 + gy;
  const n = Math.max(1, s.b - s.a), u = glide(clamp01((f - s.a) / Math.max(18, n * 0.8)));
  const creep = 1 - 0.0018 * Math.max(0, f - s.a - n * 0.5);
  const side = s.id % 2 ? 1 : -1, az0 = side * (s.size === "close" ? 0.12 : 0.3);
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
  const rad = L(r0, r1) * creep, hh = L(h0, h1), az = L(a0, a1), sx = dx ? L(-dx, dx) : 0;
  const look: [number, number, number] = [sx, fy, lz ? L(0, lz) : 0];
  return { pos: [look[0] + Math.sin(az) * rad, hh, look[2] - Math.cos(az) * rad], look, fov, roll: roll * u };
};
