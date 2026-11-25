"""Script -> shot plan.

Pure Python, no heavy dependencies. The plan is plain JSON (see docs/PLAN_SCHEMA.md), so an AI operator may
refine it by hand before rendering. Rules come from the reference analysis in docs/STYLE_GUIDE.md.
"""
from __future__ import annotations

import re

WPS = 2.6  # narration words per second; planning estimate only, real timing comes from the audio

KIT_WORDS = {
    "fortress": ["fort", "castle", "wall", "siege", "army", "soldier", "sword", "general", "gate", "archer",
                 "kingdom", "battle", "enemy", "defend", "commander", "empire", "knight", "armies"],
    "canyon": ["railroad", "railway", "rail", "rails", "train", "canyon", "track", "tracks", "locomotive",
               "bridge", "station", "desert"],
    "interior": ["room", "office", "lab", "laboratory", "house", "inside", "library", "kitchen", "desk",
                 "school", "hospital", "workshop", "factory", "meeting"],
}
TOD_WORDS = {
    "night": ["night", "midnight", "darkness"],
    "dusk": ["dusk", "evening", "sunset"],
    "dawn": ["morning", "dawn", "sunrise"],
    "day": ["noon", "daylight", "next day"],
}
EXPR_WORDS = [  # priority order
    ("rage", ["furious", "rage", "enraged", "screams", "screamed", "shouted", "yelled"]),
    ("shocked", ["suddenly", "explode", "explodes", "exploded", "boom", "crash", "collapse", "collapsed",
                 "impossible", "disaster", "shock", "shocked", "fell", "falls"]),
    ("angry", ["angry", "hate", "refuse", "refused", "demand", "threat", "enemy", "fight", "war", "never"]),
    ("worried", ["problem", "fail", "failed", "risk", "danger", "trouble", "afraid", "worry", "but",
                 "however", "except", "crack", "broke", "gap", "gaps"]),
    ("happy", ["win", "won", "success", "victory", "perfect", "thrilled", "celebrate", "finally", "solved",
               "saved", "genius", "brilliant"]),
    ("smug", ["secret", "trick", "clever", "plan", "scheme", "idea", "simple", "cheap", "only"]),
]
AERIAL = ["army", "armies", "valley", "across the", "miles", "country", "landscape", "empire", "thousands",
          "horizon", "canyon"]
MACRO = ["tiny", "detail", "hole", "holes", "gap", "gaps", "inch", "millimeter", "wire", "fuse", "spark",
         "screw", "bolt", "nail", "thread"]
CLOSE = ["face", "eyes", "said", "asked", "whispered", "smiled", "glared", "laughed"]
LOW = ["towering", "giant", "huge", "massive", "enormous", "king", "tycoon", "commander", "general"]
RIVAL = ["general", "commander", "king", "boss", "owner", "director", "tycoon", "rival", "enemy", "rich",
         "president", "emperor", "manager"]
CROWD = ["everyone", "soldiers", "workers", "crowd", "people", "army", "guards", "villagers", "men"]
PROPS = {"cart": ["cart", "wagon"], "crate": ["crate", "box", "boxes"], "barrel": ["barrel", "barrels"],
         "umbrella": ["umbrella", "parasol"], "lamp": ["lamp", "lantern", "torch", "torches"],
         "table": ["table", "desk"]}
