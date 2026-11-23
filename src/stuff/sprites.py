"""Procedural 2.5D character sprites: white round head, thick black outline, noodle legs, coloured vest."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

S = 2
W, H = 600, 1100
BLACK = (15, 15, 18, 255)
WHITE = (255, 255, 255, 255)
PALETTES = {
    "hero": {"vest": (24, 160, 150), "hat": "cap", "hat_col": (70, 80, 120), "accent": (200, 40, 50)},
    "rival": {"vest": (222, 178, 40), "hat": "bowler", "hat_col": (30, 30, 34), "accent": (120, 70, 20)},
    "extra": {"vest": (150, 160, 70), "hat": "helmet", "hat_col": (150, 155, 165), "accent": (200, 30, 30)},
    "extra2": {"vest": (60, 90, 170), "hat": "none", "hat_col": (90, 60, 40), "accent": (230, 230, 230)},
}
EXPRESSIONS = ["neutral", "angry", "rage", "happy", "shocked", "worried", "smug"]


def _poly(d, pts, width):
    pts = [(x * S, y * S) for x, y in pts]
    d.line(pts, fill=BLACK, width=int(width * S), joint="curve")
    r = width * S / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=BLACK)


def _hat(d, pal):
    kind, col = pal["hat"], pal["hat_col"] + (255,)
    if kind == "cap":
        d.chord((130 * S, 80 * S, 470 * S, 420 * S), 200, 340, fill=col, outline=BLACK, width=12 * S)
        for x in range(190, 411, 24):
            top = 250 - (170 ** 2 - (x - 300) ** 2) ** 0.5
            d.line((x * S, (top + 6) * S, x * S, 190 * S), fill=(235, 235, 245, 255), width=5 * S)
        d.ellipse((130 * S, 170 * S, 300 * S, 205 * S), fill=col, outline=BLACK, width=8 * S)
    elif kind == "bowler":
        d.ellipse((190 * S, 30 * S, 410 * S, 160 * S), fill=col, outline=BLACK, width=12 * S)
        d.ellipse((135 * S, 135 * S, 465 * S, 185 * S), fill=col, outline=BLACK, width=12 * S)
    elif kind == "helmet":
        d.ellipse((150 * S, 55 * S, 450 * S, 235 * S), fill=col, outline=BLACK, width=12 * S)
        d.ellipse((280 * S, 5 * S, 322 * S, 95 * S), fill=(200, 30, 30, 255), outline=BLACK, width=8 * S)
    else:
        d.chord((130 * S, 80 * S, 470 * S, 420 * S), 205, 335, fill=col, outline=BLACK, width=10 * S)


def _face(d, e):
    def eye(cx, cy, r=11):
        d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), fill=BLACK)

    def line(a, b, w=10):
        d.line((a[0] * S, a[1] * S, b[0] * S, b[1] * S), fill=BLACK, width=int(w * S))

    L, R = (238, 262), (362, 262)
    if e in ("neutral", "smug"):
        eye(*L)
        eye(*R)
        line((215, 225), (262, 232))
        line((338, 232), (385, 225))
        if e == "smug":
            line((218, 252), (262, 252), 12)
            line((338, 252), (382, 252), 12)
            line((250, 345), (345, 328))
        else:
            line((255, 342), (345, 342))
    elif e in ("angry", "rage"):
        eye(L[0], L[1] + 4, 10)
        eye(R[0], R[1] + 4, 10)
        line((212, 222), (265, 248), 12)
        line((335, 248), (388, 222), 12)
        d.rounded_rectangle((235 * S, 320 * S, 365 * S, 365 * S), radius=10 * S, fill=WHITE, outline=BLACK, width=8 * S)
        for x in range(255, 365, 22):
            line((x, 322), (x, 363), 5)
        line((235, 342), (365, 342), 5)
        if e == "rage":
            for cx, cy in ((110, 120), (95, 185), (490, 120), (505, 185)):
                d.ellipse(((cx - 38) * S, (cy - 30) * S, (cx + 38) * S, (cy + 30) * S), fill=WHITE, outline=BLACK, width=6 * S)
    elif e == "happy":
        for x0 in (215, 337):
            d.arc((x0 * S, 240 * S, (x0 + 50) * S, 285 * S), 200, 340, fill=BLACK, width=10 * S)
        d.arc((235 * S, 285 * S, 365 * S, 380 * S), 20, 160, fill=BLACK, width=10 * S)
    elif e == "shocked":
        for cx in (L[0], R[0]):
            d.ellipse(((cx - 26) * S, (262 - 26) * S, (cx + 26) * S, (262 + 26) * S), fill=WHITE, outline=BLACK, width=7 * S)
            eye(cx, 262, 8)
        line((205, 205), (265, 200))
        line((335, 200), (395, 205))
        d.ellipse((275 * S, 320 * S, 325 * S, 385 * S), fill=BLACK)
    elif e == "worried":
        eye(*L)
        eye(*R)
        line((215, 238), (262, 214))
        line((338, 214), (385, 238))
        pts = [(255, 350), (278, 338), (300, 352), (322, 338), (345, 350)]
        d.line([(x * S, y * S) for x, y in pts], fill=BLACK, width=9 * S, joint="curve")
        d.polygon([(420 * S, 150 * S), (400 * S, 190 * S), (440 * S, 190 * S)], fill=(120, 190, 255, 255), outline=BLACK)


def draw_character(role: str = "hero", expression: str = "neutral") -> Image.Image:
    pal = PALETTES.get(role, PALETTES["extra"])
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _poly(d, [(255, 720), (245, 880), (255, 1040)], 16)
    _poly(d, [(345, 720), (355, 880), (345, 1040)], 16)
    d.ellipse((225 * S, 1030 * S, 285 * S, 1060 * S), fill=BLACK)
    d.ellipse((320 * S, 1030 * S, 380 * S, 1060 * S), fill=BLACK)
    _poly(d, [(205, 480), (150, 600), (180, 700)], 14)
    _poly(d, [(395, 480), (450, 600), (420, 700)], 14)
    d.rounded_rectangle((195 * S, 420 * S, 405 * S, 730 * S), radius=80 * S, fill=pal["vest"] + (255,),
                        outline=BLACK, width=14 * S)
    d.rectangle((197 * S, 610 * S, 403 * S, 636 * S), fill=pal["accent"] + (255,))
    d.line((300 * S, 440 * S, 300 * S, 610 * S), fill=BLACK, width=6 * S)
    head = (150, 70, 200, 255) if expression == "rage" else WHITE
    d.ellipse((130 * S, 80 * S, 470 * S, 420 * S), fill=head, outline=BLACK, width=16 * S)
    _hat(d, pal)
    _face(d, expression)
    return img.resize((W, H), Image.LANCZOS)


def ensure_sprites(pairs, out_dir) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for role, expr in sorted(set(pairs)):
        p = out / f"{role}_{expr}.png"
        if not p.exists():
            draw_character(role, expr).save(p)
        paths[(role, expr)] = str(p)
    return paths


def pairs_from_plan(plan) -> list:
    return [(c["role"], c["expression"]) for s in plan["shots"] for c in s.get("characters", [])]
