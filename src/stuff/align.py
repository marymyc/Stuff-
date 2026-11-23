"""Word timing + timeline. Default: proportional (deterministic). Optional: faster-whisper word timestamps."""
from __future__ import annotations

import re

_WHISPER = None


def word_weights(words):
    out = []
    for x in words:
        base = len(re.sub(r"\W", "", x)) + 1.5
        if x[-1] in ",;:":
            base += 2.5
        if x[-1] in ".!?":
            base += 4.0
        out.append(base)
    return out


def proportional_words(text, start, end):
    words = text.split()
    if not words:
        return []
    w = word_weights(words)
    tot, t, out = sum(w), start, []
    for word, wt in zip(words, w):
        dt = (end - start) * wt / tot
        out.append({"word": word, "start": round(t, 3), "end": round(t + dt, 3)})
        t += dt
    return out


def whisper_words(wav_path, text, offset):
    global _WHISPER
    from faster_whisper import WhisperModel

    if _WHISPER is None:
        _WHISPER = WhisperModel("base.en", device="cpu", compute_type="int8")
    segs, _ = _WHISPER.transcribe(wav_path, word_timestamps=True)
    got = [w for s in segs for w in (s.words or [])]
    script = text.split()
    if len(got) != len(script):
        return None
    return [{"word": sw, "start": round(offset + g.start, 3), "end": round(offset + g.end, 3)}
            for sw, g in zip(script, got)]


def build_timeline(plan, manifest, cfg) -> dict:
    v = cfg["voice"]
    gap, lead = v["gap_seconds"], v["lead"]
    d_diss = cfg["transitions"]["dissolve_seconds"]
    t, shots = 0.0, []
    for shot, m in zip(plan["shots"], manifest["shots"]):
        a = m["duration"]
        dur = max(1.4, lead + a + gap)
        words = None
        if cfg["align"]["backend"] == "whisper":
            try:
                words = whisper_words(m["wav"], shot["text"], lead)
            except Exception:
                words = None
        if words is None:
            words = proportional_words(shot["text"], lead, lead + a)
        shots.append({**shot, "start": round(t, 3), "duration": round(dur, 3), "voice_wav": m["wav"],
                      "voice_offset": lead, "audio_seconds": a, "words": words})
        t += dur
    shots[-1]["duration"] = round(shots[-1]["duration"] + cfg["video"]["tail_hold"], 3)
    t += cfg["video"]["tail_hold"]
    for i, s in enumerate(shots):
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        s["render_seconds"] = round(s["duration"] + (d_diss if nxt and nxt["transition"] == "dissolve" else 0.0), 3)
    return {"title": plan.get("title", ""), "total_seconds": round(t, 3), "shots": shots}
