# GeoWeb — tests for the video frame sampler.
# Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FRAMES = REPO / "video" / "frames.py"

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _make_tiny_clip(path: Path) -> None:
    """Render a ~1.5 s, 320x180 12-fps clip: pure red, then pure blue (a scene change)."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "smptebars=duration=0.5:size=320x180:rate=12", "-loglevel", "error", str(path)],
        check=True,
    )


def test_extract_contact_sheet_and_metadata(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    _make_tiny_clip(clip)
    out = tmp_path / "frames"
    (tmp_path / "frames").mkdir()
    res = subprocess.run(["uv", "run", "-q", str(FRAMES), str(clip), "--out-dir", str(out)],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    samples = json.loads((out / "samples.json").read_text())
    video = json.loads((out / "video.json").read_text())
    assert samples["samples"], "no frames extracted"
    assert (out / "contact_sheet.jpg").is_file()
    assert {s["file"] for s in samples["samples"]} <= {p.name for p in out.glob("frame_*.jpg")}
    assert video["width"] == 320 and video["height"] == 180
    assert (video.get("duration") or video.get("duration_sec") or 0) > 0
    for s in samples["samples"]:
        assert "index" in s and "t_sec" in s and "ts" in s


def test_dedupe_param_keeps_at_most_max(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    _make_tiny_clip(clip)
    out = tmp_path / "frames"
    res = subprocess.run(["uv", "run", "-q", str(FRAMES), str(clip), "--out-dir", str(out), "--max", "1"],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    samples = json.loads((out / "samples.json").read_text())
    assert len(samples["samples"]) <= 1