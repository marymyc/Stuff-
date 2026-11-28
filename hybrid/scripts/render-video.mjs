import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { mkdirSync } from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
let entry = "src/index.ts";
let compId = process.env.COMP_ID || "MainShort";
let outFile = "out/video_raw.mp4";
let scale = 1;
let concurrency = 2;

for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--entry" && args[i + 1]) entry = args[++i];
  else if (a === "--comp" && args[i + 1]) compId = args[++i];
  else if (a === "--out" && args[i + 1]) outFile = args[++i];
  else if (a === "--scale" && args[i + 1]) scale = Number(args[++i]) || 1;
  else if (a === "--concurrency" && args[i + 1]) concurrency = Math.max(1, Number(args[++i]) || 2);
}

const outputLocation = path.resolve(outFile);
mkdirSync(path.dirname(outputLocation), { recursive: true });

console.log(`Bundling ${compId} from ${entry}...`);
const t0 = Date.now();
const serveUrl = await bundle({
  entryPoint: path.resolve(entry),
  webpackOverride: (cfg) => cfg,
});

const composition = await selectComposition({
  serveUrl,
  id: compId,
});

console.log(
  `Rendering ${composition.id}: ${composition.width}x${composition.height} @ ${composition.fps}fps, ${composition.durationInFrames} frames`,
);

let lastLoggedPct = -5;
await renderMedia({
  composition,
  serveUrl,
  codec: "h264",
  crf: 14,
  scale,
  pixelFormat: "yuv420p",
  outputLocation,
  overwrite: true,
  muted: true,
  concurrency,
  chromiumOptions: { gl: "angle" },
  onProgress: ({ progress, renderedFrames, encodedFrames }) => {
    const pct = Math.floor(progress * 100);
    if (pct >= lastLoggedPct + 5 || pct === 100) {
      lastLoggedPct = pct;
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
      console.log(
        `[${elapsed}s] ${pct}% (rendered=${renderedFrames}/${composition.durationInFrames}, encoded=${encodedFrames})`,
      );
    }
  },
});

console.log(`Done -> ${outputLocation} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
