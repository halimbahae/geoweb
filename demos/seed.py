#!/usr/bin/env python3
# GeoWeb · author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
# /// script
# requires-python = ">=3.10"
# ///
"""Seed GeoWeb with the bundled demo archive.

Copies the demo media (3 photos + 2 videos, see demos/README.md for sources)
into the archive root, creates sessions, cuts video frames, then runs the FULL
recon (metadata, OCR, reverse search, text→countries, detection, calibration,
world prior) on each — directly on the photo, or on the best frame of a video.
Prints a summary table. Idempotent: finished demos are skipped unless --force.

  python3 demos/seed.py                              # ~/geoweb-photos, full recon
  python3 demos/seed.py --root /mnt/photos --recon quick
  python3 demos/seed.py --force

--recon full runs every step (needs the ML weights, cached on first use);
--recon quick is the fast no-model pass; none just imports the media.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MEDIA = Path(__file__).resolve().parent / "media"
SCRIPTS = REPO / "scripts"
VIDEO_PY = REPO / "video" / "frames.py"
UV = os.environ.get("UV") or "uv"

DEMOS = [
    {"name": "demo-image-1", "media": "demo-image-1.jpg", "kind": "photo",
     "what": "Milan Cathedral, Italy — landmark, clean sun, GPS stripped"},
    {"name": "demo-image-2", "media": "demo-image-2.jpg", "kind": "photo",
     "what": "Colosseum, Rome (CC0) — architecture + people"},
    {"name": "demo-image-3", "media": "demo-image-3.jpg", "kind": "photo",
     "what": "Shibuya scramble crossing, Tokyo (CC0) — dense signs & text"},
    {"name": "demo-image-4", "media": "demo-image-4.jpg", "kind": "photo",
     "what": "Eiffel Tower, Paris (public domain) — tower + Champ de Mars"},
    {"name": "demo-image-5", "media": "demo-image-5.jpg", "kind": "photo",
     "what": "Taj Mahal, Agra (CC BY-SA 4.0) — EXIF stripped"},
    {"name": "demo-video-1", "media": "demo-video-1.mp4", "kind": "video",
     "what": "Real footage (Pexels), Tokyo street at night — neon signs"},
    {"name": "demo-video-2", "media": "demo-video-2.mp4", "kind": "video",
     "what": "Real footage (Pexels), Colosseum in daylight"},
]


def run(cmd: list[str], cwd: Path) -> int:
    print("  $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd), env={**os.environ, "PYTHONUTF8": "1",
                                                  "PYTHONUNBUFFERED": "1",
                                                  "TOKENIZERS_PARALLELISM": "false"}).returncode


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_session(root: Path, d: dict) -> Path:
    folder = root / d["name"]
    (folder / "original").mkdir(parents=True, exist_ok=True)
    src = MEDIA / d["media"]
    rel = f"original/{src.name}"
    shutil.copy2(src, folder / rel)
    meta = {
        "schema_version": 1,
        "timestamp": d["media"].rsplit(".", 1)[0],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000+00:00", time.gmtime()),
        "timezone": None,
        "status": "pending",
        "kind": d["kind"],
        "demo": {"what": d["what"]},
        "original": {
            "source_path": "demos/media/" + src.name,
            "relative_path": rel,
            "sha256": sha256(src),
        },
    }
    (folder / "session.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "report.md").write_text(f"# {d['name']}\n\nDemo seeded from `demos/media/{src.name}`.\n",
                                      encoding="utf-8")
    return folder


def seed(root: Path, recon_mode: str, force: bool) -> list[dict]:
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for d in DEMOS:
        name = d["name"]
        folder = root / name
        if force and folder.is_dir():
            shutil.rmtree(folder)
        done = (folder / "recon" / "recon.md").is_file()
        if done:
            print(f"[skip]    {name} — already recon'd (use --force to re-run)")
            results.append({"name": name, "status": "skipped", "photo": ""})
            continue
        print(f"[{ 'video' if d['kind'] == 'video' else 'photo' }]  {name}")
        if not folder.is_dir() or not (folder / "session.json").is_file():
            folder = make_session(root, d)

        rel = json.loads((folder / "session.json").read_text(encoding="utf-8"))["original"]["relative_path"]
        if not (folder / rel).is_file():
            results.append({"name": name, "status": "media-missing", "photo": ""})
            continue
        if d["kind"] == "video" and not (folder / "frames" / "samples.json").is_file():
            rc = run([UV, "run", "-q", str(VIDEO_PY), rel, "--out-dir", "frames"], folder)
            if rc:
                results.append({"name": name, "status": "frames-failed", "photo": ""})
                continue
            samples = json.loads((folder / "frames" / "samples.json").read_text(encoding="utf-8"))["samples"]
            pick = max(samples, key=lambda s: s["index"])  # last scene = most info
            rel = "frames/" + pick["file"]
            print(f"       picked frame {pick['file']} (t {pick['ts']}) for recon")

        if recon_mode == "full":
            rc = run([UV, "run", "-q", str(SCRIPTS / "recon.py"), rel, "--out-dir", "recon"], folder)
        elif recon_mode == "quick":
            rc = run([UV, "run", "-q", str(SCRIPTS / "recon.py"), rel, "--out-dir", "recon", "--no-ml"], folder)
        else:
            rc = 0
        status = "ok" if rc == 0 else "recon-failed"
        results.append({"name": name, "status": status, "photo": rel})
    return results


def main() -> None:
    ap = argparse.ArgumentParser(prog="geoweb-demos", description=__doc__)
    ap.add_argument("--root", default=str(Path.home() / "geoweb-photos"), help="archive root")
    ap.add_argument("--recon", choices=["full", "quick", "none"], default="full",
                    help="full = all steps incl. ML prior (default), quick = fast no-model pass")
    ap.add_argument("--force", action="store_true", help="erase and re-seed existing demo sessions")
    args = ap.parse_args()

    print(f"Seeding GeoWeb demo archive into {args.root} (recon: {args.recon})")
    t0 = time.time()
    results = seed(Path(args.root), args.recon, args.force)
    print("\nSummary")
    for r in results:
        print(f"  {r['name']:<20} {r['status']}")
    print(f"\nDone in {time.time() - t0:.0f}s. Open the console and look for the demo-* sessions.")


if __name__ == "__main__":
    main()