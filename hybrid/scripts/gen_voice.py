"""Generate energetic narration (Fish Audio s2-pro) + Whisper word timestamps."""
from difflib import SequenceMatcher
import json
import os
import re
import subprocess
import numpy as np
import requests
from faster_whisper import WhisperModel
from dsp import SR, ns, read_wav, write_wav, st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VOICE_DIR = os.path.join(ROOT, "public", "audio")
CACHE_DIR = os.path.join(VOICE_DIR, "_lines_fish")
os.makedirs(CACHE_DIR, exist_ok=True)

# Public Fish Audio s2-pro voice IDs tested for Shorts storytelling:
#   English US Shorts Storyteller (~190 Hz F0): "b0204e37cbc94a16954c78697b844af2"
#   Indonesian Deep Baritone      (~118 Hz F0): "090af282b9204275ace6fd7aecbf5748"
VOICE_NAME = os.environ.get("VOICE_NAME", "US Shorts Storyteller")
REF_ID = os.environ.get("FISH_REF_ID", "b0204e37cbc94a16954c78697b844af2")
WHISPER_LANG = os.environ.get("WHISPER_LANG", "en")
MODEL_HDR = "s2-pro"

# Replace SCRIPT_LINES with your story beats! Aim for ~3.5-4.1 words/sec per slot.
# Tuple format: (line_id, display_text, tts_text, speed, gap_sec, target_f0, target_f1)
SCRIPT_LINES = [
    (
        "hook",
        "This deadly curve hid a clever brain trick!",
        "This deadly curve hid a clever brain trick!",
        1.16,
        0.20,
        0,
        75,
    ),
    (
        "twist",
        "Turns out simple paint fooled speeding drivers into braking fast.",
        "Turns out, simple paint fooled speeding drivers into braking fast!",
        1.16,
        0.25,
        75,
        150,
    ),
]


