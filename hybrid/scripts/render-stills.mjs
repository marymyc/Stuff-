import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import { mkdirSync } from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
let entry = "src/index.ts";
let compId = process.env.COMP_ID || "MainShort";
let scale = 0.75;
let outDirArg = "out/stills";
const frames = [];

for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--entry" && args[i + 1]) entry = args[++i];
  else if (a === "--comp" && args[i + 1]) compId = args[++i];
  else if (a === "--scale" && args[i + 1]) scale = Number(args[++i]) || 0.75;
  else if (a === "--out" && args[i + 1]) outDirArg = args[++i];
  else if (!Number.isNaN(Number(a))) frames.push(Number(a));
}

const TARGET_FRAMES = frames.length ? frames : [12, 45, 76, 120];
const outDir = path.resolve(outDirArg);
mkdirSync(outDir, { recursive: true });

console.log(`Bundling ${compId} from ${entry}...`);
const serveUrl = await bundle({
  entryPoint: path.resolve(entry),
  webpackOverride: (cfg) => cfg,
});

const composition = await selectComposition({
  serveUrl,
  id: compId,
});

for (const frame of TARGET_FRAMES) {
  const out = path.join(outDir, `f${String(frame).padStart(4, "0")}.jpg`);
  const t0 = Date.now();
  await renderStill({
    composition,
    serveUrl,
    frame,
    output: out,
    imageFormat: "jpeg",
    jpegQuality: 88,
    scale,
    chromiumOptions: { gl: "angle" },
  });
  console.log(`Rendered f=${frame} -> ${out} (${Date.now() - t0}ms)`);
}
