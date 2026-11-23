# Operator guide for AI models

**The user gives you ONE input: the English narration script.** Do not ask for anything else
(no style choices, camera, voice, scenes). Defaults are in `config/default.json`.

## Steps
1. Save the script as `script.txt` (about 150-170 words for 60-70 s; the CLI warns if the timeline is outside 55-75 s).
2. `python -m stuff preflight --mode light` (Colab: add `--mode all` before a long render).
3. `python -m stuff plan script.txt --workdir work/x` and read `work/x/plan.json`.
   You MAY edit it to improve the result (kit, shot_size, camera_move, expression, sfx, emphasis); schema: `docs/PLAN_SCHEMA.md`.
   Keep the style rules in `docs/STYLE_GUIDE.md` (shot every 2-3 s, no 3 equal shot sizes in a row, dissolve only for time jumps).
4. `python -m stuff make script.txt --plan work/x/plan.json --workdir work/x --name final`
5. Open `work/x/final.mp4` checks in `work/x/report.json` (`ok` must be true). Tell the user the file path.

## Rules
- Narration and captions are English. Never change the voice settings between shots or videos (identity = `voice_manifest.json` fingerprint).
- A user-supplied reference voice goes in `assets/voice/` and is passed with `--ref-voice`. Never commit audio or keys.
- When something fails, read the traceback, fix the cause in `src/`, re-run. Do not claim success without a passing `report.json`.
- CI results are pushed to branch `ci-report` (`<job>/…`); read them there before declaring a stage verified.
