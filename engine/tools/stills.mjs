// Render look-check stills (bundles once, then renders each frame as a jpeg).
// usage: node tools/stills.mjs <CompositionId> <outPrefix> <frame,frame,...> [scale=0.5]
//   e.g. node tools/stills.mjs TitanicShort out/titanic/x_ 100,400,900 0.5
// ENTRY=src/sandboxes/<name>/index.tsx renders a sandbox copy instead of src/index.ts.
// .env: REMOTION_TMP (big folder for bundles), CHROME_PATH (optional), REMOTION_GL (angle | egl | swangle | vulkan).
import fs from "node:fs";
import path from "node:path";
if (fs.existsSync(".env")) for (const l of fs.readFileSync(".env", "utf8").split(/\r?\n/)) {
  const m = l.match(/^\s*([A-Z_]+)\s*=\s*(.*)\s*$/); if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
}
// every bundle copies public/ into the temp folder and is never deleted: keep it on a big drive
const tmp = path.resolve(process.env.REMOTION_TMP || "remotion-tmp");
fs.mkdirSync(tmp, { recursive: true });
process.env.TEMP = process.env.TMP = process.env.TMPDIR = tmp;
const { bundle } = await import("@remotion/bundler");
const { renderStill, selectComposition } = await import("@remotion/renderer");

const [id, prefix, frames, scale = "0.5"] = process.argv.slice(2);
if (!id || !prefix || !frames) { console.log("usage: node tools/stills.mjs <CompositionId> <outPrefix> <frames> [scale]"); process.exit(1); }
fs.mkdirSync(path.dirname(path.resolve(prefix)), { recursive: true });
const browserExecutable = process.env.CHROME_PATH || null;
// PROPS=plan.json renders a generated short (inputProps); without it the composition's defaultProps (demo plan) are used
const inputProps = process.env.PROPS ? { plan: JSON.parse(fs.readFileSync(process.env.PROPS, "utf8")) } : undefined;
const chromiumOptions = { gl: process.env.REMOTION_GL || "angle" };
const serveUrl = await bundle({ entryPoint: path.resolve(process.env.ENTRY || "src/index.ts"), publicDir: path.resolve("public") });
const composition = await selectComposition({ serveUrl, id, browserExecutable, chromiumOptions, inputProps });
const onBrowserLog = (l) => { if (l.type === "error" || l.type === "warning") console.log(`[${l.type}]`, l.text.slice(0, 300)); };
for (const f of frames.split(",").map(Number)) {
  const t0 = Date.now();
  await renderStill({ composition, serveUrl, frame: f, output: `${prefix}${f}.jpg`, imageFormat: "jpeg", jpegQuality: 88,
    scale: Number(scale), inputProps, browserExecutable, chromiumOptions, timeoutInMilliseconds: 180000, onBrowserLog });
  console.log("still", f, ((Date.now() - t0) / 1000).toFixed(1) + "s", `${prefix}${f}.jpg`);
}
