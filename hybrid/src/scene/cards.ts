import {
  Expr,
  FrontOpts,
  INK,
  KID,
  OFFICER,
  Outfit,
  PARENT,
  Pen,
  SKIN,
  SKINS,
  bodyFront,
  fxBurst,
  fxPuff,
  fxStars,
  poseSnap,
  soldier,
  springBounce,
  townsfolk,
} from "../engine/toon";
import { PLAN_SHOTS, groundY, zoneZ } from "./story";

export const createPen = (g: CanvasRenderingContext2D) => new Pen(g);

export type ExportCardSpec =
  | {
      id: string;
      kind?: "toon";
      width?: number;
      height?: number;
      designW?: number;
      designH?: number;
      draw: (p: Pen) => void;
    }
  | {
      id: string;
      kind: "canvas";
      width: number;
      height: number;
      draw2d: (ctx: CanvasRenderingContext2D, w: number, h: number) => void;
    };

export type CardPlacement = {
  id: string;
  card: string;
  pos: [number, number, number];
  heightM: number;
  a: number;
  b: number;
  emit?: number;
  shadow?: boolean;
  rotDeg?: number;
  pitchDeg?: number;
  yawDeg?: number;
  scaleX?: number;
  scaleY?: number;
  jitter?: number;
};

export const EXPORT_CARDS: ExportCardSpec[] = [];
export const CARD_PLACEMENTS: CardPlacement[] = [];

const seenCards = new Set<string>();
const BLINK_ENV = [0.55, 1.0, 1.0, 0.55];
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (t: number) => {
  const u = clamp01(t);
  return u * u * (3 - 2 * u);
};
const qInt = (v: number, steps = 20) => Math.round(v * steps);

function blinkValueAt(f: number, period: number, phaseShift: number, swaps: number[]): number {
  for (const ts of swaps) {
    const k = f - ts + 1;
    if (k >= 0 && k < 4) return BLINK_ENV[k];
  }
  const ph = (((f + phaseShift) % period) + period) % period;
  return ph >= 0 && ph < 4 ? BLINK_ENV[ph] : 0;
}

/** 3-phase grounded comic jump: 6f knee-bend anticipation -> 3D pos[1] arc -> 7f landing catch. */
function jumpState(f: number, tTakeoff: number, tLand: number, peakM = 0.36) {
  const antStart = tTakeoff - 6;
  const catchEnd = tLand + 7;
  if (f >= antStart && f < tTakeoff) {
    const u = Math.sin(clamp01((f - antStart) / 6) * Math.PI * 0.5);
    return { yLift: 0, hop: 0, knees: 0.95 * u, squash: 1 - 0.10 * u, bend: 8 * u };
  }
  if (f >= tTakeoff && f < tLand) {
    const u = (f - tTakeoff) / Math.max(1, tLand - tTakeoff);
    const arc = Math.sin(u * Math.PI);
    const takeStretch = u < 0.25 ? (1 - u / 0.25) * 0.07 : u > 0.78 ? ((u - 0.78) / 0.22) * 0.06 : 0;
    return { yLift: arc * peakM, hop: arc, knees: 0, squash: 1 + takeStretch, bend: 2 };
  }
  if (f >= tLand && f < catchEnd) {
    const u = smooth((f - tLand) / 7);
    const c = 1 - u;
    return { yLift: 0, hop: 0, knees: 0.75 * c, squash: 1 - 0.10 * c, bend: 6 * c };
  }
  return { yLift: 0, hop: 0, knees: 0, squash: 1, bend: 0 };
}

function actorCardKey(prefix: string, o: FrontOpts): string {
  const blinkQ = o.blink === true ? 4 : qInt(Number(o.blink) || 0, 4);
  const propK = Array.isArray(o.prop) ? `${o.prop[0]}_${qInt(o.prop[1], 16)}` : String(o.prop ?? "none");
  const hOff = o.headOff ? `${qInt(o.headOff[0], 6)}_${qInt(o.headOff[1], 6)}` : "0";
  const eLook = o.eyeLook ? `${qInt(o.eyeLook[0], 6)}_${qInt(o.eyeLook[1], 6)}` : qInt(o.look ?? 0, 8);
  return [
    prefix,
    o.mode ?? "stand",
    o.expr ?? "neutral",
    o.armL ?? "d",
    o.armR ?? "d",
    qInt(o.armK ?? 1, 14),
    qInt(o.phase ?? 0, 16),
    eLook,
    blinkQ,
    qInt(o.bend ?? 0, 2),
    qInt(o.tilt ?? 0, 2),
    qInt(o.headTilt ?? 0, 2),
    hOff,
    qInt(o.headSquash ?? 1, 12),
    qInt(o.squash ?? 1, 12),
    qInt(o.inflate ?? 1, 10),
    qInt(o.spineCurve ?? 0, 10),
    qInt(o.hop ?? 0, 12),
    qInt(o.knees ?? 0, 8),
    o.soleY ?? 975,
    qInt(o.browLift ?? 0, 4),
    o.faceTint ? o.faceTint.replace("#", "") : "s",
    o.facing ?? 0,
    propK,
  ].join("_");
}

