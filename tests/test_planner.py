from stuff.planner import build_plan, chunk_sentence, split_sentences, validate_plan

TEXT = ("In 1869, two companies were racing across a canyon so deep that nothing could fill it. "
        "Then a furious tycoon screamed at his workers! The next morning, a tiny gap in the rail changed everything. Boom.")


def test_split_and_chunk():
    assert len(split_sentences(TEXT)) == 4
    assert all(len(c.split()) <= 12 for c in chunk_sentence("word " * 30))


def test_plan_shape_and_rules():
    p = build_plan(TEXT, "t")
    assert validate_plan(p) == []
    shots = p["shots"]
    assert shots[0]["shot_size"] == "wide_aerial"
    assert shots[0]["kit"] == "canyon"
    assert any(s["tod"] == "dawn" and s["transition"] == "dissolve" for s in shots)
    assert any(c["expression"] == "rage" for s in shots for c in s["characters"])
    assert any("explosion" in s["fx"] for s in shots)
    assert shots[-1]["camera_move"] == "dutch_push"


def test_no_three_equal_sizes_in_a_row():
    p = build_plan("He walked. " * 30, "t")
    sizes = [s["shot_size"] for s in p["shots"]]
    assert not any(sizes[i] == sizes[i + 1] == sizes[i + 2] for i in range(len(sizes) - 2))
