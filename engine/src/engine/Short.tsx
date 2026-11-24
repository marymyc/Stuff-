// The generic short: one Plan -> the same look pipeline as the bridge short
// (InkPass -> lens blur -> bloom + NEUTRAL tone map + grade, MSAA 4) + word-by-word captions.
import React, { useMemo } from "react";
import * as THREE from "three";
import { AbsoluteFill, getInputProps, interpolate, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import { EffectComposer } from "@react-three/postprocessing";
import { BlendFunction, BloomEffect, ToneMappingEffect, ToneMappingMode } from "postprocessing";
import { GenericWorld } from "./world";
import { InkPass, noInkFallback } from "../videos/bridge/ink";
import { LensBlur } from "../videos/bridge/lensblur";
import { GradeEffect, GRADES, GRADE_STRENGTH, gradeFor } from "../videos/bridge/grade";
import { DOF_BY_SIZE, Plan, Word, layersAt } from "./plan";

const makeBloom = () => {
  const b = new BloomEffect({ blendFunction: BlendFunction.ADD, intensity: 0.5, luminanceThreshold: 1.0, luminanceSmoothing: 0.2, mipmapBlur: true, levels: 6, radius: 0.6 });
  const mip = b.mipmapBlurPass;
  const setSize = mip.setSize.bind(mip);
  mip.setSize = (w: number, h: number) => setSize(Math.round((1920 * w) / Math.max(h, 1)), 1920);
  return b;
};
const fwd = new THREE.Vector3(), fpt = new THREE.Vector3();

const Inner: React.FC<{ plan: Plan; i: number }> = ({ plan, i }) => {
  const f = useCurrentFrame();
  const { camera, scene } = useThree();
  const world = useMemo(() => new GenericWorld(plan), [plan]);
  const fx = useMemo(() => ({
    ink: new InkPass(scene, camera as THREE.PerspectiveCamera),
    lens: new LensBlur({ maxCoC: 24, nearScale: 1.2 }),
    bloom: makeBloom(),
    tone: new ToneMappingEffect({ mode: ToneMappingMode.NEUTRAL }),
    grade: new GradeEffect(GRADES.day, GRADE_STRENGTH.day),
  }), [camera, scene]);
  React.useEffect(() => () => fx.ink.dispose(), [fx]);
  const post = useMemo(() => (
    <EffectComposer multisampling={4}>
      <primitive object={fx.ink} dispose={null} />
      <primitive object={fx.lens.pre} dispose={null} />
      <primitive object={fx.lens.main} dispose={null} />
      <primitive object={fx.bloom} dispose={null} />
      <primitive object={fx.tone} dispose={null} />
      <primitive object={fx.grade} dispose={null} />
    </EffectComposer>
  ), [fx]);
  const cam = camera as THREE.PerspectiveCamera;
  const target = world.update(plan, i, f, cam, scene);
  noInkFallback(world.root);
  const s = plan.shots[i];
  cam.getWorldDirection(fwd);
  fpt.copy(target);
  fx.lens.focus = Math.max(0.3, fpt.sub(cam.position).dot(fwd));
  fx.lens.cInf = DOF_BY_SIZE[s.size] ?? 10;
  gradeFor(fx.grade, s.light);
  return (<><primitive object={world.root} dispose={null} />{post}</>);
};

const ShotView: React.FC<{ plan: Plan; i: number; alpha: number }> = ({ plan, i, alpha }) => (
  <AbsoluteFill style={{ opacity: alpha }}>
    <ThreeCanvas width={1080} height={1920} shadows gl={{ antialias: false, stencil: false, powerPreference: "high-performance", toneMappingExposure: 1.0 }} camera={{ fov: 40, near: 0.2, far: 1500 }}>
      <Inner plan={plan} i={i} />
    </ThreeCanvas>
  </AbsoluteFill>
);

// ---- captions: 1-2 words at a time, white heavy sans, black outline, ~70 % height, small pop-in ----
type Card = { s: number; e: number; text: string };
const toCards = (words: Word[]): Card[] => {
  const cards: Card[] = [];
  for (let k = 0; k < words.length;) {
    const g = [words[k++]];
    while (k < words.length && g.length < 2 && !/[.!?,;:]$/.test(g[g.length - 1].w)) g.push(words[k++]);
    cards.push({ s: g[0].s, e: g[g.length - 1].e, text: g.map((x) => x.w).join(" ") });
  }
  for (let k = 0; k + 1 < cards.length; k++) cards[k].e = Math.max(cards[k].e, Math.min(cards[k + 1].s - 0.02, cards[k].e + 0.25));
  return cards;
};
const Captions: React.FC<{ words: Word[]; fps: number }> = ({ words, fps }) => {
  const f = useCurrentFrame();
  const cards = useMemo(() => toCards(words), [words]);
  const t = f / fps;
  const c = cards.find((x) => t >= x.s && t < x.e);
  if (!c) return null;
  const k = Math.round((t - c.s) * fps);
  const pop = interpolate(k, [0, 2, 5], [0.8, 1.12, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center" }}>
      <div style={{
        position: "absolute", top: "70%", transform: `translateY(-50%) scale(${pop})`, width: "92%", textAlign: "center",
        fontFamily: '"Arial Black", "Helvetica Neue", Impact, "DejaVu Sans", sans-serif', fontWeight: 900, fontSize: 104, lineHeight: 1.05,
        color: "#fff", WebkitTextStroke: "14px #000", paintOrder: "stroke fill", textShadow: "0 6px 0 rgba(0,0,0,0.35)",
      }}>{c.text}</div>
    </AbsoluteFill>
  );
};

export const Short: React.FC<{ plan: Plan }> = ({ plan: planProp }) => {
  const f = useCurrentFrame();
  const plan = ((getInputProps() as { plan?: Plan }).plan ?? planProp) as Plan;
  const flash = plan.flashAt != null && f >= plan.flashAt && f < plan.flashAt + 4 ? [1, 0.75, 0.45, 0.2][f - plan.flashAt] : 0;
  return (
    <AbsoluteFill style={{ background: "#cfe3f2" }}>
      {layersAt(plan, f).map((l, k) => <ShotView key={k ? "over" : "base"} plan={plan} i={l.i} alpha={l.alpha} />)}
      {flash > 0 && <AbsoluteFill style={{ background: "#ffffff", opacity: flash }} />}
      {plan.captions && <Captions words={plan.words} fps={plan.fps} />}
    </AbsoluteFill>
  );
};