function ensureActorCard(keyPrefix: string, outfit: Outfit, opts: FrontOpts): string {
  const cleanOpts: FrontOpts = { mouthOpen: "auto", soleY: 1080, ...opts };
  const id = actorCardKey(keyPrefix, cleanOpts).replace(/[^a-zA-Z0-9_-]/g, "_");
  if (!seenCards.has(id)) {
    seenCards.add(id);
    EXPORT_CARDS.push({ id, width: 900, height: 1680, designW: 600, designH: 1120, draw: (p) => bodyFront(p, outfit, cleanOpts) });
  }
  return id;
}

type ExtraTrans = Partial<Pick<CardPlacement, "rotDeg" | "pitchDeg" | "yawDeg" | "scaleX" | "scaleY" | "jitter">>;

/** 30fps on-ones elastic actor generator with automatic deduplication for consecutive identical frames. */
function addLivingSeq(
  id: string,
  keyPrefix: string,
  outfit: Outfit,
  a: number,
  b: number,
  posAt: (u: number, f: number) => [number, number, number],
  optsAt: (u: number, f: number) => FrontOpts,
  cfg?: {
    blinkPeriod?: number;
    blinkShift?: number;
    swaps?: number[];
    heightAt?: (u: number, f: number) => number;
    emit?: number;
    extraAt?: (u: number, f: number) => ExtraTrans;
  }
) {
  const period = cfg?.blinkPeriod ?? 36;
  const shift = cfg?.blinkShift ?? 0;
  const swaps = cfg?.swaps ?? [];
  const span = Math.max(1, b - a - 1);
  let lastKey = "";

  for (let f = a; f < b; f++) {
    const u = (f - a) / span;
    const baseOpts = optsAt(u, f);
    const bl = baseOpts.blink ?? blinkValueAt(f, period, shift, swaps);
    const card = ensureActorCard(keyPrefix, outfit, { ...baseOpts, blink: bl });
    const pos = posAt(u, f);
    const heightM = cfg?.heightAt ? cfg.heightAt(u, f) : 2.15;
    const extra = cfg?.extraAt ? cfg.extraAt(u, f) : {};
    const placementKey = JSON.stringify([card, pos.map((v) => Math.round(v * 1000)), Math.round(heightM * 100), extra]);
    const prev = CARD_PLACEMENTS[CARD_PLACEMENTS.length - 1];
    if (prev && prev.id === id && prev.b === f && placementKey === lastKey) {
      prev.b = f + 1;
    } else {
      CARD_PLACEMENTS.push({ id, card, pos, heightM, a: f, b: f + 1, emit: cfg?.emit ?? 0.50, ...extra });
      lastKey = placementKey;
    }
  }
}


/** role / outfit name -> drawing outfit (thin pure-black limbs like the references). `i` varies skin/costume inside a crowd. */
export const outfitFor = (name: string, i: number): Outfit => {
  const base: Outfit = (() => {
    switch (name) {
      case "soldier": return soldier(i);
      case "commander": return { ...OFFICER };
      case "citizen": return townsfolk(i);
      case "kid": return KID;
      case "parent": return PARENT;
      case "worker": return { jacket: "#b5653f", pants: "#3b3f52", boots: "#4a3426", hat: "cap", cap: "#d9a441", skin: SKINS[i % 4] };
      case "rival": case "tycoon":
        return { jacket: "#e0b233", pants: "#3b3f52", boots: INK, hat: "tophat", belt: "#7a4a1e", buttons: "#8a5a22", moustache: "#2a201a", pocketWatch: true, skin: SKIN };
      case "hero": case "engineer":
        return { jacket: "#1fa89a", pants: "#2d3a52", boots: INK, hat: "cap", cap: "#3b4a78", belt: "#c9353a", buttons: "#f1efe6", skin: SKIN };
      default: return townsfolk(i);
    }
  })();
  return { ...base, limb: INK };
};

