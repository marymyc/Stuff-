"""Engine plan contract (no rendering): frames contiguous, words inside the video, focus (insert) shots mapped."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_plan", ROOT / "engine" / "tools" / "make_plan.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)

SCRIPT = ("Two companies raced across a deep canyon. The owner held a coin up to the gap. "
          "Then the calendar flipped to July, and the gap was thinner than a sheet of paper. "
          "The newspaper called it the perfect rail. Boom.")


def _plan(tmp_path):
    s = tmp_path / "s.txt"
    s.write_text(SCRIPT)
    return mp.make(str(s), str(tmp_path / "plan.json"), voice="silent")


def test_frames_contiguous_and_words_inside(tmp_path):
    p = _plan(tmp_path)
    shots = p["shots"]
    assert shots[0]["a"] == 0 and shots[-1]["b"] == p["total"]
    assert all(a["b"] == b["a"] for a, b in zip(shots, shots[1:]))
    assert all(0 <= w["s"] < w["e"] <= p["total"] / p["fps"] + 0.5 for w in p["words"])
    assert [w["s"] for w in p["words"]] == sorted(w["s"] for w in p["words"])


def test_insert_shots_have_focus_and_no_cast(tmp_path):
    p = _plan(tmp_path)
    foci = {s["focus"] for s in p["shots"] if s.get("focus")}
    assert {"coin", "calendar", "paper", "newspaper"} <= foci
    assert all(s["size"] == "macro" and not s["chars"] for s in p["shots"] if s.get("focus"))
    assert not p["shots"][0].get("focus")            # the hook is never an insert


def test_plan_is_json_and_mix_fields_present(tmp_path):
    p = _plan(tmp_path)
    json.dumps(p)
    assert len(p["voice"]["wavs"]) == len(p["voice"]["starts"]) == len(p["shots"])


def test_point_action_goes_to_the_boss(tmp_path):
    s = tmp_path / "s.txt"
    s.write_text("Two companies raced across a canyon. The tycoon pointed at his workers. Boom.")
    p = mp.make(str(s), str(tmp_path / "plan.json"), voice="silent")
    pointers = [c for sh in p["shots"] for c in sh["chars"] if c.get("action") == "point"]
    assert pointers and all(c["outfit"] in ("tycoon", "commander") for c in pointers)
