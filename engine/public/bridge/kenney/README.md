# Kenney CC0 3D props

The world loads these `.glb` models (trees, bushes, lanterns, stalls, banners, windmill, canoe).
They are **not** included in the repo. Missing models are skipped, so a render still works,
but the town looks much emptier.

1. Download (free, CC0) from https://kenney.nl/assets :
   - **Nature Kit**  (tree_oak, plant_bush, flower_redA, grass, lily_large, canoe ...)
   - **Fantasy Town Kit** (lantern, cart, stall-red, banner-red, windmill, hedge ...)
2. Unzip them anywhere, then run:
   `python tools/import_kenney.py <folder-with-the-unzipped-kits>`
   It finds the GLB files listed in `src/videos/bridge/world.ts` (const KENNEY) and copies them here.
3. Check with `python tools/check_env.py`.
