// Every short is registered here. tools/new_short.py inserts new compositions above the marker line automatically.
import React from "react";
import { Composition } from "remotion";
import { BridgeShort, BRIDGE_FRAMES } from "./videos/bridge/Bridge";
import { Short } from "./engine/Short";
import demoPlan from "./engine/demo_plan.json";
import type { Plan } from "./engine/plan";
// @@IMPORTS@@

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="BridgeShort" component={BridgeShort} durationInFrames={BRIDGE_FRAMES} fps={30} width={1080} height={1920} />
    <Composition id="Short" component={Short} width={1080} height={1920} fps={30} durationInFrames={(demoPlan as Plan).total}
      defaultProps={{ plan: demoPlan as Plan }}
      calculateMetadata={({ props }) => ({ durationInFrames: (props as { plan: Plan }).plan.total, fps: (props as { plan: Plan }).plan.fps })} />
    {/* @@COMPOSITIONS@@ */}
  </>
);
