# Architecture

1. **plan** (`planner.py`): sentences -> beats of 6-9 words -> one shot each; keyword rules pick kit, time of day, expression, shot size, camera move, SFX.
2. **voice** (`tts.py`): one model load, one conditioning, fixed seed per shot, silence trimmed. `voice_manifest.json` stores a fingerprint; cached per shot.
3. **timeline** (`align.py`): shot duration = lead + audio + gap; word times proportional (or faster-whisper with `--align whisper`); dissolve shots are rendered `dissolve_seconds` longer so the xfade keeps sync.
4. **render**: `blender` (production) writes PNG frames per shot, encoded to `clips/shot_XXX.mp4`; `pil` (preview/CI) pipes frames straight to ffmpeg. Both produce identical clip timing.
5. **compose** (`compose.py`): hard cuts via `concat`, dissolves via `xfade`; voice and SFX mixed in numpy at 48 kHz; ASS captions burned with libass; AAC + H.264 `+faststart`; `verify_output` checks size, audio and duration.

Blender specifics: characters are textured planes with `COPY_ROTATION` from the camera (billboards) and an emission/alpha material plus a blob shadow; the camera is a child of a `TRACK_TO` rig so roll (dutch) is animated on the camera itself; vertical FOV (`sensor_fit=VERTICAL`).
