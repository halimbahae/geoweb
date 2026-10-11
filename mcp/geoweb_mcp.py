#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2", "requests"]  # requests is only used for the SSE health check
# ///
"""GeoWeb MCP server — give your AI agents hands on the GeoWeb archive.

A stdio/server-sent-event (SSE) Model Context Protocol server that exposes a
local GeoWeb archive (the `~/geoweb-photos` sessions) as MCP tools:

    sessions        list every session and its outcome
    session         one session: metadata, jobs, report, recon status
    recon           start a recon (quick/full) on a session, or one video frame
    recon_status    per-step progress + the rendered recon summary
    read_file       read a text file inside a session (recon.md, prior.json, ...)
    frames          video sessions: the extracted contact sheet + frame list
    tools           every curated CLI tool the web console offers (textgeo, board, ...)

The server is read-only apart from starting recon jobs, which use the same
`uv run` subprocesses as web/app.py and write to <session>/.webui/jobs/ so the
two interfaces never fight. Nothing leaves the machine.

Run:
    GEOWEB_ROOT=~/geoweb-photos python3 mcp/geoweb_mcp.py            # stdio (default)
    GEOWEB_ROOT=~/geoweb-photos python3 mcp/geoweb_mcp.py --transport sse --port 8989
    uv run mcp/geoweb_mcp.py
"""

# Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP

UV = os.environ.get("UV") or "uv"

SESSION_NAME = re.compile(r"^[0-9A-Za-z_.+\-]+$")
RECON_STEPS = [
    ("meta", "recon/meta/meta.json", "Metadata"),
    ("intake", "recon/intake/intake.json", "OCR + reverse search"),
    ("textgeo", "recon/textgeo.json", "Text → countries"),
    ("detect", "recon/detect/detect.json", "Object detection"),
    ("calib", "recon/calib.json", "Camera calibration"),
    ("prior", "recon/prior/prior.json", "World prior"),
]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".mkv", ".avi"}

ROOT = Path(os.environ.get("GEOWEB_ROOT", str(Path.home() / "geoweb-photos")))
REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
VIDEO_PY = REPO / "video" / "frames.py"

mcp = FastMCP("geoweb-mcp")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def session_folder(name: str) -> Path:
    if not SESSION_NAME.fullmatch(name):
        raise ValueError(f"invalid session name {name!r}")
    folder = (ROOT / name).resolve()
    if not folder.is_relative_to(ROOT.resolve()) or not (folder / "session.json").is_file():
        raise ValueError(f"no such session: {name}")
    return folder


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def job_dir(folder: Path) -> Path:
    d = folder / ".webui" / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _base_env() -> dict:
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"}


def _step_digest(kind: str, folder: Path) -> str:
    """Cheap human digest for a recon step, mirroring web/app.py."""
    try:
        if kind == "meta":
            j = read_json(folder / "recon/meta/meta.json").get("digest", {})
            g = j.get("gps") or {}
            gps = f"GPS {g['lat']},{g['lon']}" if g.get("lat") is not None else "no GPS"
            return f"{j.get('width')}x{j.get('height')} · {gps}"
        if kind == "intake":
            j = read_json(folder / "recon/intake/intake.json")
            rev = j.get("reverse") or {}
            n = [k for k, v in (rev.get("engines") or {}).items() if v == "ok"]
            return f"OCR {len(j.get('ocr') or [])} text item(s) · reverse {len(n)}/{len(rev.get('engines') or {})} sheets"
        if kind == "textgeo":
            j = read_json(folder / "recon/textgeo.json")
            short = j.get("shortlist") or []
            return f"{','.join(x.get('name', '?') for x in short[:2])} (log LR {short[0]['log_lr']})" if short else "no shortlist"
        if kind == "detect":
            j = read_json(folder / "recon/detect/detect.json")
            d = j.get("detections") or []
            by = {}
            for x in d:
                by[x.get("cls")] = by.get(x.get("cls"), 0) + 1
            return f"{len(d)} detection(s), {','.join(sorted(by)[:4])}"
        if kind == "calib":
            j = read_json(folder / "recon/calib.json")
            return f"hfov {j.get('hfov_deg')}, 35 mm eq {j.get('focal_35mm_equiv')}" if j.get("hfov_deg") else "n/a"
        if kind == "prior":
            j = read_json(folder / "recon/prior/prior.json")
            gc = j.get("geoclip") or {}
            comb = j.get("combined") or []
            cls = gc.get("clusters")
            bg = j.get("best_guess")
            return f"{len(cls or [])} cluster(s) · geo: {(comb[0].get('name') or '?') if comb else '?'}" + (
                f" · combined: {bg.get('near')}" if bg else "")
    except (AttributeError, TypeError, KeyError, ValueError):
        return ""
    return ""


