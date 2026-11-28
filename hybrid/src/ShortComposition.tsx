import React, { useLayoutEffect, useMemo, useRef } from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import {
  BloomEffect,
  EffectComposer,
  EffectPass,
  RenderPass,
  ToneMappingEffect,
  ToneMappingMode,
} from "postprocessing";
import { CaptionsOverlay } from "./CaptionsOverlay";
import { GRADE_DAY2, GradeEffect, gradeFor } from "./engine/grade";
import { InkPass } from "./engine/ink";
import { GrainEffect, LensBlur } from "./engine/lensblur";
import {
  ENABLE_AUDIO,
  FLASH_AT,
  SHOW_CAPTIONS,
  SHOTS,
  dofAt,
  focusAt,
  layersAt,
} from "./scene/story";
import { WorldScene } from "./scene/world";

type LayerProps = {
  shotId: number;
  frame: number;
  alpha: number;
};

const SceneRig: React.FC<{ shotId: number; frame: number; world: WorldScene }> = ({
  shotId,
  frame,
  world,
}) => {
  const { gl, scene, camera, size } = useThree();
  const focusVec = useRef(new THREE.Vector3());
  const camFwd = useRef(new THREE.Vector3());

  const pipeline = useMemo(() => {
    const comp = new EffectComposer(gl, {
      frameBufferType: THREE.HalfFloatType,
      multisampling: 0,
    });
    const render = new RenderPass(scene, camera);
    const ink = new InkPass(scene, camera as THREE.PerspectiveCamera);
    const lens = new LensBlur({ maxCoC: 24, nearScale: 1.2 });
    const bloom = new BloomEffect({
      luminanceThreshold: 1.0,
      intensity: 0.42,
      mipmapBlur: true,
    });
    const tone = new ToneMappingEffect({ mode: ToneMappingMode.NEUTRAL });
    const grade = new GradeEffect(GRADE_DAY2);
    const grain = new GrainEffect({ amount: 0.006, cellPx: 1.2 });

    comp.addPass(render);
    comp.addPass(ink);
    comp.addPass(new EffectPass(camera, lens.pre));
    comp.addPass(new EffectPass(camera, lens.main, bloom, tone, grade, grain));
    comp.setSize(size.width, size.height);

    return { comp, ink, lens, bloom, grade, grain };
  }, [gl, scene, camera, size.width, size.height]);

  useLayoutEffect(() => {
    if (!scene.children.includes(world.root)) {
      scene.add(world.root);
    }
    const cam = camera as THREE.PerspectiveCamera;
    world.update(shotId, frame, cam, scene);

    const shot = SHOTS.find((x) => x.id === shotId) ?? SHOTS[0];
    const dof = dofAt(frame);
    const explicitFocus = focusAt(shotId, frame);
    focusVec.current.set(...explicitFocus).sub(cam.position);
    cam.getWorldDirection(camFwd.current);
    const focusDist = Math.max(1.2, focusVec.current.dot(camFwd.current));

    pipeline.lens.focus = focusDist;
    pipeline.lens.cInf = dof.cInf;
    pipeline.bloom.intensity = shot.light === "golden" ? 0.55 : 0.4;
    gradeFor(pipeline.grade, shot.light);
    pipeline.grain.seed = frame;
  }, [shotId, frame, world, scene, camera, pipeline]);

  useFrame(() => {
    pipeline.comp.render();
  }, 1);

  return null;
};

const ShotLayer: React.FC<LayerProps> = ({ shotId, frame, alpha }) => {
  const { width, height } = useVideoConfig();
  const world = useMemo(() => new WorldScene(), []);

  return (
    <AbsoluteFill style={{ opacity: alpha }}>
      <ThreeCanvas
        width={width}
        height={height}
        shadows
        dpr={1}
        gl={{
          antialias: false,
          stencil: false,
          powerPreference: "high-performance",
          toneMappingExposure: 1.0,
        }}
        camera={{ fov: 40, near: 0.2, far: 1400, position: [0, 4, -20] }}
      >
        <SceneRig shotId={shotId} frame={frame} world={world} />
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

export const ShortComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const layers = layersAt(frame);

  // 4-frame crisp white flash exiting hook
  const flashAge = frame - FLASH_AT;
  const flashOpacity =
    FLASH_AT >= 0 && flashAge >= 0 && flashAge < 4
      ? Math.max(0, 1 - flashAge / 4) * 0.92
      : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#141822" }}>
      {layers.map((layer) => (
        <ShotLayer
          key={layer.id}
          shotId={layer.id}
          frame={frame}
          alpha={layer.alpha}
        />
      ))}

      {flashOpacity > 0 && (
        <AbsoluteFill
          style={{
            backgroundColor: "#ffffff",
            opacity: flashOpacity,
            pointerEvents: "none",
          }}
        />
      )}

      {SHOW_CAPTIONS && <CaptionsOverlay />}
      {ENABLE_AUDIO && <Audio src={staticFile("audio/mix.wav")} />}
    </AbsoluteFill>
  );
};

export const CaptionsOnlyComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const flashAge = frame - FLASH_AT;
  const flashOpacity =
    FLASH_AT >= 0 && flashAge >= 0 && flashAge < 4
      ? Math.max(0, 1 - flashAge / 4) * 0.92
      : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      {flashOpacity > 0 && (
        <AbsoluteFill
          style={{
            backgroundColor: "#ffffff",
            opacity: flashOpacity,
            pointerEvents: "none",
          }}
        />
      )}
      {SHOW_CAPTIONS && <CaptionsOverlay />}
    </AbsoluteFill>
  );
};
