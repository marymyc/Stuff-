import shutil
from pathlib import Path

import pytest

from stuff import pipeline
from stuff.config import load_config

import os
pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not os.environ.get("RUN_RENDER_TESTS"),
                                reason="render tests are opt-in (RUN_RENDER_TESTS=1): renders are run by the user only")
SCRIPT = Path(__file__).parent.parent / "examples" / "mini_script.txt"


def test_end_to_end_silent_pil(tmp_path):
    cfg = load_config(overrides={"voice": {"backend": "silent"}, "render": {"renderer": "pil", "scale": 0.25, "fps": 10}})
    out, v = pipeline.make(SCRIPT, tmp_path, cfg)
    assert out.exists() and v["ok"] and v["has_audio"] and v["captions_burned"]
    assert (v["width"], v["height"]) == (180, 320)


def test_relative_workdir(tmp_path, monkeypatch):
    """Regression: caption burn-in used a cwd-relative output path and failed with relative workdirs."""
    monkeypatch.chdir(tmp_path)
    cfg = load_config(overrides={"voice": {"backend": "silent"}, "render": {"renderer": "pil", "scale": 0.25, "fps": 10}})
    out, v = pipeline.make(SCRIPT, "work/rel", cfg)
    assert out.exists() and v["ok"]
