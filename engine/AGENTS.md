# AGENTS.md - instructions for ANY AI coding agent


## HARD RULE: never render in the agent's own environment
Do NOT run any render (Remotion stills/video, Blender, frame/video generation) in your own sandbox or CI, even "just one still".
Only the USER runs renders (their GPU / their Colab). You may: write code, typecheck (`npx tsc --noEmit`), run unit tests,
build plans (`tools/make_plan.py`) and audio, and push to GitHub. Anything visual stays unverified until the user reports back.

You are working in a template that turns **one script** into a finished **55-70 s vertical animated short**
(1080x1920 master, 2K final 1440x2560): flat 2D cartoon characters (bean heads, plum ink) in a colourful painted 3D
world with black ink outlines, lens blur, gliding cameras, a narrated voice, synthesized SFX and an original score.
Everything renders locally with three.js inside Remotion. No AI video generator.

A complete, proven example ships with the repo: **"The Bridge That Fell for a Song"** (`src/videos/bridge/` +
`projects/bridge/`). Every new short is a copy of it in which the **story** is rewritten and the **look** is kept.

These instructions work for Claude Code, Codex, Gemini CLI, Cursor, Copilot, Aider, OpenHands or any agent that can
read files, edit code and run shell commands. If you cannot run commands, say so and give the user the exact commands.

---------------------------------------------------------------------------------------------------------------------
## 0. Inputs you get from the user
- A script (pasted text or a file), or just a topic. Optional: a short name, visual notes, voice preference.
- If only a topic is given: research it where browsing is available, write sourced facts + script using the formula in section 3, and **ask the user to approve the script before step 4**. If research is unavailable, state that and ask for sources/fact notes rather than inventing facts. Once the script is approved: "just do it" - finish without asking again,
  except for things only the user can do (API keys, recording a voice, installing software).
- If the user's script is in another language or too long/short, adapt it to the formula, show the English version
  and get approval first.

## 1. Hard rules (never break)
1. Story, characters and voice are **original**. `references/` is for the LOOK only: never copy its scripts,
   characters or shots, never name its source channel, never upload or publish those frames.
2. No captions, subtitles or text labels in the video. English voice-over, one steady tone.
3. Jokes and facts are real and sourced (sources at the top of SCRIPT.md).
4. Keep the look values (section 6) unchanged unless the user asks. They took 4 verification rounds to reach.
5. Every visual reaction lands **0-3 frames before** its word in `words.json`.
6. Standard mix: music +3 dB, SFX -6 dB, voice unchanged. Final export 2K vertical (`--scale 1.3333`).
7. **Save progress after every step** in `projects/<name>/STATUS.md` (tick the box, write decisions and frame
   numbers). Another agent must be able to resume from that file alone.
8. Do not rename the exports `BridgeShort` / `BRIDGE_FRAMES` in a copied short (Root.tsx imports them under an alias).
9. Lock the picture timing (story.ts constants) before making the sound. Any later timing change = re-run the sound.

## 2. Setup (once per machine) - check first, install only what is missing
```
python tools/check_env.py          # tells you exactly what is missing
```
Needs: Node 18+, Python 3.9+, ffmpeg/ffprobe on PATH, `npm install` (in the repo root), `pip install -r requirements.txt`,
optional Kenney CC0 props (public/bridge/kenney/README.md), a voice engine in `.env` (copy `.env.example`).
A GPU is strongly recommended (WebGL via ANGLE). On Linux servers set `REMOTION_GL=egl` or `swangle`.

## 3. The pipeline - do these in order, tick STATUS.md after each

| # | Step | Command / files | Done when |
|---|------|-----------------|-----------|
| 1 | Create the short | `python tools/new_short.py <name> [script.md]` | `src/videos/<name>/`, `projects/<name>/`, composition `<Name>Short` exist |
| 2 | Facts + script | `projects/<name>/SCRIPT.md` (format: `SCRIPT_TEMPLATE.md`) | user approved |
| 3 | Voice | `python tools/voice_tts.py <name>` then `python tools/words_align.py <name>` | `voice/voice.wav` 48 kHz + `voice/words.json`, spot-checked |
| 4 | Shot plan | `src/videos/<name>/story.ts` | typecheck passes |
| 5 | World | `build.ts` (layout, buildings, props), `world.ts`, `paint.ts` only for new materials | stills show the new place |
| 6 | Characters | `cast.ts` (roles, crowds, fx cards), `toon.ts` (new faces/poses/props if needed) | stills show the cast |
| 7 | Look check | `npx tsc --noEmit`; `node tools/stills.mjs <Name>Short out/<name>/x_ <frames> 0.5`; `python tools/sbs_sheet.py ...` | no readability traps, matches references |
| 8 | Sound | edit `projects/<name>/audio/{timeline,sfx,music,mix}.py`, run `python projects/<name>/audio/mix.py` | `mix.wav`, stems, `cues.md` |
| 9 | Final | `python tools/render.py <name>` | `out/<name>/final.mp4`, QA clean |
| 10 | Deliver | tell the user the path, duration, what to review | STATUS.md complete |

