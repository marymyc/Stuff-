"""Word-by-word pop captions as ASS: bold white, black outline, ~70% height, keyword highlight."""
from __future__ import annotations

import re


def ts(t):
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    if round(s, 2) >= 60:
        s = 59.99
    return f"{h}:{m:02d}:{s:05.2f}"


def make_cards(shots, per_card=2):
    cards = []
    for sh in shots:
        words, i = sh["words"], 0
        emph = set(sh.get("emphasis", []))
        while i < len(words):
            grp = [words[i]]
            i += 1
            while i < len(words) and len(grp) < per_card and grp[-1]["word"][-1] not in ".!?,;:":
                grp.append(words[i])
                i += 1
            cards.append({
                "start": sh["start"] + grp[0]["start"], "end": sh["start"] + grp[-1]["end"],
                "words": [(g["word"], re.sub(r"[^A-Za-z0-9']", "", g["word"]).lower() in emph) for g in grp],
            })
    for a, b in zip(cards, cards[1:]):
        a["end"] = max(a["end"], min(b["start"] - 0.02, a["end"] + 0.25))
    for c in cards:
        c["end"] = max(c["end"], c["start"] + 0.2)
    return cards


def build_ass(timeline, cfg, width, height) -> str:
    c = cfg["captions"]
    size = int(height * c["size_ratio"])
    x, y = width // 2, int(height * c["y_ratio"])
    hi = c["highlight"]
    out = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 2",
        "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Cap,{c['font']},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,"
        f"{max(2, size // 12)},{max(1, size // 30)},5,20,20,20,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    pop = r"\fscx80\fscy80\t(0,100,\fscx112\fscy112)\t(100,180,\fscx100\fscy100)" if c["pop"] else ""
    for card in make_cards(timeline["shots"], c["words_per_card"]):
        parts = []
        for w, e in card["words"]:
            w = w.replace("{", "(").replace("}", ")")
            parts.append(f"{{\\c{hi}}}{w}{{\\c&H00FFFFFF&}}" if e else w)
        out.append(f"Dialogue: 0,{ts(card['start'])},{ts(card['end'])},Cap,,0,0,0,,"
                   f"{{\\an5\\pos({x},{y}){pop}}}{' '.join(parts)}")
    return "\n".join(out) + "\n"
