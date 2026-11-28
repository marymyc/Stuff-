# Attribution
`hybrid/` is built on **ricks-clip-skill** (MIT, Copyright (c) 2026 JosuaZxz): the toon character engine (`src/engine/*`), card export
(`scripts/export-cards.mjs`), Blender compositing renderer (`scripts/blender_render.py`), caption/mux (`scripts/composite_stage2.mjs`),
audio DSP (`scripts/dsp.py`, `instruments.py`, `sfx_gen.py`) and QA scripts, which descend from the same author's animated-shorts template.
Changes in this repository: plan-driven `src/scene/story.ts` / `cards.ts`, a generic Blender set library (`scripts/blender_scene.py`),
Chatterbox voice + planner (`tools/`). The original license is in `LICENSE`.
