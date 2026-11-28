import * as THREE from "three";
import { Actor, Fx, Pool, SU, charCanvasSize, drawContactBlob, drawSunShadowTail } from "../engine/billboard";
import { LIGHTS } from "../engine/lights";
import {
  Expr,
  Outfit,
  SKIN,
  WordTiming,
  blinkAt,
  bodyFront,
  fxBurst,
  fxSparkles,
  isSpeakingAt,
  poseSnap,
} from "../engine/toon";
import wordsData from "../../public/audio/words.json";
import { FPS } from "./story";

const WORDS = wordsData.words as WordTiming[];

export const HERO_OUTFIT: Outfit = {
  jacket: "#365f9e",
  pants: "#2b3240",
  boots: "#241726",
  hat: "hair",
  hair: "#4a2e1d",
  skin: SKIN,
};

export function stageStarterCast(
  shotId: number,
  frame: number,
  cam: THREE.PerspectiveCamera,
  pool: Pool,
  actors: Actor[],
  fxs: Fx[]
) {
  actors.forEach((a) => {
    a.mesh.visible = false;
    a.r = null;
  });
  fxs.forEach((x) => {
    x.mesh.visible = false;
    x.r = null;
  });

  const t = frame / FPS;
  const lightMode = shotId === 2 ? "golden" : "day";
  const L = LIGHTS[lightMode];
  const blobHex = `#${L.blob.map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("")}`;

  const camPos = cam.position;
  let aIdx = 0;
  let fIdx = 0;

  const drawActor = (
    x: number,
    y: number,
    z: number,
    heightScale: number,
    expr: Expr,
    wave: number | undefined,
    facing: -1 | 0 | 1,
    keyTag: string
  ) => {
    const actor = actors[aIdx++];
    const dist = camPos.distanceTo(new THREE.Vector3(x, y + 1.0, z));
    const [cw, ch, k] = charCanvasSize(dist);
    const speaking = isSpeakingAt(WORDS, t);
    const blink = speaking ? 0 : blinkAt(frame, 68, 13);

    actor.r = pool.req(`hero_${keyTag}_b${blink.toFixed(2)}`, cw, ch, k, (p) =>
      bodyFront(p, HERO_OUTFIT, {
        mode: "stand",
        expr,
        wave,
        facing,
        blink,
        mouthOpen: "auto",
        seed: 3,
      })
    );
    actor.mesh.position.set(x, y, z);
    actor.mesh.scale.setScalar(heightScale);
    actor.mesh.lookAt(camPos.x, y, camPos.z);
    actor.mesh.visible = true;

    const blob = fxs[fIdx++];
    blob.r = drawContactBlob(pool, blobHex);
    blob.mesh.position.set(x, y + 0.015, z);
    blob.mesh.rotation.set(-Math.PI / 2, 0, 0);
    blob.mesh.scale.set(0.95 * heightScale, 0.58 * heightScale, 1);
    blob.mesh.visible = true;

    if (lightMode === "day") {
      const tail = fxs[fIdx++];
      tail.r = drawSunShadowTail(pool, blobHex);
      tail.mesh.position.set(x - 0.52 * heightScale, y + 0.012, z - 0.44 * heightScale);
      tail.mesh.rotation.set(-Math.PI / 2, 0, -0.78);
      tail.mesh.scale.set(1.05 * heightScale, 2.15 * heightScale, 1);
      tail.mesh.visible = true;
    }
  };

  if (shotId === 1) {
    // Snap crisp into greeting wave over 8 frames then HOLD solidly (zero idle sine wobble!)
    const snapWave = poseSnap(frame / 18, 0.45);
    drawActor(0, 0, 0, 1.0, "grin", snapWave, 0, `s1_${snapWave < 1 ? frame : "hold"}`);
  } else {
    drawActor(0, 0, 0, 1.02, "meme_shock", undefined, 1, "s2_peak");
    const age = (frame - 76) / 18;
    if (age >= 0 && age <= 1.0) {
      const fx = fxs[fIdx++];
      fx.use(false);
      fx.r = pool.req(`burst_${Math.round(age * 10)}`, 384, 384, 384 / 500, (p) =>
        fxBurst(p, age, "#fff3b0", 10, 40, 220)
      );
      fx.mesh.position.set(0, 1.85, 0.25);
      fx.mesh.scale.setScalar(1.1);
      fx.mesh.lookAt(camPos);
      fx.mesh.visible = true;
    }
    const sp = fxs[fIdx++];
    sp.use(false);
    sp.r = pool.req(`sparkles_${Math.round(frame / 3)}`, 500, 360, 1.0, (p) =>
      fxSparkles(p, (frame - 75) / 36, "#ffe44d")
    );
    sp.mesh.position.set(0, 1.78, 0.22);
    sp.mesh.scale.set(1.25, 0.9, 1);
    sp.mesh.lookAt(camPos);
    sp.mesh.visible = true;
  }

  pool.flush();
  actors.forEach((a) => {
    if (a.mesh.visible) a.bind();
  });
  fxs.forEach((x) => {
    if (x.mesh.visible) x.bind();
  });
  void SU;
}
