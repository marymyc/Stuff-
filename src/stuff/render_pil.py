"""Fast fallback/preview renderer (Pillow). Same plan -> same clips, no Blender needed.
Used for CI timing/sync/compose tests and quick previews; the production look comes from Blender."""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .config import video_fps, video_size

TOD = {"day": ((46, 115, 242), (190, 224, 255)), "dawn": ((90, 100, 190), (255, 184, 128)),
       "dusk": ((70, 56, 140), (255, 140, 90)), "night": ((6, 8, 30), (20, 26, 64))}
K = 1.4
CHAR_FRAC = {"close": 0.66, "medium": 0.44, "medium_low": 0.52, "wide": 0.22}
MOVES = {  # zoom0, zoom1, pan_x0, pan_x1, pan_y0, pan_y1 (fractions of W/H), rot0, rot1 (deg)
    "fly_forward": (0.85, 1.35, 0, 0, 0.02, -0.05, 0, 0), "pull_back": (1.4, 0.9, 0, 0, 0, 0, 0, 0),
    "orbit_slow": (1.05, 1.15, -0.06, 0.06, 0, 0, 0, 0), "push_in": (1.0, 1.45, 0, 0, 0, 0, 0, 0),
    "push_in_low": (1.0, 1.35, 0, 0, 0.05, 0, 0, 0), "slide": (1.3, 1.3, -0.1, 0.1, 0, 0, 0, 0),
    "dutch_push": (1.0, 1.35, 0, 0, 0, 0, 0, 10),
}


def _ease(t):
    return t * t * (3 - 2 * t)


def _background(kit, tod, BW, BH):
    top, hor = TOD.get(tod, TOD["day"])
    g = np.linspace(0, 1, BH)[:, None, None]
    arr = (np.array(top) * (1 - g) + np.array(hor) * g) * np.ones((1, BW, 1))
    img = Image.fromarray(arr.astype("uint8"), "RGB")
    d = ImageDraw.Draw(img)
    hz = int(BH * 0.55)
    night = tod == "night"
    if kit == "canyon":
        d.rectangle((0, hz, BW, BH), fill=(205, 120, 70) if not night else (60, 40, 50))
        for i in range(14):
            y = int(BH * 0.1 + i * BH * 0.045)
            col = [(200, 70, 50), (240, 140, 60), (200, 60, 120)][i % 3]
            d.polygon([(BW * 0.62, y), (BW, y - BH * 0.05), (BW, y + BH * 0.04), (BW * 0.66, y + BH * 0.045)], fill=col)
        for k in range(-4, 5):
            d.line((BW * 0.5 + k * BW * 0.03, hz, BW * 0.5 + k * BW * 0.5, BH), fill=(70, 55, 50), width=max(2, BW // 120))
    elif kit == "fortress":
        d.rectangle((0, hz, BW, BH), fill=(70, 150, 60) if not night else (20, 50, 30))
        d.rectangle((BW * 0.05, hz - BH * 0.22, BW * 0.95, hz), fill=(140, 140, 146))
        for x in range(int(BW * 0.05), int(BW * 0.95), max(8, BW // 18)):
            d.rectangle((x, hz - BH * 0.25, x + BW // 36, hz - BH * 0.22), fill=(140, 140, 146))
        d.pieslice((BW * 0.4, hz - BH * 0.17, BW * 0.6, hz + BH * 0.02), 180, 360, fill=(40, 36, 36))
        d.rectangle((BW * 0.12, hz - BH * 0.2, BW * 0.17, hz - BH * 0.08), fill=(30, 70, 200))
    elif kit == "interior":
        img.paste((200, 150, 100) if not night else (60, 40, 30), (0, 0, BW, hz))
        d.rectangle((0, hz, BW, BH), fill=(120, 80, 50))
        d.rectangle((BW * 0.62, hz - BH * 0.3, BW * 0.9, hz - BH * 0.1), fill=(190, 225, 255))
    else:
        d.rectangle((0, hz, BW, BH), fill=(80, 170, 70) if not night else (20, 55, 30))
        for i, x in enumerate(range(0, BW, max(10, BW // 6))):
            d.ellipse((x - BW * 0.2, hz - BH * 0.06 - (i % 2) * BH * 0.03, x + BW * 0.25, hz + BH * 0.08), fill=(60, 140, 60))
    return img


def render_shot(shot, cfg, sprite_dir, out_mp4):
    W, H = video_size(cfg)
    fps = video_fps(cfg)
    n = max(2, round(shot["render_seconds"] * fps))
    BW, BH = int(W * K) // 2 * 2, int(H * K) // 2 * 2
    base = _background(shot["kit"], shot["tod"], BW, BH)
    frac = CHAR_FRAC.get(shot["shot_size"])
    if frac:
        xs = {"left": 0.38, "right": 0.64, "center": 0.5}
        for c in shot["characters"]:
            sp = Image.open(Path(sprite_dir) / f"{c['role']}_{c['expression']}.png").convert("RGBA")
            h = int(BH * frac)
            sp = sp.resize((int(sp.width * h / sp.height), h), Image.LANCZOS)
            base.paste(sp, (int(BW * xs.get(c["side"], 0.5) - sp.width / 2), int(BH * 0.9 - h)), sp)
    z0, z1, px0, px1, py0, py1, r0, r1 = MOVES.get(shot["camera_move"], MOVES["push_in"])
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(out_mp4)], stdin=subprocess.PIPE)
    for i in range(n):
        e = _ease(i / max(1, n - 1))
        z = z0 + (z1 - z0) * e
        cw, ch = W / z, H / z
        cx = BW / 2 + (px0 + (px1 - px0) * e) * W + math.sin(i * 0.37) * W * 0.002
        cy = BH / 2 + (py0 + (py1 - py0) * e) * H + math.cos(i * 0.31) * H * 0.002
        rot = r0 + (r1 - r0) * e
        if abs(rot) > 0.01:
            m = 1.3
            reg = base.crop((int(cx - cw * m / 2), int(cy - ch * m / 2), int(cx + cw * m / 2), int(cy + ch * m / 2)))
            reg = reg.rotate(rot, resample=Image.BILINEAR)
            ox, oy = (reg.width - cw) / 2, (reg.height - ch) / 2
            frame = reg.crop((int(ox), int(oy), int(ox + cw), int(oy + ch)))
        else:
            frame = base.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2)))
        proc.stdin.write(frame.resize((W, H), Image.BILINEAR).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError(f"ffmpeg failed for shot {shot['id']}")