def norm_word(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def align_tokens(display_tokens: list[str], raw_words: list[tuple[str, float, float]], total_dur: float) -> list[dict]:
    """Map Whisper acoustic word intervals onto exact display tokens cleanly."""
    n = len(display_tokens)
    if not raw_words:
        step = total_dur / max(1, n)
        return [{"w": tok, "s": i * step, "e": (i + 1) * step} for i, tok in enumerate(display_tokens)]

    exp_norm = [norm_word(t) for t in display_tokens]
    got_norm = [norm_word(w[0]) for w in raw_words]

    sm = SequenceMatcher(None, exp_norm, got_norm, autojunk=False)
    anchors: list[tuple[int, float, float]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                _, ws, we = raw_words[j1 + k]
                anchors.append((i1 + k, ws, we))
        elif tag == "replace" and i2 > i1 and j2 > j1:
            span_s = raw_words[j1][1]
            span_e = raw_words[j2 - 1][2]
            cnt = i2 - i1
            for k in range(cnt):
                anchors.append((
                    i1 + k,
                    span_s + (span_e - span_s) * (k / cnt),
                    span_s + (span_e - span_s) * ((k + 1) / cnt),
                ))

    starts: list[float | None] = [None] * n
    ends: list[float | None] = [None] * n
    for idx, ws, we in anchors:
        starts[idx] = ws
        ends[idx] = we

    last_t = max(0.0, raw_words[0][1])
    i = 0
    while i < n:
        if starts[i] is not None:
            last_t = float(ends[i])  # type: ignore[arg-type]
            i += 1
            continue
        j = i
        while j < n and starts[j] is None:
            j += 1
        next_t = float(starts[j]) if j < n else raw_words[-1][2]  # type: ignore[arg-type]
        next_t = max(last_t + 0.05 * (j - i), next_t)
        cnt = j - i
        for k in range(cnt):
            starts[i + k] = last_t + (next_t - last_t) * (k / cnt)
            ends[i + k] = last_t + (next_t - last_t) * ((k + 1) / cnt)
        last_t = next_t
        i = j

    out = []
    prev_e = 0.0
    for idx, tok in enumerate(display_tokens):
        s = max(prev_e, float(starts[idx] or 0.0))
        e = max(s + 0.05, min(total_dur, float(ends[idx] or (s + 0.05))))
        out.append({"w": tok, "s": s, "e": e})
        prev_e = s
    return out


def synth_and_fit(
    idx: int,
    lid: str,
    text: str,
    tts_text: str,
    speed: float,
    target_speech_dur: float,
    whisper_model: WhisperModel,
):
    mp3 = os.path.join(CACHE_DIR, f"{idx:02d}_{lid}_raw.mp3")
    trimmed_wav = os.path.join(CACHE_DIR, f"{idx:02d}_{lid}_raw.wav")
    final_wav = os.path.join(CACHE_DIR, f"{idx:02d}_{lid}_fit.wav")

    if not os.path.exists(mp3):
        api_key = os.environ.get("FISH_API_KEY")
        if not api_key:
            raise RuntimeError("FISH_API_KEY env var is required to synthesize narration lines.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": MODEL_HDR,
        }
        payload = {
            "text": tts_text,
            "reference_id": REF_ID,
            "format": "mp3",
            "normalize": True,
            "latency": "normal",
            "temperature": 0.58,
            "top_p": 0.68,
            "prosody": {"speed": speed},
        }
        r = requests.post("https://api.fish.audio/v1/tts", headers=headers, json=payload, timeout=45)
        r.raise_for_status()
        with open(mp3, "wb") as f:
            f.write(r.content)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", mp3,
            "-af", "silenceremove=start_periods=1:start_threshold=-55dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-55dB:start_silence=0.05,areverse,aresample=48000",
            "-ac", "1", "-c:a", "pcm_s16le", trimmed_wav,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    raw_mono, _ = read_wav(trimmed_wav)
    raw_mono = raw_mono[0] if raw_mono.ndim > 1 else raw_mono
    raw_dur = len(raw_mono) / SR

    tempo = max(1.0, min(1.22, raw_dur / max(0.5, target_speech_dur)))
    af_chain = []
    if tempo > 1.005:
        af_chain.append(f"atempo={tempo:.4f}")
    af_chain.append("highpass=f=75" if WHISPER_LANG == "en" else "highpass=f=60")
    af_chain.append("acompressor=threshold=-17dB:ratio=2.4:attack=4:release=55")
    af_chain.append("aresample=48000")

    subprocess.run(
        ["ffmpeg", "-y", "-i", trimmed_wav, "-af", ",".join(af_chain), "-ac", "1", "-c:a", "pcm_s16le", final_wav],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    x, _ = read_wav(final_wav)
    mono = x[0] if x.ndim > 1 else x
    dur = len(mono) / SR
    fade = min(ns(0.01), len(mono) // 4)
    if fade > 0:
        mono = mono.copy()
        mono[:fade] *= np.linspace(0, 1, fade)
        mono[-fade:] *= np.linspace(1, 0, fade)

    segs, _ = whisper_model.transcribe(final_wav, language=WHISPER_LANG, initial_prompt=text, word_timestamps=True)
    w_words = [(w.word.strip(), float(w.start), float(w.end)) for seg in segs for w in (seg.words or [])]
    aligned = align_tokens(text.split(), w_words, dur)
    for w in aligned:
        w["line"] = lid
    print(f"  [{idx:02d}] {lid:13s}: raw={raw_dur:.2f}s -> fit={dur:.2f}s (atempo={tempo:.3f}x), words={len(aligned)}")
    return mono, aligned


def main() -> None:
    print("Loading faster-whisper small alignment model...")
    wmodel = WhisperModel("small", device="cpu", compute_type="int8")

    chunks = []
    all_words = []
    line_spans = {}
    lead_in = 0.08
    cur_t = lead_in
    chunks.append(np.zeros(ns(lead_in)))

    for idx, (lid, text, tts_text, speed, gap, f0, f1) in enumerate(SCRIPT_LINES):
        slot_end_s = f1 / 30.0
        target_dur = max(0.8, slot_end_s - cur_t - gap)
        seg, words = synth_and_fit(idx, lid, text, tts_text, speed, target_dur, wmodel)
        start_s = cur_t
        for w in words:
            ws = start_s + w["s"]
            we = start_s + w["e"]
            all_words.append({
                "w": w["w"],
                "s": round(ws, 4),
                "e": round(we, 4),
                "startMs": round(ws * 1000),
                "endMs": round(we * 1000),
                "line": lid,
            })
        dur_line = len(seg) / SR
        actual_gap = max(0.08, slot_end_s - (start_s + dur_line))
        line_spans[lid] = {
            "s": round(start_s, 3),
            "e": round(start_s + dur_line, 3),
            "f0": int(round(start_s * 30)),
            "f1": int(round((start_s + dur_line + actual_gap) * 30)),
        }
        chunks.append(seg)
        chunks.append(np.zeros(ns(actual_gap)))
        cur_t += dur_line + actual_gap

    full_mono = np.concatenate(chunks)
    total_frames = SCRIPT_LINES[-1][6]
    exact_dur = total_frames / 30.0
    target_n = ns(exact_dur)
    full_mono = np.pad(full_mono, (0, max(0, target_n - len(full_mono))))[:target_n]

    voice_wav = os.path.join(VOICE_DIR, "voice.wav")
    write_wav(voice_wav, st(full_mono), bits=24)

    out = {
        "voice": f"fish-audio:{VOICE_NAME}:{REF_ID}",
        "model": MODEL_HDR,
        "durationSec": round(exact_dur, 4),
        "totalFrames": total_frames,
        "lines": line_spans,
        "words": all_words,
    }
    with open(os.path.join(VOICE_DIR, "words.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"voice.wav written: {exact_dur:.3f}s ({total_frames} frames), {len(all_words)} words")


if __name__ == "__main__":
    main()
