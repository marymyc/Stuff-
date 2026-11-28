# Audio, TTS & Mastering Spec (`scripts/gen_voice.py` & `scripts/make_audio.py`)

## 1. Narration Synthesis (Fish Audio `s2-pro`)
- Pass the API key exclusively via environment variable (`FISH_API_KEY`). Never store keys inside project files or scripts.
- **Verified Public Storytelling Voices:**
  - **English US Shorts Storyteller:** `reference_id = "b0204e37cbc94a16954c78697b844af2"` (`s2-pro`, median `F0 ~ 190.5 Hz`, `p25=147.5`, `p75=222.2` matching energetic American YouTube Shorts delivery).
  - **Indonesian Deep Baritone:** `reference_id = "090af282b9204275ace6fd7aecbf5748"` (`s2-pro`, warm lower male narration).
- **Recommended Payload Settings:**
  - `model` HTTP header: `"s2-pro"`
  - `prosody`: `{"speed": 1.16}` (`1.14-1.20` for brisk Shorts rhythm)
  - `temperature: 0.58`, `top_p: 0.68`, `normalize: true`
- **Post-TTS Cleanup & Fit (`gen_voice.py`):**
  - Strip edge dead-air with `-55 dB` threshold (`silenceremove=start_periods=1:start_threshold=-55dB:start_silence=0.03...`), keeping `0.05 s` tail breath room so endings never clip.
  - Fit line duration inside shot slots (`[target_f0, target_f1]`) with `atempo <= 1.22` (rewrite text shorter if natural speech ratio would exceed `1.20x`).
  - Vocal EQ chain: `highpass=f=75` (EN) or `f=60` (baritone warmth), `acompressor=threshold=-17dB:ratio=2.4:attack=4:release=55`, `aresample=48000`.
  - Keep separate TTS cache folders per language (e.g., `_lines_fish_en`) so stale cached MP3 lines never leak between revisions.

## 2. Word Alignment (`words.json`)
- Align synthesized fitted `.wav` segments with `faster-whisper` (`WhisperModel("small", device="cpu", compute_type="int8")`, `word_timestamps=True`, `initial_prompt=text`, explicit `language="en"` or `"id"`).
- Map Whisper word intervals deterministically back onto exact display punctuation tokens via `SequenceMatcher`, then enforce strictly non-overlapping monotonic `(s, e)` spans bounded by `totalFrames / 30`.
- Validate after running: confirm zero zero-length/negative intervals and `100%` monotonic word start order.

## 3. Procedural Music, Frame-Locked SFX & Mastering (`make_audio.py`)
- Lock shot cut frames and hero reaction frames (`FLASH_AT`, impact frames, reveal beats) in `src/scene/story.ts` BEFORE building audio cues. Place SFX strictly at `frame / 30.0`.
- Balance stems relative to integrated voice loudness before sidechain ducking:
  - Music bed ~ `-11.5 dB` below voice (`dsp.integrated`)
  - SFX bus ~ `-9.0 dB` below voice
- Apply smooth `ndimage.uniform_filter1d` ducking curve from `words.json`: `-5.2 dB` on music during speech (`-2.3 dB` on SFX).
- Master final `public/audio/mix.wav` (`48000 Hz`, 24-bit stereo) via iterative BS.1770-4 limiting to **`-15.0 LUFS`**, True Peak ceiling **`-1.2 dBTP`**, LRA `~1.5-2.5 LU`, then mux into final MP4 (`-c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest`).