def recon_live(folder: Path) -> dict:
    recon_json = read_json(folder / "recon/recon.json").get("steps", {})
    steps = []
    done_total = 0
    for key, rel, label in RECON_STEPS:
        done = (folder / rel).is_file()
        entry = recon_json.get(key, {})
        if done:
            done_total += 1
        steps.append({
            "key": key, "label": label,
            "state": "err" if entry.get("rc") not in (None, 0) else ("done" if done else "run"),
            "digest": _step_digest(key, folder),
        })
    return {
        "steps": steps,
        "done": done_total,
        "total": len(RECON_STEPS),
        "finished": (folder / "recon" / "recon.md").is_file(),
    }


# --------------------------------------------------------------------------- #
# tools
# --------------------------------------------------------------------------- #

@mcp.tool()
def sessions(recent: int = 20, only_name: str = "") -> list[dict]:
    """List GeoWeb archive sessions (newest first): name, kind, status, result, recon summary presence."""
    if not ROOT.is_dir():
        return []
    out = []
    for folder in sorted(ROOT.iterdir()):
        meta = read_json(folder / "session.json")
        if not meta:
            continue
        if only_name and only_name not in folder.name:
            continue
        res = meta.get("result") or {}
        out.append({
            "name": folder.name,
            "kind": meta.get("kind", "photo"),
            "started_at": meta.get("started_at"),
            "completed_at": meta.get("completed_at"),
            "status": meta.get("status"),
            "result": {k: res.get(k) for k in ("country", "region", "city_or_nearest_locality", "latitude", "longitude", "confidence")} if res else None,
            "truth_error_km": (meta.get("truth") or {}).get("error_km"),
            "recon": (folder / "recon" / "recon.md").is_file(),
        })
    out.sort(key=lambda s: s["started_at"] or "", reverse=True)
    return out[:recent]


@mcp.tool()
def session(name: str) -> dict:
    """Everything known about one session: meta, jobs, report text and the recon summary (recon.md)."""
    folder = session_folder(name)
    meta = read_json(folder / "session.json")
    jobs = []
    jdir = folder / ".webui" / "jobs"
    if jdir.is_dir():
        for jf in sorted(jdir.glob("*.json")):
            jobs.append(read_json(jf))
    md = folder / "recon" / "recon.md"
    return {
        "name": name,
        "meta": meta,
        "jobs": jobs,
        "report": (folder / "report.md").read_text(encoding="utf-8", errors="replace") if (folder / "report.md").is_file() else "",
        "recon_summary": md.read_text(encoding="utf-8", errors="replace")[:30000] if md.is_file() else "",
        "live": recon_live(folder) if md.is_file() else None,
    }


@mcp.tool()
def recon_status(name: str) -> dict:
    """Per-step progress of a session's recon (tags, digests) and whether recon.md is finished."""
    folder = session_folder(name)
    live = recon_live(folder)
    md = folder / "recon" / "recon.md"
    return {
        "name": name,
        "finished": live["finished"],
        "done": live["done"],
        "total": live["total"],
        "steps": live["steps"],
        "summary_head": md.read_text(encoding="utf-8", errors="replace")[:4000] if md.is_file() else "",
    }