INSERTS = {  # object keyword -> close-up "insert" shot of that object (macro, no cast), like the references' cutaways
    "coin": ["coin", "coins"], "paper": ["paper", "sheet"], "calendar": ["calendar", "july"],
    "newspaper": ["newspaper", "newspapers", "headline", "herald"], "caliper": ["caliper", "gauge", "measure", "measured", "measuring"],
    "thermometer": ["thermometer", "temperature", "degrees"], "moneybag": ["money", "dollars", "cash", "fortune", "profit"],
    "map": ["map", "maps"], "clock": ["clock", "watch", "o'clock"], "marble": ["marble", "ball"],
}
ACTIONS = [  # what the lead character does during the beat (first match wins)
    ("point", ["pointed", "points", "pointing", "showed", "shows", "showing", "demanded", "insisted"]),
    ("wave", ["waved", "waving", "greeted", "hello", "welcomed", "cheered"]),
    ("sit", ["sat", "sitting", "relaxed", "rested", "lounging", "waited"]),
    ("hop", ["suddenly", "jumped", "startled", "gasped", "shocked", "froze"]),
    ("stroll", ["walked", "walking", "marched", "strolled", "ran", "rushed", "arrived"]),
]
BREAK_BEFORE = {"and", "but", "because", "until", "while", "when", "so", "then", "after", "before", "which",
                "where", "as"}
EMPH_WORDS = {"never", "only", "perfect", "impossible", "million", "billion", "every", "nobody", "everything"}
SIZE_MOVE = {"wide_aerial": "fly_forward", "wide": "pull_back", "medium": "orbit_slow",
             "medium_low": "push_in_low", "close": "push_in", "macro": "slide"}
SIZE_CYCLE = ["medium", "close", "wide", "medium_low", "medium"]


def _tokens(text: str):
    return re.findall(r"[a-z0-9']+", text.lower())


def split_sentences(text: str):
    text = re.sub(r"\s+", " ", text.strip())
    return [p for p in re.split(r"(?<=[.!?])\s+", text) if p]


def chunk_sentence(s: str, target: int = 6, max_words: int = 9):
    words = s.split()
    if len(words) <= max_words:
        return [s]
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1].lower().strip(",;:.") if i + 1 < len(words) else None
        if len(cur) >= max_words or (len(cur) >= target and (w[-1] in ",;:" or nxt in BREAK_BEFORE)):
            chunks.append(cur)
            cur = []
    if cur:
        if chunks and len(cur) < 3:
            chunks[-1].extend(cur)
        else:
            chunks.append(cur)
    return [" ".join(c) for c in chunks]


def detect_kit(tokens):
    best, score = None, 0
    for kit, words in KIT_WORDS.items():
        sc = sum(1 for t in tokens if t in words)
        if sc > score:
            best, score = kit, sc
    return best


def detect_tod(low: str):
    for tod, words in TOD_WORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
            return tod
    return None


def detect_expression(tokens, default="neutral"):
    for expr, words in EXPR_WORDS:
        if any(t in words for t in tokens):
            return expr
    return default


def pick_action(tokens):
    for name, words in ACTIONS:
        if any(t in words for t in tokens):
            return name
    return None


def pick_focus(tokens):
    for name, words in INSERTS.items():
        if any(t in words for t in tokens):
            return name
    return None


def pick_size(text, low, tokens, i, prev_sizes):
    if i == 0:
        return "wide_aerial"
    prev = prev_sizes[-1] if prev_sizes else None
    if any(k in low for k in AERIAL):
        return "wide_aerial" if prev != "wide_aerial" else "wide"
    if re.search(r"\b\d{1,3}\b", text) or any(t in MACRO for t in tokens):
        return "macro" if prev != "macro" else "close"
    if "!" in text or "?" in text or any(t in CLOSE for t in tokens):
        return "close"
    if any(t in LOW for t in tokens):
        return "medium_low"
    cand = SIZE_CYCLE[i % len(SIZE_CYCLE)]
    if len(prev_sizes) >= 2 and prev_sizes[-1] == prev_sizes[-2] == cand:
        cand = "close" if cand != "close" else "medium"
    return cand


def pick_characters(tokens, size, expr):
    if size in ("wide_aerial", "macro"):
        return []
    chars = [{"role": "hero", "expression": expr, "side": "left"}]
    if any(t in RIVAL for t in tokens):
        chars.append({"role": "rival", "expression": "angry" if expr in ("neutral", "happy") else expr,
                      "side": "right"})
    if any(t in CROWD for t in tokens) and size in ("wide", "medium"):
        chars.append({"role": "extra", "expression": "shocked", "side": "center"})
    return chars


