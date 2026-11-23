"""Audio mix, shot joining (cuts + dissolves), caption burn-in, final MP4."""
from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from .config import video_fps
from .sfx import SR, render_track

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts"]


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))[:300]}\n{r.stderr[-1500:]}")
    return r


def probe_duration(path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(r.stdout)["format"]["duration"])


def ffmpeg_has_filter(name) -> bool:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return any(f" {name} " in line for line in out.splitlines())


def encode_frames_dir(frames_dir, fps, out_mp4, pattern="f_%04d.png", out_fps=None):
    """PNG sequence -> clip. If out_fps > fps, frames are duplicated up (cheap 'on twos' look)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(frames_dir) / pattern), "-an",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    if out_fps and int(out_fps) != int(fps):
        cmd += ["-r", str(int(out_fps))]
    run(cmd + [str(out_mp4)])


def build_mix(timeline, cfg, out_wav, with_sfx=True) -> str:
    total = timeline["total_seconds"]
    voice = np.zeros(int(SR * total) + SR, dtype=np.float32)
    for s in timeline["shots"]:
        x, sr = sf.read(s["voice_wav"], dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        if sr != SR:
            g = gcd(sr, SR)
            x = resample_poly(x, SR // g, sr // g).astype(np.float32)
        i = int((s["start"] + s["voice_offset"]) * SR)
        voice[i:i + len(x)] += x[: len(voice) - i]
    mix = voice[: int(SR * total)]
    if with_sfx and cfg["sfx"]["enabled"]:
        ev = [(e["name"], s["start"] + e.get("at", 0.0), e.get("gain", 1.0)) for s in timeline["shots"] for e in s.get("sfx", [])]
        mix = mix + render_track(ev, total, cfg["sfx"]["volume"])[: len(mix)]
    peak = float(np.max(np.abs(mix))) or 1.0
    if peak > 0.89:
        mix = mix / peak * 0.89
    sf.write(out_wav, mix, SR)
    return str(out_wav)


def join_video(clips, timeline, cfg, out_mp4):
    d = cfg["transitions"]["dissolve_seconds"]
    fps = video_fps(cfg)
    shots = timeline["shots"]
    segs = []
    for i, s in enumerate(shots):
        if i > 0 and s["transition"] == "dissolve":
            segs.append([i])          # dissolve boundary: new segment, joined by xfade
        elif i == 0:
            segs.append([i])
        else:
            segs[-1].append(i)        # hard cut: plain concat inside a segment
    lens = {i: probe_duration(clips[i]) for i in range(len(clips))}
    parts, labels = [], []
    for k, seg in enumerate(segs):
        if len(seg) == 1:
            parts.append(f"[{seg[0]}:v]settb=AVTB,fps={fps}[s{k}]")
        else:
            parts.append("".join(f"[{i}:v]" for i in seg) + f"concat=n={len(seg)}:v=1:a=0,settb=AVTB,fps={fps}[s{k}]")
        labels.append(sum(lens[i] for i in seg))
    if len(segs) == 1:
        parts.append("[s0]null[vout]")
    else:
        cum, prev = labels[0], "s0"
        for k in range(1, len(segs)):
            nxt = "vout" if k == len(segs) - 1 else f"x{k}"
            parts.append(f"[{prev}][s{k}]xfade=transition=fade:duration={d}:offset={cum - d:.3f}[{nxt}]")
            cum = cum + labels[k] - d
            prev = nxt
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "16", "-pix_fmt", "yuv420p", str(out_mp4)]
    run(cmd)


def burn_and_mux(video, wav, ass_path, out_mp4, total):
    video, wav, ass_path, out_mp4 = (Path(x).resolve() for x in (video, wav, ass_path, out_mp4))
    work = video.parent
    have_ass = ffmpeg_has_filter("ass") and Path(ass_path).exists()
    vf = []
    if have_ass:
        fd = next((p for p in FONT_DIRS if Path(p).exists()), None)
        vf = ["-vf", f"ass={Path(ass_path).name}" + (f":fontsdir={fd}" if fd else "")]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", Path(video).name, "-i", Path(wav).name, *vf, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{total:.3f}", "-movflags", "+faststart", str(out_mp4)]
    run(cmd, cwd=str(work))
    return have_ass


def verify_output(path, width, height, expected_seconds) -> dict:
    r = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-show_entries", "format=duration",
             "-of", "json", str(path)])
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    kinds = {s["codec_type"] for s in j["streams"]}
    dur = float(j["format"]["duration"])
    return {"width": v["width"], "height": v["height"], "duration": round(dur, 2), "has_audio": "audio" in kinds,
            "ok": v["width"] == width and v["height"] == height and "audio" in kinds and abs(dur - expected_seconds) < 0.6}
