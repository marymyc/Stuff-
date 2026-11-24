"""Shared helpers for the tools: repo paths, .env loading, short-name checks."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env():
    """Read KEY=VALUE lines from .env into os.environ (existing variables win)."""
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def check_name(name):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name or ""):
        sys.exit(f"bad short name {name!r}: use lowercase letters, digits and _ (e.g. titanic_rivets)")
    return name


def comp_id(name):
    return "".join(p.capitalize() for p in name.split("_")) + "Short"


def project_dir(name):
    return os.path.join(ROOT, "projects", name)


def video_dir(name):
    return os.path.join(ROOT, "src", "videos", name)


def voiceover_text(script_path):
    """The spoken text of SCRIPT.md: everything under '## Voiceover' (up to the next '## '), else the whole file
    minus headings, list items and the facts block."""
    src = open(script_path, encoding="utf-8").read()
    m = re.search(r"^##\s*Voice[- ]?over\s*$(.*?)(?=^##\s|\Z)", src, re.M | re.S | re.I)
    body = m.group(1) if m else src
    lines = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", "-", "*", ">", "|", "Facts:", "Format:", "Source")):
            continue
        lines.append(s)
    return "\n".join(lines).strip()