const EXPRS = new Set<string>(["neutral", "stern", "grin", "laugh", "laugh_tears", "whistle", "nervous", "shock", "relief", "relief_open", "dazed",
  "pained", "smile", "smile_closed", "lick", "smug", "wink", "furious", "bloodshot", "tired", "talk_o", "talk_a", "meme_grin", "meme_fume", "meme_shock"]);

// ---- fx cards (shared) ----
for (let k = 0; k < 8; k++) EXPORT_CARDS.push({ id: `fxb_${k}`, width: 600, height: 600, designW: 500, designH: 500, draw: (p) => fxBurst(p, k / 7, "#fff3b0", 10, 40, 220) });
for (let k = 0; k < 6; k++) {
  EXPORT_CARDS.push({ id: `fxp_${k}`, width: 500, height: 500, designW: 400, designH: 400, draw: (p) => fxPuff(p, k / 5) });
  EXPORT_CARDS.push({ id: `fxs_${k}`, width: 500, height: 360, designW: 400, designH: 300, draw: (p) => fxStars(p, k / 5) });
}

// ---- the whole cast, straight from the plan ----
for (const s of PLAN_SHOTS) {
  const z0 = zoneZ(s.zone), gy = groundY(s.set);
  s.chars.forEach((c, k) => {
    const act = c.action, sc = c.scale ?? 1, expr = (EXPRS.has(c.expr) ? c.expr : "neutral") as Expr;
    const outfit = outfitFor(c.outfit, s.id * 10 + k);
    addLivingSeq(
      `s${s.id}_c${k}`, `${c.outfit}${k}`, outfit, s.a, s.b,
      (u, f) => {
        const j = act === "hop" ? jumpState(f, s.a + 4, s.a + 18, 0.34) : null;
        return [c.x + (act === "stroll" ? (u - 0.5) * 0.9 : 0), gy + (j ? j.yLift : 0), z0 - (c.z ?? 0)];
      },
      (_u, f) => {
        const sp = springBounce(f - s.a, 0.55, 0.18, 0.15);           // pop on arrival, then HOLD (no idle wobble)
        const o: FrontOpts = { mode: "stand", expr, squash: 1 - sp, inflate: 1 + sp * 0.3, headOff: [0, sp * 10], headSquash: 1 + sp * 0.2, facing: 0, seed: 3 + k };
        if (act === "stroll") { o.mode = "stroll"; o.phase = (f * 0.045) % 1; }
        if (act === "sit") o.mode = "sit";
        if (act === "wave") o.wave = poseSnap((f - s.a) / 18, 0.45);
        if (act === "point") { o.armR = "point"; o.armK = poseSnap((f - s.a - 3) / 10, 0.3); }
        if (act === "hop") {
          const j = jumpState(f, s.a + 4, s.a + 18, 0.34);
          o.hop = j.hop; o.knees = j.knees; o.bend = j.bend; o.squash = j.squash - sp * 0.5;
        }
        return o;
      },
      { heightAt: () => 2.15 * sc, blinkPeriod: 30 + ((k * 7 + s.id * 5) % 14), blinkShift: s.id * 11 + k * 5, swaps: [s.a] }
    );
  });

  const lead = s.chars[0];
  const fxAt = (cards: string, n: number, f0: number, f1: number, pos: [number, number, number], h: number, step: number, emit: number) => {
    for (let f = f0; f < Math.min(f1, s.b); f++) {
      const idx = Math.min(n - 1, Math.floor((f - f0) / step));
      CARD_PLACEMENTS.push({ id: `fx_${cards}_${s.id}`, card: `${cards}_${idx}`, pos, heightM: h, a: f, b: f + 1, emit, shadow: false });
    }
  };
  if (s.fx.includes("burst") || s.fx.includes("explosion")) fxAt("fxb", 8, s.a + 2, s.a + 18, [0, 1.9 + gy, z0 - 1.0], 2.4, 2, 0.9);
  if (s.fx.includes("puff")) fxAt("fxp", 6, s.a + 2, s.a + 20, [(lead?.x ?? 0) - 0.5, 2.4 + gy, z0], 1.0, 3, 0.5);
  if (s.fx.includes("stars")) fxAt("fxs", 6, s.a + 2, s.a + 24, [lead?.x ?? 0, 2.55 + gy, z0], 0.9, 4, 0.7);
}
