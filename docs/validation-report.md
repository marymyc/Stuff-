# Validation report

Source of truth: GitHub Actions runs on `main`, reports pushed to branch `ci-report` (one folder per job).
Last verified commit: `b1bf737`.

## Verified on GitHub Actions
| Stage | Result |
|---|---|
| Unit tests (10) + light preflight (ffmpeg with libass/xfade, DejaVu font) | pass |
| Full pipeline, silent voice + preview renderer, 15-shot sample script | pass |
| Blender 4.2.0 (`pip bpy`) renders 4 kits (fortress, canyon, interior, field) with sprites, props, explosion, dutch roll | pass, previews in `ci-report/preflight-blender/` |
| Full pipeline with real Blender (tiny 180x320, Cycles CPU 2 samples): 120 frames at 0.47 s/frame, 58.7 s total | pass (`ok: true`, captions burned) |
| Chatterbox `chatterbox-tts 0.1.7` + torch 2.6.0 (CPU): load 40 s, two sentences generated (27-47 s each on CPU) | pass |
| Voice identity metrics (default voice): f0 median 124 / 132 Hz, spectral correlation between sentences 0.984 | pass (crude metric) |
| Full pipeline with real Chatterbox voice + preview renderer: 11.8 s video, 126 s on CPU | pass |

## NOT verified yet (be honest before relying on it)
- A full 60-70 s video at 720x1280 with Blender **and** Chatterbox together. Only tiny/short runs were executed.
- Google Colab itself: the notebook was never run in Colab. GPU Cycles device selection and the Blender 4.2.3 tarball download are untested.
- Full-scale render time. Measured 0.47 s/frame at 180x320 / 2 samples on a 2-core CPU runner; 720x1280 at 24 samples on CPU would be far slower, so use a GPU runtime.
- `--align whisper` and `--ref-voice` paths (code exists, not exercised in CI).
- "American" accent: not measurable automatically. The default Chatterbox voice measured in the adult-male pitch range; supply a reference clip to lock the identity.
- Visual parity with the reference videos: characters are simple procedural sprites and environments are low-poly kits.

## Problems found while testing, and fixes
1. `keyframe_insert("angle")` raised `TypeError: property "angle" not animatable` on real Blender 4.2 -> camera FOV is animated through `lens` (vertical sensor fit).
2. Caption burn-in failed for relative `--workdir` (ffmpeg ran with a different cwd). Local tests had used absolute paths so they passed -> all paths resolved, regression test `test_relative_workdir` added.
3. CI hid failures: `cmd | tee log` returned success even when the command failed -> workflows now use `shell: bash` (pipefail) and cancel stale runs.
4. `xfade` timebase mismatch between concat output and single clips -> every segment is normalised with `settb=AVTB,fps=N`.
5. Dissolve/cut logic was inverted (ghost frames on every cut) -> only `dissolve` shots start a new xfade segment; hard cuts use `concat`.
6. Real previews showed: overexposed day light (sun 4.0 -> 2.4), characters cropped on close shots (fixed spacing -> spacing per shot size), tiny heroes in wide shots (x2.2 scale), smoke sphere hiding the fireball (re-layered, softer emission), dark interior (own point light).
7. Scene build + render was slow (first end-to-end 174 s for 117 tiny frames) -> Cycles max bounces 3, adaptive sampling, persistent data, Blender renders at 15 fps and FFmpeg duplicates frames to 30 fps (58.7 s afterwards; setting changes, not a controlled benchmark).
8. First heavy voice run sat >8 min in the apt step and was cancelled; the re-run passed. Cause not investigated.
9. The repository already contained a stale bootstrap workflow and README from an earlier attempt; they had been deleted before this build started and nothing from them was used.

## Engine (engine/)
CI (`engine.yml`) runs typecheck and plan generation only. Renders are never run by the assistant or CI (see `docs/ENGINE.md`).
