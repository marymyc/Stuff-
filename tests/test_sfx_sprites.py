import numpy as np

from stuff.sfx import SR, render_track
from stuff.sprites import EXPRESSIONS, draw_character


def test_sfx_track_finite_and_placed():
    x = render_track([("boom", 0.5, 1.0), ("whoosh", 0.0, 0.5)], 4.0)
    assert len(x) == 4 * SR and np.isfinite(x).all() and np.abs(x).max() > 0.05
    assert np.abs(x[: SR // 10]).max() > 0  # whoosh starts at 0


def test_all_expressions_render_rgba():
    for e in EXPRESSIONS:
        im = draw_character("hero", e)
        assert im.mode == "RGBA" and im.size == (600, 1100) and im.getchannel("A").getbbox()
