import React from "react";
import { Composition } from "remotion";
import { CaptionsOnlyComposition, ShortComposition } from "./ShortComposition";
import { FPS, TOTAL } from "./scene/story";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainShort"
        component={ShortComposition}
        durationInFrames={TOTAL}
        fps={FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="CaptionsOverlay"
        component={CaptionsOnlyComposition}
        durationInFrames={TOTAL}
        fps={FPS}
        width={1080}
        height={1920}
      />
    </>
  );
};
