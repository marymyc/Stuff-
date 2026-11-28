import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
let framesDir = "out/blender_frames";
let fmt = "jpg";
let audioFile = "public/audio/mix.wav";
let wordsFile = "public/audio/words.json";
let captionsSrc = "src/CaptionsOverlay.tsx";
let storySrc = "src/scene/story.ts";
let outFile = "out/final.mp4";
let fps = 30;
let fontName = "Arial Black";
let fontSize = 98;
let marginV = 530;
let keepAss = false;
let yellowEmphasis = false;

for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--frames" && args[i + 1]) framesDir = args[++i];
  else if (a === "--format" && args[i + 1]) fmt = args[++i].toLowerCase();
  else if (a === "--audio" && args[i + 1]) audioFile = args[++i];
  else if (a === "--words" && args[i + 1]) wordsFile = args[++i];
  else if (a === "--captions-src" && args[i + 1]) captionsSrc = args[++i];
  else if (a === "--story-src" && args[i + 1]) storySrc = args[++i];
  else if (a === "--out" && args[i + 1]) outFile = args[++i];
  else if (a === "--fps" && args[i + 1]) fps = Number(args[++i]) || 30;
  else if (a === "--font" && args[i + 1]) fontName = args[++i];
  else if (a === "--font-size" && args[i + 1]) fontSize = Number(args[++i]) || 98;
  else if (a === "--margin-v" && args[i + 1]) marginV = Number(args[++i]) || 530;
  else if (a === "--yellow-emphasis") yellowEmphasis = true;
  else if (a === "--keep-ass") keepAss = true;
}

const cleanTok = (raw) => raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "").toUpperCase();

function loadEmphasisWords() {
  const out = new Set();
  if (existsSync(captionsSrc)) {
    const txt = readFileSync(captionsSrc, "utf8");
    const m = txt.match(/EMPHASIS_WORDS\s*=\s*new\s+Set\(\[([\s\S]*?)\]\)/);
    if (m) {
      for (const hit of m[1].matchAll(/"([^"]+)"|'([^']+)'/g)) {
        out.add(cleanTok(hit[1] || hit[2]));
      }
    }
  }
  return out;
}

function loadUpperFlag() {
  if (!existsSync(captionsSrc)) return false;
  const txt = readFileSync(captionsSrc, "utf8");
  return /UPPERCASE_CAPTIONS\s*=\s*true/.test(txt);
}

function loadFlashAt() {
  if (!existsSync(storySrc)) return -1;
  const txt = readFileSync(storySrc, "utf8");
  const m = txt.match(/FLASH_AT\s*=\s*(-?\d+)/);
  return m ? Number(m[1]) : -1;
}