### Step 2 - script formula (~3.7 words/s, 55-70 s = ~200-260 words)
Hook (the absurd fact in one line) -> Setting (year, place, pride) -> Action (3-4 escalating beats) -> Snap (the
moment it breaks) -> Deadpan double line ("Luckily ... / Unluckily ...") -> Explanation (one physics idea through an
everyday analogy) -> Consequence (the rule it created) -> Callback twist. Never describe what the viewer already sees.
Pick a story with a **visible** physical cause and effect. Example: `projects/bridge/SCRIPT.md`.

### Step 3 - voice
`TTS_ENGINE` in `.env`: `elevenlabs` (default; configure the API key once, and it returns word timings), `openai`, `manual` (user records `voice/raw.wav`), or `kokoro` (free, local; requires optional packages and a first model download). Target 55-70 s. If too long/short, tighten the script, not the speed.
Open `words.json` and fix obviously wrong times: **everything is timed to it.** Format: `[{"w","s","e"}]` in seconds.

### Step 4 - story.ts (the heart of a new short)
Rewrite it, keeping the exported names and types the other files import (`grep -n 'from "./story"' src/videos/<name>/*`):
- `FPS = 30`, `TOTAL` = voice length in frames + ~1 s tail.
- Story physics as functions of story time `tau` (positions, phases, the "snap" moment...). Replace bridge-specific
  ones (`front`, `amp`, `deckY`, `SNAP`, `DROP*`...) with your story's and update their importers (world.ts, cast.ts).
- `SHOTS`: `{id, a, b, light: "day"|"golden", crowd, tau}` - cut at sentence/beat boundaries from words.json.
- `XFADE` at place/time changes, `FLASH_AT` a white flash right after the hook.
- `CAMS`: per-shot keys `{f, dur?, cut?, s: f => {pos, look, fov, roll}}`. Grammar: hard cuts on big jumps, otherwise
  smootherstep glides of 18-40 f, every hold creeps in 0.15-0.35 %/f (0.6 %/f on punch words), rolls 4-5 deg,
  no hand-held float. `KICKS`: impact shakes that flip sign every frame and decay over 7 f.
- `DOF` / `dofAt`: lens blur cInf px at 1080: close-ups 12-16, medium 10-12, wides/aerials 0. Focus on the eyes.
- `FOREGROUND`: near framing props in about 1/3 of shots.
Work shot by shot: write a shot, render 2-3 stills of it, look, fix, then move on.

### Step 7 - verifying the look
- Stills at 0.5 take 3-8 s each after a ~40 s bundle. Render the first, middle and last frame of each shot.
- If you can see images: put your stills next to references with
  `python tools/sbs_sheet.py out/<name>/sbs.jpg --ours out/<name>/x_100.jpg ... --ref references/frames/short05_0060.jpg ...`
  and score colour day/golden, lighting, ink, textures, characters, depth, composition out of 10 with a numbered
  fix list (frame numbers). Fix, re-render, re-score. If a second model or sub-agent is available, let a fresh one score.
- If you cannot see images: rely on `tools/short_qa.py` numbers and the measured targets in `references/reports/`,
  and ask the user to look at the stills.
- Check every new prop/shot against "Readability traps" in `docs/PIPELINE_DETAILS.md`.
- Big look passes with several agents: `python tools/sandbox.py make|merge|sync <name>` (one owner per file group).

### Step 8 - sound (Python, numpy/scipy; everything synthesized, no samples)
- `timeline.py` mirrors story.ts **read-only**: copy `TOTAL`, `SHOTS`, `XFADE`, event times (snap, impacts, ...).
- `sfx.py` `cues()`: the event table -> synthesized sounds (generators in `sfx_gen.py`, DSP in `dsp.py`).
- `music.py`: original score; `SECTIONS` follow the picture; tempo may lock to on-screen rhythm (the bridge march =
  footsteps at 120 bpm). Write a new theme for each short - do not reuse the bridge melody.
- `mix.py`: section levels, ducking keyed from words.json, -15 LUFS integrated. Output `mix.wav` at exact length.
- Bridge-specific names in these files are examples; replace them with your story's events.

### Step 9 - final
`python tools/render.py <name>` renders 2K (~4 fps, ~10 min for 67 s), muxes `mix.wav`, writes `out/<name>/shots.json`
and runs frame-by-frame QA (black / white / frozen / pop frames, loudness, contact sheets in `out/<name>/qa/`).
Fix everything it flags (planned flashes, crossfades and kicks are already ignored), re-render, re-check.

