// Plan-driven casting: turns a shot's characters into lit billboard drawings (toon.ts) plus contact shadows and fx cards.
import { person, blob, lidAt, setStageLight, Stage, CamInfo, Who as CastWho } from "../videos/bridge/cast";
import { Outfit, Expr, FrontOpts, soldier, townsfolk, OFFICER, KID, PARENT, INK, SKINS, fxBurst, fxPuff, fxStars } from "../videos/bridge/toon";
import { GROUND_Y, PlanShot } from "./plan";

/** role / outfit name -> drawing outfit. `i` varies skin and costume inside a crowd. */
export const outfitFor = (name: string, i: number): Outfit => {
  switch (name) {
    case "soldier": return soldier(i);
    case "commander": return { ...OFFICER };
    case "citizen": return townsfolk(i);
    case "kid": return KID;
    case "parent": return PARENT;
    case "worker": return { jacket: "#b5653f", pants: "#3b3f52", boots: "#4a3426", hat: "cap", cap: "#d9a441", skin: SKINS[i % 4] };
    case "rival": case "tycoon":
      return { jacket: "#e0b233", pants: "#3b3f52", boots: INK, hat: "tophat", belt: "#7a4a1e", buttons: "#8a5a22", moustache: "#2a201a", skin: SKINS[0] };
    case "hero": case "engineer":
      return { jacket: "#1fa89a", pants: "#2d3a52", boots: INK, hat: "cap", cap: "#3b4a78", belt: "#c9353a", buttons: "#f1efe6", skin: SKINS[0] };
    default: return townsfolk(i);
  }
};

const EXPRS = new Set(["neutral", "stern", "grin", "laugh", "whistle", "nervous", "shock", "relief", "relief_open", "dazed", "pained", "smile", "smile_closed", "lick"]);
const q = (v: number, n = 30) => Math.round(v * n) / n;

export const stageShot = (s: PlanShot, f: number, fps: number, cam: CamInfo): Stage => {
  setStageLight(s.light, cam);
  const t = f / fps, out: Stage = { places: [], fx: [] }, gy = GROUND_Y[s.set] ?? 0;
  s.chars.forEach((c, k) => {
    const i = s.id * 10 + k, o = outfitFor(c.outfit, i), sc = c.scale ?? 1;
    const who: CastWho = { i, o, okey: `${c.outfit}${i % 4}` };
    const expr = (EXPRS.has(c.expr) ? c.expr : "neutral") as Expr;
    const stroll = c.mode === "stroll";
    const fo: FrontOpts = { mode: stroll ? "stroll" : "stand", phase: stroll ? q((t * 1.1) % 1, 60) : 0, expr, blink: lidAt(t, i), look: 0 };
    const x = c.x, z = (c.z ?? 0) + (stroll ? 0.35 * Math.sin(t * 0.8) : 0);
    out.places.push(person(cam, who, x, gy, z, { side: false, mirror: false }, fo, {}, sc));
    blob(out, x, gy, z, sc);
  });
  const u = Math.min(1, Math.max(0, (f - s.a) / 14));
  if (s.fx.includes("burst") || s.fx.includes("explosion")) {
    const uu = q(u, 14);
    out.fx.push({ key: `burst${uu}`, cw: 700, ch: 700, draw: (p) => fxBurst(p, uu, "#ffb02e", 12, 40, 260), x: 0, y: 1.9 + gy, z: 1.4, w: 4.6, h: 4.6 });
  }
  if (s.fx.includes("puff")) {
    const uu = q(u, 14);
    out.fx.push({ key: `puff${uu}`, cw: 400, ch: 400, draw: (p) => fxPuff(p, uu), x: -1.2, y: 0.6 + gy, z: 0.8, w: 2.2, h: 2.2, soft: true });
  }
  if (s.fx.includes("stars")) {
    const uu = q(u, 14);
    out.fx.push({ key: `stars${uu}`, cw: 400, ch: 300, draw: (p) => fxStars(p, uu), x: 0, y: 2.7 + gy, z: 0.2, w: 1.8, h: 1.3 });
  }
  return out;
};