@mcp.tool()
def start_recon(name: str, mode: str = "quick", frame: str = "", no_rev: bool = False,
                skip: str = "") -> dict:
    """Start a recon on a session (mode 'quick' = fast, no ML models | 'full' = includes the learned world prior).
    For a video session pass a frame file (e.g. 'frame_000075.jpg') from the frames tool. Reuses the same
    scripts the web console runs; a running job is tracked like any other."""
    folder = session_folder(name)
    meta = read_json(folder / "session.json")
    if frame:
        if not re.fullmatch(r"[0-9A-Za-z_.+\-]+", frame) or not frame.lower().endswith(tuple(IMAGE_EXTS)):
            raise ValueError("invalid frame name")
        rel = "frames/" + frame
    else:
        rel = (meta.get("original") or {}).get("relative_path") or ""
        if not rel:
            raise ValueError("session has no original file")
        if meta.get("kind") == "video":
            raise ValueError("video sessions need a frame — list them with the frames tool")
    cmd = [UV, "run", "-q", str(SCRIPTS / "recon.py"), rel, "--out-dir", "recon"]
    if mode == "quick":
        cmd.append("--no-ml")
    if no_rev:
        cmd.append("--no-rev")
    for part in [p.strip() for p in skip.split(",") if p.strip()]:
        cmd += ["--skip", part]
    jl = job_dir(folder) / (uuid.uuid4().hex[:12] + ".log")
    log = open(jl, "a", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(folder), stdout=log, stderr=subprocess.STDOUT,
                            text=True, env=_base_env())
    job_id = jl.stem

    def wait() -> None:
        try:
            rc = proc.wait()
        finally:
            log.close()
        payload = {"job": job_id, "session": name, "status": "done" if rc == 0 else "failed",
                   "rc": rc, "kind": "recon", "command": [str(c) for c in cmd],
                   "started": None, "ended": time.strftime("%Y-%m-%dT%H:%M:%S.000+00:00"),
                   "log": jl.name}
        try:
            (job_dir(folder) / (job_id + ".json")).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    threading.Thread(target=wait, daemon=True).start()
    return {"job": job_id, "session": name, "status": "running", "photo": rel, "log": jl.name}


@mcp.tool()
def read_file(name: str, rel: str) -> str:
    """Read a text file inside a session by relative path, e.g. 'recon/prior/prior.json' or 'report.md'."""
    folder = session_folder(name)
    p = (folder / rel).resolve()
    if not p.is_relative_to(folder.resolve()):
        raise ValueError("invalid path")
    if not p.is_file():
        raise ValueError(f"no such file: {rel}")
    if p.suffix.lower() not in {".json", ".md", ".txt", ".html", ".csv", ".log"}:
        raise ValueError("not a text file (use the files endpoint for binaries)")
    return p.read_text(encoding="utf-8", errors="replace")[:60000]


@mcp.tool()
def frames(name: str) -> dict:
    """Video sessions: the extracted frame list (index, timestamp, file) and the contact-sheet image path."""
    folder = session_folder(name)
    meta = read_json(folder / "session.json")
    samples = read_json(folder / "frames/samples.json")
    video = read_json(folder / "frames/video.json")
    contact = folder / "frames/contact_sheet.jpg"
    return {
        "kind": meta.get("kind"),
        "done": bool(samples.get("samples")),
        "count": len(samples.get("samples") or []) if samples else 0,
        "samples": (samples.get("samples") or []) if samples else [],
        "video": video,
        "contact_rel": "frames/contact_sheet.jpg" if contact.is_file() else "",
    }


@mcp.tool()
def tools() -> list[dict]:
    """The curated CLI tools the console exposes (textgeo, geodata, board, refsheet) with their inputs."""
    return [
        {"name": "textgeo", "label": "Text → countries / phones / brands / places", "input": "text"},
        {"name": "geodata", "label": "GeoNames lookup", "input": "query or cc[-admin1]"},
        {"name": "board", "label": "Reasoning board (init/apply/clue/ingest/rank/next/check/report)", "input": "cmd"},
        {"name": "refsheet", "label": "Reference sheets", "input": "no input"},
        {"name": "image", "label": "Run any scripts/*.py with an argv list", "input": "argv"},
    ]


def main() -> None:
    global ROOT
    ap = argparse.ArgumentParser(prog="geoweb-mcp", description="MCP server for a GeoWeb archive")
    ap.add_argument("--root", default=str(ROOT), help=f"archive root (default {ROOT})")
    ap.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    ap.add_argument("--port", type=int, default=8989, help="port for --transport sse")
    args = ap.parse_args()
    ROOT = Path(args.root)
    ROOT.mkdir(parents=True, exist_ok=True)
    mcp_args = {"transport": args.transport}
    if args.transport == "sse":
        mcp_args["host"] = "127.0.0.1"
        mcp_args["port"] = args.port
    print(f"[geoweb-mcp] root={ROOT} transport={args.transport}", file=__import__("sys").stdout, flush=True)
    mcp.run(**mcp_args)


if __name__ == "__main__":
    main()