## 4. File map
| Path | Role | Change per short? |
|------|------|-------------------|
| `src/videos/<name>/story.ts` | timeline, physics, shots, cameras, DOF, foreground | **always** |
| `src/videos/<name>/build.ts` | town/landscape layout, buildings, Kenney props, sight-line culling | **always (layout)** |
| `src/videos/<name>/cast.ts` | characters on stage, crowds, effect cards, walk cycles, blinks | **always (roles)** |
| `src/videos/<name>/toon.ts` | Canvas2D `Pen` character drawing API, faces (14 expressions) | add poses/props as needed |
| `src/videos/<name>/world.ts` | sky, fog, river/water, per-frame posing, sun per shot, kit loading | when the place type changes |
| `src/videos/<name>/paint.ts` | HD painted textures (brick, stone, planks, grass, water, clouds) | new materials only |
| `lights.ts`, `shade.ts`, `grade.ts`, `ink.ts`, `lensblur.ts`, `cardshade.ts`, `Bridge.tsx` | the LOOK | **no** |
| `projects/<name>/SCRIPT.md`, `STATUS.md` | script, facts, progress log | always |
| `projects/<name>/voice/` | voice.wav, words.json | always |
| `projects/<name>/audio/*.py` | SFX, score, mix | always |
| `references/` | measured style targets (reports) + reference frames/sheets | read only |
| `docs/PIPELINE_DETAILS.md` | the original full skill: every rule, value, gotcha and readability trap | read when stuck |
| `tools/` | helper commands (section 5) | no |

`docs/PIPELINE_DETAILS.md` was written for the author's own machine. Translate its paths:
`templates/bridge/` -> `src/videos/bridge/`; `~/bridge-short/` -> `projects/<name>/`; `scripts/bridge-stills.mjs` ->
`tools/stills.mjs <CompId>`; `scripts/bridge_merge.py` -> `tools/sandbox.py merge`; `scripts/bridge_shots.py` ->
`tools/shots.py`; "Opus max verifier" -> step 7 above; "SendUserFile" -> give the user `out/<name>/final.mp4`.

## 5. Tools
| Command | What it does |
|---------|--------------|
| `python tools/check_env.py` | checks Node, Python packages, ffmpeg, npm packages, Kenney props, voice keys |
| `python tools/new_short.py <name> [script]` | copies the template, registers the composition, creates STATUS.md |
| `python tools/voice_tts.py <name>` | SCRIPT.md voice-over -> voice.wav (ElevenLabs / OpenAI / Kokoro / manual) |
| `python tools/words_align.py <name>` | voice.wav -> words.json with whisper, spelling matched to the script |
| `node tools/stills.mjs <CompId> <prefix> <frames> [scale]` | renders look-check stills (`ENTRY=` for sandboxes) |
| `python tools/sbs_sheet.py out.jpg --ours ... --ref ...` | side-by-side sheet: our frames vs reference frames |
| `python tools/sandbox.py make/merge/sync <name>` | parallel look passes, one owner per file group |
| `python tools/shots.py <name>` | shots.json for QA from story.ts |
| `python tools/render.py <name>` | 2K render + mux + QA |
| `python tools/short_qa.py <mp4> <outdir> [shots.json]` | frame-by-frame QA and contact sheets |
| `python tools/import_kenney.py <folder>` | copies the needed Kenney GLB props into public/ |
| `npm run studio` | Remotion Studio: scrub the timeline in a browser |

## 6. Look values to keep (summary - full list in docs/PIPELINE_DETAILS.md)
- Light presets day (az 75 / el 48, sky #3e7fd2 -> #b8d0ec) and golden (backlit, peach horizon, violet-blue shade).
- Ink #030303, 5.1 px near -> 3.3 px far at 1080x1920; characters on layer `NOINK` with their own plum ink #241726.
- Post order: ink -> lens pre -> lens main -> bloom (thr 1.0) -> NEUTRAL tone map -> grade, MSAA 4, grain OFF.
- Characters: bean heads h/w .94, ~3.5 head-heights, stick limbs, no blush, blinks 0.5-2.3 s, walk bob 5 %.
- Every pixel-sized parameter scales with output height / 1920.

## 7. Gotchas
- Every Remotion bundle copies `public/` into the temp folder and never deletes it: the tools set TEMP to
  `REMOTION_TMP`. Clean old `remotion-webpack-bundle-*` folders there when nothing is rendering (ask the user first).
- Remotion writes a silent audio track: mux with `-map 0:v:0 -map 1:a:0` (render.py does this).
- Ink must be its own pass before the blur. Cameras inside houses: the sight-line culler in build.ts removes blockers.
- Kenney nature-kit materials are teal: recolour by material name in build.ts.
- Scratch `.ts` files inside `out/` break `tsc`: name them `.txt`.
- In JS strings use forward slashes in paths (`\r` becomes a carriage return).
