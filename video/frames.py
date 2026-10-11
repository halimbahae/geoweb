#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless>=4.8,<5", "numpy"]
# ///
"""Cut a video into a short list of distinct frames ready for GeoWeb.

Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

The recon pipeline works on stills, so a clip is first reduced to a contact
sheet of representative frames: a uniform pass over the whole timeline, scene
changes broken out, near-duplicates dropped with a 64-bit dHash (Hamming distance
<= --hamming), then evenly trimmed to --max frames. The analyst picks one frame
and the rest of GeoWeb treats it exactly like an uploaded photo.

Frames are written as JPEGs next to a contact sheet and two JSON files:

  frames.py clip.mp4 --out-dir frames/
      → frames/frame_000000.jpg ... frame_000011.jpg
        frames/contact_sheet.jpg
        frames/samples.json   [{index, t_sec, file, ts}]
        frames/video.json     {path, width, height, fps, n_frames, duration}

Use `--check` to verify OpenCV + FFmpeg are present before running a job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError as exc:  # pragma: no cover
    sys.exit(f"video/frames.py needs opencv-python-headless: pip install 'opencv-python-headless>=4.8' ({exc})")


def dhash(gray: np.ndarray, size: int = 8) -> int:
    """64-bit difference hash of a grayscale frame (with horizontal padding)."""
    small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).reshape(-1)
    out = 0
    for i, b in enumerate(bits):
        if b:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def probe(cap: cv2.VideoCapture) -> dict:
    """Best-effort metadata; every value can be 0/None on broken containers."""
    return {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
        "fps": round(float(cap.get(cv2.CAP_PROP_FPS) or 0.0), 3),
        "n_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
    }


def pick_frames(cap: cv2.VideoCapture, total: int, max_frames: int = 24, hamming_dist: int = 3,
                scene_thresh: float = 16.0, sample_mult: int = 6) -> list[int]:
    """Indexes of the most informative frames, in time order.

    Uniform candidates at ~sample_mult x the target, then a greedy sweep keeps a
    frame unless both its scene-change delta *and* its dHash distance to the last
    kept frame are under the thresholds. First/middle/last frames are always
    candidates so the sheet has stable anchors.
    """
    if max_frames < 1:
        return []
    cands = sorted(set(int(i) for i in np.linspace(0, max(0, total - 1), max(2, sample_mult * max_frames + 1)))
                   | {0, total // 2, max(0, total - 1)})
    kept: list[int] = []
    last_hash: int | None = None
    last_small: np.ndarray | None = None

    def read(idx: int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        return frame if ok else None

    _pre = read(0) if total else None
    if _pre is None:
        return []
    _small0 = cv2.resize(_pre, (128, 72))
    last_small = cv2.cvtColor(_small0, cv2.COLOR_BGR2GRAY)

    for idx in cands:
        if idx == 0:
            kept.append(0)
            continue
        frame = read(idx)
        if frame is None:
            continue
        small = cv2.resize(frame, (128, 72))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        delta = float(cv2.absdiff(g, last_small).mean())
        h = dhash(g, 8)
        if last_hash is not None and hamming(h, last_hash) <= hamming_dist and delta < scene_thresh:
            last_small = g
            continue
        kept.append(idx)
        last_hash = h
        last_small = g

    if len(kept) > max_frames:
        pos = sorted(set(int(round(i)) for i in np.linspace(0, len(kept) - 1, max_frames)))
        kept = [kept[i] for i in pos]
    return kept


def write_frame(cap: cv2.VideoCapture, idx: int, out: Path) -> bool:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok:
        return False
    cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return True


def contact_sheet(frames: list[Path], out: Path, cols: int = 4, thumb_w: int = 320) -> int:
    """Tile the chosen frames into one sheet with index + timestamp labels."""
    if not frames:
        return 0
    thumbs = []
    for p in frames:
        im = cv2.imread(str(p))
        if im is None:
            continue
        scale = thumb_w / im.shape[1]
        h = max(1, int(round(im.shape[0] * scale)))
        t = cv2.resize(im, (thumb_w, h), interpolation=cv2.INTER_AREA)
        label = p.stem.replace("frame_", "f")
        cv2.putText(t, label, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(t, label, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 22, 30), 1, cv2.LINE_AA)
        thumbs.append(t)
    rows = [thumbs[i:i + cols] for i in range(0, len(thumbs), cols)]
    rh = max(t.shape[0] for t in thumbs)
    rw = max(len(row) for row in rows) * thumb_w
    sheet = np.full((rh * len(rows), rw, 3), 16, dtype=np.uint8)
    for r, row in enumerate(rows):
        x = 0
        for t in row:
            sheet[r * rh:(r * rh) + t.shape[0], x:x + t.shape[1]] = t
            x += t.shape[1]
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return len(thumbs)


def sample_video(video: Path, out_dir: Path, max_frames: int = 24, hamming_dist: int = 3,
                 scene_thresh: float = 16.0) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"could not open {video} — is ffmpeg in PATH? (cv2: {cv2.__version__})")
    try:
        meta = probe(cap)
        total = meta["n_frames"]
        if total <= 0:
            for _ in range(10 ** 6):
                if not cap.grab():
                    total = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) or 0
                    break
            if total <= 0:
                raise RuntimeError("could not determine frame count")
        idxs = pick_frames(cap, total, max_frames=max_frames, hamming_dist=hamming_dist,
                           scene_thresh=scene_thresh)
        fps = meta["fps"] or 25.0
        samples = []
        written = []
        for i, idx in enumerate(idxs):
            name = f"frame_{idx:06d}.jpg"
            if write_frame(cap, idx, out_dir / name):
                samples.append({
                    "index": idx,
                    "t_sec": round(idx / fps, 3),
                    "ts": f"{int(idx / fps // 60):02d}:{idx / fps % 60:05.2f}",
                    "file": name,
                })
                written.append(out_dir / name)
        sheet_n = contact_sheet(written, out_dir / "contact_sheet.jpg")
        meta.update({"duration_sec": round(total / fps, 3)})
        samples_out = {
            "tool": "video/frames.py",
            "video": str(video),
            "count": len(samples),
            "params": {"max_frames": max_frames, "hamming": hamming_dist, "scene_thresh": scene_thresh},
            "samples": samples,
        }
        (out_dir / "samples.json").write_text(json.dumps(samples_out, indent=1, ensure_ascii=False), encoding="utf-8")
        (out_dir / "video.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        return {"meta": meta, "count": len(samples), "sheet_frames": sheet_n}
    finally:
        cap.release()


def main() -> None:
    ap = argparse.ArgumentParser(prog="video.py", description="Cut a video into distinct frames for GeoInt.")
    ap.add_argument("video", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("frames"))
    ap.add_argument("--max", type=int, default=24, help="target number of frames (default 24)")
    ap.add_argument("--hamming", type=int, default=3, help="dHash Hamming threshold for near-duplicates (default 3)")
    ap.add_argument("--scene", type=float, default=16.0, help="mean-abs-diff threshold for scene changes (default 16)")
    ap.add_argument("--check", action="store_true", help="verify OpenCV/ffmpeg then exit")
    args = ap.parse_args()

    if args.check:
        print(f"cv2 {cv2.__version__}  ffmpeg: {cv2.videoio_registry.hasFFmpeg()}")
        return
    if not args.video.is_file():
        sys.exit(f"no such video: {args.video}")
    res = sample_video(args.video, args.out_dir, max_frames=args.max,
                       hamming_dist=args.hamming, scene_thresh=args.scene)
    print(f"-> {args.out_dir}/samples.json, contact_sheet.jpg ({res['count']} frames; "
          f"{res['meta']['width']}x{res['meta']['height']} @ {res['meta']['fps']}fps, {res['meta']['duration_sec']}s)")


if __name__ == "__main__":
    main()