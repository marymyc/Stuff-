import { createRequire } from "node:module";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const req = createRequire(path.resolve("package.json"));
const { build } = req("esbuild");
const { ensureBrowser, openBrowser } = req("@remotion/renderer");

const args = process.argv.slice(2);
let entry = "src/scene/cards.ts";
let storyEntry = "src/scene/story.ts";
let outDirArg = "out/cards";

for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--entry" && args[i + 1]) entry = args[++i];
  else if (a === "--story" && args[i + 1]) storyEntry = args[++i];
  else if (a === "--out" && args[i + 1]) outDirArg = args[++i];
}

const outDir = path.resolve(outDirArg);
mkdirSync(outDir, { recursive: true });

const t0 = Date.now();
const bundledCards = await build({
  entryPoints: [path.resolve(entry)],
  bundle: true,
  write: false,
  format: "iife",
  globalName: "__RICKS_CARDS__",
  platform: "browser",
  target: ["chrome120"],
});

let bundleStoryJs = "";
if (storyEntry && existsSync(path.resolve(storyEntry))) {
  const bundledStory = await build({
    entryPoints: [path.resolve(storyEntry)],
    bundle: true,
    write: false,
    format: "iife",
    globalName: "__RICKS_STORY__",
    platform: "browser",
    target: ["chrome120"],
  });
  bundleStoryJs = bundledStory.outputFiles[0].text;
}

const bundleJs = bundledCards.outputFiles[0].text;
const status = await ensureBrowser();
const browser = await openBrowser("chrome-headless-shell", {
  browserExecutable: status.path,
  chromiumOptions: { gl: "angle" },
  logLevel: "warn",
});

try {
  const ctx = browser.browserContexts()[0];
  const page = await ctx.newPage({
    context: {
      getOriginalStackFrame: async (x) => x,
      getOriginalStackTrace: async (x) => x,
    },
    logLevel: "warn",
    indent: false,
    pageIndex: 0,
    onBrowserLog: null,
    onLog: () => {},
  });

  // Step 1: Initialize modules in browser context & extract lightweight metadata + placements + camPath
  const meta = await page.evaluate(
    (code, storyCode) => {
      const mod = new Function(`${code}; return __RICKS_CARDS__;`)();
      window.__CARDS_MOD__ = mod;
      const specs = mod.EXPORT_CARDS || [];
      const placements = mod.CARD_PLACEMENTS || [];
      const cardsMeta = {};
      for (const item of specs) {
        cardsMeta[item.id] = { width: item.width || 900, height: item.height || 1500 };
      }

      const camPath = [];
      if (storyCode) {
        const st = new Function(`${storyCode}; return __RICKS_STORY__;`)();
        const total = Number(st.TOTAL || 0);
        const shots = st.SHOTS || [];
        for (let f = 0; f < total; f++) {
          const s = shots.find((x) => f >= x.a && f < x.b) || shots[shots.length - 1] || { id: 1, light: "day" };
          const cm = st.camAt ? st.camAt(s.id, f) : { pos: [0, 1.6, 4], look: [0, 1.3, 0], fov: 40, roll: 0 };
          const dof = st.dofAt ? st.dofAt(f) : { cInf: 0 };
          const focus = st.focusAt ? st.focusAt(s.id, f) : cm.look;
          const flash =
            typeof st.flashLevelAt === "function"
              ? st.flashLevelAt(f)
              : st.FLASH_AT != null && f >= st.FLASH_AT && f < st.FLASH_AT + 4
              ? Math.sin(((f - st.FLASH_AT + 0.5) / 4) * Math.PI)
              : 0;
          camPath.push({
            f,
            shot: s.id,
            light: typeof st.lightAt === "function" ? st.lightAt(f) : (s.light || "day"),
            pos: cm.pos,
            look: cm.look,
            fov: cm.fov ?? 40,
            roll: cm.roll ?? 0,
            cInf: dof.cInf ?? 0,
            focus,
            flash,
          });
        }
      }
      return { totalCards: specs.length, cardsMeta, placements, camPath };
    },
    bundleJs,
    bundleStoryJs
  );

  // Step 2: Render & transfer PNGs in small 20-card batches to keep Chrome CDP payload tiny (<3 MB/batch)
  const BATCH = 20;
  for (let start = 0; start < meta.totalCards; start += BATCH) {
    const end = Math.min(meta.totalCards, start + BATCH);
    const batchFiles = await page.evaluate(
      (i0, i1) => {
        const mod = window.__CARDS_MOD__;
        const specs = mod.EXPORT_CARDS || [];
        const out = [];
        let c = window.__CARD_TMP_CANVAS__;
        if (!c) {
          c = document.createElement("canvas");
          window.__CARD_TMP_CANVAS__ = c;
        }
        for (let i = i0; i < i1; i++) {
          const item = specs[i];
          const w = item.width || 900;
          const h = item.height || 1500;
          if (c.width !== w) c.width = w;
          if (c.height !== h) c.height = h;
          const g = c.getContext("2d");
          g.setTransform(1, 0, 0, 1, 0, 0);
          g.clearRect(0, 0, w, h);
          if (item.kind === "canvas" && typeof item.draw2d === "function") {
            item.draw2d(g, w, h);
          } else if (typeof item.draw === "function") {
            const designW = item.designW || 600;
            const designH = item.designH || 1000;
            const k = w / designW;
            const p = mod.createPen ? mod.createPen(g) : null;
            if (!p) throw new Error("cards module must re-export createPen from engine/toon");
            g.save();
            g.setTransform(k, 0, 0, k, 0, 0);
            item.draw(p, designW, designH);
            g.restore();
          }
          const dataUrl = c.toDataURL("image/png");
          out.push({ id: item.id, b64: dataUrl.split(",")[1] });
        }
        return out;
      },
      start,
      end
    );
    for (const f of batchFiles) {
      writeFileSync(path.join(outDir, `${f.id}.png`), Buffer.from(f.b64, "base64"));
    }
  }

  writeFileSync(
    path.join(outDir, "manifest.json"),
    JSON.stringify({ cards: meta.cardsMeta, placements: meta.placements, camPath: meta.camPath }, null, 2)
  );
  console.log(
    `Exported ${meta.totalCards} PNG card(s), ${meta.placements.length} placement(s), ${meta.camPath.length} camPath frame(s) -> ${outDir} (${Date.now() - t0}ms)`
  );
} finally {
  await browser.close({ silent: true });
}
