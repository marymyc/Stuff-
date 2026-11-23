import shutil
from pathlib import Path

import pytest

from stuff import pipeline
from stuff.config import load_config

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
SCRIPT = Path(__file__).parent.parent / "examples" / "mini_script.txt"


def test_end_to_end_silent_pil(tmp_path):
    cfg = load_config(overrides={"voice": {"backend": "silent"}, "render": {"renderer": "pil", "scale": 0.25, "fps": 10}})
    out, v = pipeline.make(SCRIPT, tmp_path, cfg)
    assert out.exists() and v["ok"] and v["has_audio"] and v["captions_burned"]
    assert (v["width"], v["height"]) == (180, 320)
