from stuff.align import build_timeline, proportional_words
from stuff.captions import build_ass, make_cards, ts
from stuff.config import load_config
from stuff.planner import build_plan
from stuff.tts import synthesize_plan


def _timeline(tmp_path):
    cfg = load_config(overrides={"voice": {"backend": "silent"}})
    plan = build_plan("In 1869, two companies were racing across a canyon so deep that nothing could fill it. Boom.", "t")
    return cfg, build_timeline(plan, synthesize_plan(plan, tmp_path, cfg), cfg)


def test_proportional_words_cover_interval():
    w = proportional_words("one two three four", 1.0, 3.0)
    assert w[0]["start"] == 1.0 and abs(w[-1]["end"] - 3.0) < 0.01
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(w, w[1:]))


def test_timeline_is_contiguous(tmp_path):
    _, tl = _timeline(tmp_path)
    t = 0
    for s in tl["shots"]:
        assert abs(s["start"] - t) < 0.01
        t += s["duration"]
    assert abs(tl["total_seconds"] - t) < 0.01


def test_ass_events_monotonic(tmp_path):
    cfg, tl = _timeline(tmp_path)
    ass = build_ass(tl, cfg, 720, 1280)
    assert "PlayResX: 720" in ass and ass.count("Dialogue:") == len(make_cards(tl["shots"], 2))
    starts = [c["start"] for c in make_cards(tl["shots"], 2)]
    assert starts == sorted(starts)
    assert ts(61.5) == "0:01:01.50"
