---
name: geoweb
description: Use when working in the GeoWeb repository — building, running, or extending the geolocation console, the video frame sampler, the MCP server, or its landing page. Covers layout, run/debug commands, the recon pipeline, license boundaries, and where new code belongs.
license: MIT
metadata:
  author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
---

# GeoWeb

GeoWeb answers "where was this taken?" for photos **and videos**. It is a
local-first, open-source browser console around a full recon pipeline, plus an
MCP server, OpenCV video frame sampling, Docker packaging, and a GitHub Pages
landing site.

Everything runs on the user's machine: the server (`web/app.py`) is standard
-library-only Python, and every pipeline step is `uv run scripts/*.py`
(scripts declare their own deps as PEP-723 headers).

## Repository map

| Path | What it is |
| --- | --- |
| `web/app.py` | HTTP server + job runner (stdlib only). Serves `web/static/`, owns the `/api/session/...` JSON API. |
| `web/static/` | No-build front end: `index.html`, `app.js`, `styles.css`, vendored Leaflet. |
| `scripts/` | **Vendored complementously** from marouane53/GeoINT (MIT) — the recon engine. Change the method upstream; fix GeoWeb-side bugs per-file. |
| `video/frames.py` | OpenCV frame sampler: scene detect + dHash dedupe → contact sheet. |
| `mcp/geoweb_mcp.py` | Model Context Protocol server exposing the archive as MCP tools. |
| `landing/` | Static marketing site, deployed to GitHub Pages on `main`. |
| `docs/` | Quickstart, using-the-console, video guide, API reference, architecture, deployment. |
| `tests/`, `Makefile`, `Dockerfile`, `.github/` | CI, packaging, health. |

## Commands

```bash
python3 web/app.py --open            # run the console (default http://127.0.0.1:8787)
uv run video/frames.py clip.mp4 --out-dir frames   # cut a video into frames
uv run mcp/geoweb_mcp.py             # MCP server (stdio)
make ci                              # ruff + pytest + py_compile + node --check
make serve / make test / make lint / make docker
```

Conventions: ruff (E/F/I/UP, line-length 120), target py3.10+. Server has no
third-party imports. Scripts and MCP/video use PEP-723 inline deps so `uv run`
works from any cwd (session folders are outside the repo).

## Workflow you will be asked to run

1. **Photo**: upload → `photo_session.py start` (byte-copy, checksum). Recon =
   `recon.py <rel> --out-dir recon` per session; steps write `recon/<step>/`,
   `recon.md` when finished; `recon/prior/prior_map.png` is the GeoCLIP map.
2. **Video**: upload sets `kind=video`, then `video/frames.py` cuts frames into
   `<session>/frames/`; recon runs on ONE selected frame (`POST .../recon` with
   `frame=frame_XXXXXX.jpg`).
3. **MCP**: `mcp/geoweb_mcp.py` reuses the same root (`GEOWEB_ROOT`, default
   `~/geoweb-photos`) and the same subprocess jobs — never two writers.

## Rules

- Never break `web/app.py`'s stdlib-only guarantee.
- Keep `scripts/` attribution: see NOTICE + LICENSE (MIT, upstream GeoINT).
  Some models are CC-BY-NC (StreetCLIP) — do not claim a permissive stack.
- Author header on every our-authored source file: `Bahae Eddine HALIM
  <https://www.linkedin.com/in/halimbahae/>`.
- Local archives and test media never get committed (`.gitignore`).