def pick_sfx(tokens, size, i, expr):
    out = []
    if size == "wide_aerial":
        out.append({"name": "whoosh", "at": 0.0, "gain": 0.6})
    if any(t in ("explode", "explodes", "exploded", "boom", "blast", "bomb", "crash") for t in tokens):
        out.append({"name": "boom", "at": 0.1, "gain": 1.0})
    if any(t in ("shake", "shakes", "collapse", "collapsed", "earthquake", "rumble") for t in tokens):
        out.append({"name": "rumble", "at": 0.0, "gain": 0.7})
    if any(t in ("spark", "sparks", "fuse", "ignite", "ignited", "fire", "burn") for t in tokens):
        out.append({"name": "spark", "at": 0.0, "gain": 0.6})
    if expr == "happy" and size == "close":
        out.append({"name": "ding", "at": 0.2, "gain": 0.5})
    if size == "macro" and not out:
        out.append({"name": "pop", "at": 0.0, "gain": 0.5})
    return out


def pick_emphasis(text):
    out = []
    for j, w in enumerate(text.split()):
        c = re.sub(r"[^A-Za-z0-9']", "", w)
        if not c:
            continue
        if c.isdigit() or c.lower() in EMPH_WORDS or (c.isupper() and len(c) > 1) or (j > 0 and c[0].isupper()):
            out.append(c.lower())
    return sorted(set(out))


def build_plan(text: str, title: str | None = None) -> dict:
    beats = [c for s in split_sentences(text) for c in chunk_sentence(s)]
    shots, kit, tod, sizes = [], "field", "day", []
    n = len(beats)
    for i, t in enumerate(beats):
        low = t.lower()
        toks = _tokens(t)
        transition = "cut"
        new_kit = detect_kit(toks)
        if new_kit and new_kit != kit:
            kit = new_kit
        new_tod = detect_tod(low)
        if new_tod and new_tod != tod:
            tod = new_tod
            transition = "dissolve" if i > 0 else "cut"
        expr = detect_expression(toks)
        size = pick_size(t, low, toks, i, sizes)
        focus = pick_focus(toks) if i > 0 else None      # the hook (shot 1) stays an establishing shot
        if focus:
            size = "macro"
        move = SIZE_MOVE[size]
        if i >= n - 2 and n >= 4 and size in ("close", "medium", "medium_low"):
            move = "dutch_push"
        sizes.append(size)
        fx = ["explosion"] if any(k in toks for k in ("explode", "explodes", "exploded", "boom", "blast")) else []
        props = [p for p, words in PROPS.items() if any(w in toks for w in words)]
        shots.append({
            "id": i, "text": t, "kit": kit, "tod": tod, "shot_size": size, "camera_move": move,
            "transition": transition, "characters": pick_characters(toks, size, expr), "props": props,
            "fx": fx, "sfx": pick_sfx(toks, size, i, expr), "emphasis": pick_emphasis(t),
            **({"focus": focus} if focus else {}),
            **({"action": pick_action(toks)} if pick_action(toks) else {}),
        })
    words = sum(len(s["text"].split()) for s in shots)
    return {"version": 1, "title": title or "untitled", "meta": {"words": words, "est_seconds": round(words / WPS, 1)},
            "shots": shots}


REQUIRED = {"id", "text", "kit", "tod", "shot_size", "camera_move", "transition", "characters"}


def validate_plan(plan: dict):
    errs = []
    if not plan.get("shots"):
        errs.append("plan has no shots")
    for s in plan.get("shots", []):
        miss = REQUIRED - set(s)
        if miss:
            errs.append(f"shot {s.get('id')}: missing {sorted(miss)}")
        if s.get("shot_size") not in SIZE_MOVE:
            errs.append(f"shot {s.get('id')}: bad shot_size {s.get('shot_size')}")
    return errs