function assTime(sec) {
  const s = Math.max(0, sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const whole = Math.floor(ss);
  const cs = Math.min(99, Math.round((ss - whole) * 100));
  return `${h}:${String(m).padStart(2, "0")}:${String(whole).padStart(2, "0")}.${String(cs).padStart(2, "0")}`;
}

function escAss(text) {
  return text.replace(/\\/g, "\\\\").replace(/\{/g, "\\{").replace(/\}/g, "\\}");
}

function buildChunks(words, emphasis, uppercase) {
  const chunks = [];
  let i = 0;
  while (i < words.length) {
    const first = words[i];
    const clean1 = cleanTok(first.w);
    const next = words[i + 1];
    const canPair =
      next &&
      next.line === first.line &&
      !/[.,!?]$/.test(first.w) &&
      clean1.length <= 7 &&
      cleanTok(next.w).length <= 7 &&
      first.w.length + next.w.length <= 13 &&
      next.s - first.e < 0.25;

    const picked = canPair ? [first, next] : [first];
    const last = picked[picked.length - 1];
    const nextAfter = words[i + picked.length];

    const startFrame = Math.max(0, Math.round(first.s * fps));
    const maxHoldFrame =
      nextAfter && nextAfter.line === first.line
        ? Math.max(startFrame + 3, Math.round(nextAfter.s * fps))
        : Math.round((last.e + 0.22) * fps);
    const endFrame = Math.min(maxHoldFrame, Math.round((last.e + 0.14) * fps));

    chunks.push({
      tokens: picked.map((p) => {
        const c = cleanTok(p.w);
        return {
          text: uppercase ? p.w.toUpperCase() : p.w,
          highlight: emphasis.has(c),
        };
      }),
      startFrame,
      endFrame,
    });
    i += picked.length;
  }

  for (let k = 0; k < chunks.length - 1; k++) {
    if (chunks[k].endFrame > chunks[k + 1].startFrame) {
      chunks[k].endFrame = chunks[k + 1].startFrame;
    }
  }
  return chunks;
}

const t0 = Date.now();
const wordsDoc = JSON.parse(readFileSync(path.resolve(wordsFile), "utf8"));
const emphasis = loadEmphasisWords();
const uppercase = loadUpperFlag();
const flashAt = loadFlashAt();
const chunks = buildChunks(wordsDoc.words || [], emphasis, uppercase);

const outAbs = path.resolve(outFile);
mkdirSync(path.dirname(outAbs), { recursive: true });
const assRel = "out/_captions_tmp.ass";
const assAbs = path.resolve(assRel);
mkdirSync(path.dirname(assAbs), { recursive: true });

// ASS BGR hex: White &H00FFFFFF, Yellow #FFE44D -> &H004DE4FF, Dark border #141016 -> &H00161014
const lines = [
  "[Script Info]",
  "ScriptType: v4.00+",
  "PlayResX: 1080",
  "PlayResY: 1920",
  "WrapStyle: 2",
  "ScaledBorderAndShadow: yes",
  "",
  "[V4+ Styles]",
  "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
  `Style: Cap,${fontName},${fontSize},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0.4,0,1,10,4,2,64,64,${marginV},1`,
  "",
  "[Events]",
  "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
];

for (const ch of chunks) {
  const tStart = assTime(ch.startFrame / fps);
  const tEnd = assTime(ch.endFrame / fps);
  const parts = ch.tokens.map((tok) => {
    const col = yellowEmphasis && tok.highlight ? "{\\c&H004DE4FF&}" : "{\\c&H00FFFFFF&}";
    return `${col}${escAss(tok.text)}`;
  });
  const pop = "{\\fscx90\\fscy90\\t(0,75,\\fscx105\\fscy105)\\t(75,150,\\fscx100\\fscy100)}";
  lines.push(`Dialogue: 0,${tStart},${tEnd},Cap,,0,0,0,,${pop}${parts.join(" ")}`);
}

writeFileSync(assAbs, lines.join("\n"), "utf8");
console.log(`Generated ${chunks.length} ASS caption cues -> ${assRel}`);

const vfParts = ["scale=1080:1920:flags=lanczos", `ass=${assRel}`];
if (flashAt >= 0) {
  vfParts.push(
    `drawbox=x=0:y=0:w=iw:h=ih:color=white@0.82:t=fill:enable='between(n,${flashAt},${flashAt + 3})'`
  );
}

const pattern = path.resolve(framesDir, `frame_%04d.${fmt}`);
const ffArgs = ["-y", "-framerate", String(fps), "-start_number", "0", "-i", pattern];
if (existsSync(path.resolve(audioFile))) {
  ffArgs.push("-i", path.resolve(audioFile));
  ffArgs.push(
    "-vf",
    vfParts.join(","),
    "-map",
    "0:v",
    "-map",
    "1:a",
    "-c:v",
    "libx264",
    "-crf",
    "15",
    "-preset",
    "medium",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-b:a",
    "192k",
    "-movflags",
    "+faststart",
    "-shortest",
    outAbs
  );
} else {
  ffArgs.push(
    "-vf",
    vfParts.join(","),
    "-c:v",
    "libx264",
    "-crf",
    "15",
    "-preset",
    "medium",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
    outAbs
  );
}

execFileSync("ffmpeg", ffArgs, { stdio: "inherit" });
if (!keepAss && existsSync(assAbs)) rmSync(assAbs, { force: true });
console.log(`Stage-2 final ready -> ${outAbs} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
