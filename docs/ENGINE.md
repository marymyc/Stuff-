# Engine: plan-driven toon shorts (Remotion + three.js)

`engine/` is the user's `animated-shorts-template` (same code as the `claude-animated-shorts` skill; only the packaging differs),
plus a generic layer so that **one script produces one video** without rewriting bridge-specific files.

## Why it replaces Blender as the default
Look fidelity: 2D bean-head characters (14 expressions, outfits, lit cards), painted HD textures, ink pass, thin-lens blur, colour grade,
camera grammar measured from 20 reference shorts. The Blender path (`src/stuff/blender`) is kept as a fallback.

## What was added (engine/src/engine, engine/tools)
| File | Role |
|---|---|
| `plan.ts` | the JSON contract (shots, cast, props, fx, words) + crossfade layers |
| `camera.ts` | plan-driven camera: ease-out glide, creeping holds, dutch roll on the punch |
| `sets.ts` | procedural sets: field, fortress, canyon (rails), interior, town + props. No Kenney download needed |
| `stage.ts` | outfits per role, expressions, blinks, contact shadows, burst/puff/stars fx |
| insert shots | `PlanShot.focus` -> `sets.buildFocus()` (coin, paper, calendar, newspaper, caliper, thermometer, moneybag, map, clock, marble), tight low camera in `camera.ts` |
| `world.ts` | the bridge world's sky / light rig / clouds / cast plumbing, driven by the plan |
| `Short.tsx` | composition (ink -> blur -> bloom -> grade) + word-by-word captions (1-2 words, ~70 % height) |
| `tools/make_plan.py` | script -> plan.json, reusing `stuff.planner` + Chatterbox voice + timeline |
| `tools/make.py` | one command: plan -> voice -> SFX mix -> Remotion render -> mux |
| `tools/gpu_probe.py` | tells whether Chromium reaches a real GPU (software GL = minutes per frame) |

## Weak points of the original and what was done
| Weak point | Status |
|---|---|
| Story code written per short (`story.ts`, `build.ts`, `cast.ts`, `world.ts`) | generic layer added; sets/cast/camera now come from the plan |
| No captions | added (`Short.tsx`) |
| No Chatterbox | voice comes from `stuff.tts` (Chatterbox, fixed seed/identity) |
| Manual Kenney props | procedural sets and props instead |
| Sound timeline copied by hand from `story.ts` | SFX events and voice offsets are written into the plan and mixed automatically |
| Only `day` / `golden` light presets | still only these two (`night` maps to `golden`); a real night preset is open |
| Original `Bridge.tsx` did not typecheck | fixed |
| Needs a GPU | unchanged. Measured here: ~2.4 min per frame with software GL, so rendering is only practical on a GPU |

## Character motion (rubber-hose style)
Limbs are thin pure-black strokes (`Outfit.limb = INK`), each a 3-point curve (shoulder-elbow-hand, hip-knee-foot), so they bend; walking swings
arms and lifts feet on a sine cycle. Added on top: a **spring** (`spring()` in `stage.ts`: overshoots ~23 % then settles) driving cane pointing,
hops and landings; idle sway (tilt/head tilt) so nobody freezes; `action` per character from the plan: `point` (cane), `wave`, `sit`, `hop`, `stroll`.
The boss (`tycoon`) always carries a cane. Not verified visually: cane pose, sit pose, hop. Not implemented: elastic foot rebound on every step.

## Rules
- **Renders are run by the user only** (their GPU / Colab). The assistant and CI never render; CI does typecheck + plan only.
- `engine/references/` (third-party frames) is not published.

## Verification status
- Typecheck of the whole engine: passes. Plan generation from the sample scripts: passes.
- Two software-GL stills of the generic layer were seen (canyon, hero/tycoon, captions) and looked in-style. After them the ground height
  and screen-side placement were changed and have NOT been seen rendered.
- Checked without rendering: tsc, 11 unit tests (incl. the plan contract and insert shots), plans + audio mix for the 3 sample scripts, notebook validity.
- Not verified: any full video, the new insert-shot objects, GPU rendering on Colab, the castle/interior/town/field sets, Chatterbox inside this pipeline.
