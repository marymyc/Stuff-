# Hybrid pipeline (default): Blender 3D world + 2D toon cast cards

`hybrid/` is built on **ricks-clip-skill** (MIT, see `hybrid/NOTICE.md`), which is the evolution of the `animated-shorts-template`.
The 3D world is rendered by **Blender** (Cycles on a GPU through CUDA/OptiX, so no OpenGL is needed); the characters are exported as
transparent **cards drawn with Canvas2D** (no WebGL), placed in the scene as upright billboards; captions (libass) and audio are muxed by ffmpeg.

```
script.txt -> tools/make_hybrid_plan.py  -> public/plan.json, audio/words.json, voice.wav, mix.wav   (planner + Chatterbox, no render)
           -> scripts/export-cards.mjs   -> out/cards (PNG cards + manifest with camera path)          (Canvas2D)
           -> scripts/blender_render.py  -> out/blender_frames  (loads scripts/blender_scene.py)       (Blender, GPU)
           -> scripts/composite_stage2.mjs -> out/<name>.mp4  (captions + audio)
```
Run everything with `python hybrid/tools/make.py script.txt --name short1` (Colab: `notebooks/colab_hybrid.ipynb`). **Renders are run by the user only.**

## What was added on top of the upstream project
| Piece | Purpose |
|---|---|
| `src/scene/story.ts`, `cards.ts` | read `public/plan.json`: shots, camera grammar, light, cast, actions (point/wave/sit/hop/stroll), fx |
| `scripts/blender_scene.py` | generic set library: field, fortress, canyon (rails), interior, town; props; insert objects (coin, paper, calendar, newspaper, caliper, thermometer, moneybag, map, clock, marble); one zone per set, per-shot visibility |
| `tools/make_hybrid_plan.py` | script -> plan (shots, zones, camera, cast), words, Chatterbox voice, SFX mix at -15 LUFS |
| `tools/make.py` | the one command |
| `tools/check_scene_build.py` | builds all sets in bpy WITHOUT rendering (CI) |
| `limb` outfit field | thin pure-black arms and legs like the references |
| `validate_plan.py` | accepts Chatterbox; word-rate and shot-length thresholds loosened for this pipeline (~3 s shots) |

## Status
Verified without rendering: typecheck of the whole project, plan + validator (40/40 on the sample), unit tests, Blender scene BUILD under bpy 4.2 in CI.
Not verified: any rendered frame, Blender 5.2 API differences (CI uses 4.2), Cycles GPU on Colab, the look of the sets, cards on Colab Chrome.
Known gaps: the boss's cane (present only in `engine/`), per-story hand-authored sets of the upstream skill are replaced by the generic library (simpler), no music bed yet.
