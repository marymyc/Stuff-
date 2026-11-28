"""Hybrid plan contract (no rendering): zones, camera, cast, words, audio files."""
import importlib.util
import json
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mhp", ROOT / "hybrid" / "tools" / "make_hybrid_plan.py")
mhp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mhp)

SCRIPT = ("Two companies raced across a canyon. The tycoon pointed at his workers, and the engineer smiled. "
          "Then the king's army surrounded the castle! Inside the room, a clock ticked. Suddenly the wall exploded. Boom.")


def _make(tmp_path, monkeypatch):
    monkeypatch.setattr(mhp, "ROOT", str(tmp_path))
    s = tmp_path / "s.txt"
    s.write_text(SCRIPT)
    plan = mhp.make(str(s), voice="silent", validate=False)
    return plan, tmp_path


def test_plan_files_and_zones(tmp_path, monkeypatch):
    plan, root = _make(tmp_path, monkeypatch)
    assert (root / "public" / "plan.json").exists() and (root / "public" / "audio" / "words.json").exists()
    shots = plan["shots"]
    assert shots[0]["a"] == 0 and shots[-1]["b"] == plan["totalFrames"] and all(a["b"] == b["a"] for a, b in zip(shots, shots[1:]))
    zones = {s["set"]: s["zone"] for s in shots}
    assert len(set(zones.values())) == len(zones) >= 2                       # one zone per set, distinct
    assert {"canyon", "fortress", "interior"} <= set(zones)


def test_camera_and_cast_rules(tmp_path, monkeypatch):
    plan, _ = _make(tmp_path, monkeypatch)
    for s in plan["shots"]:
        assert 30 <= s["fov"] <= 52 and s["camStart"][1] >= 0.4 and s["punchWords"]
        assert abs(s["lookAt"][2] - (-150 * s["zone"])) < 6.5               # looks at its own zone
    assert plan["shots"][0]["chars"], "the hook must show a character"
    assert any(c.get("action") == "point" for s in plan["shots"] for c in s["chars"])
    assert len({s["light"] for s in plan["shots"]}) >= 2
    xs = [a["pos"][0] for a in plan["actors"]]
    assert len(xs) == len(set(xs))


def test_audio_and_words(tmp_path, monkeypatch):
    plan, root = _make(tmp_path, monkeypatch)
    words = json.loads((root / "public" / "audio" / "words.json").read_text())
    assert words["totalFrames"] == plan["totalFrames"] and words["words"]
    assert [w["startMs"] for w in words["words"]] == sorted(w["startMs"] for w in words["words"])
    x, sr = sf.read(root / "public" / "audio" / "mix.wav")
    assert sr == 48000 and abs(len(x) / sr - plan["totalFrames"] / 30) < 0.15
