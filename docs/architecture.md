# Architecture

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

```
            ┌──────────────────────── web/app.py (stdlib HTTP) ───────────────────────┐
 browser ─► │  /              → web/static/  (no-build console, vendored Leaflet)       │
 (console)  │  /api/session/* → JSON: sessions, recon, frames, tools, actions           │
            │  job runner     → subprocess + uv run, capped, logged, stoppable          │
            └───────────────┬───────────────────────────────┬─────────────────────────┘
                            │ uv run                         │ uv run
                    scripts/*.py  (GeoINT engine, MIT)   video/frames.py (OpenCV)
                            │                                │
                            └──────────────┬─────────────────┘
                                           ▼
                          archive root  ~/geoweb-photos/<session>/
                              original/  session.json  recon/…  frames/…
```

## Components

- **`web/app.py`** — a single-file server built only on the Python standard
  library. It serves the static console, exposes the JSON API, and owns the job
  runner: every pipeline step is a `uv run` subprocess, limited to `--max-jobs`
  concurrently, with its stdout captured to `…/.webui/jobs/<id>.log` and a
  matching `.json` status record. Jobs can be stopped (terminate → kill).
- **`web/static/`** — the front end, deliberately **no build step**: plain
  `index.html` + `app.js` + `styles.css`, with Leaflet vendored under
  `vendor/leaflet/`. The interactive prior map, the frames grid and the job bar
  all live in `app.js`.
- **`scripts/`** — the **vendored** recon engine (from the MIT-licensed GeoINT
  project). Each script carries its own PEP-723 dependency header, so `uv run`
  materialises the right environment per step. GeoWeb treats these as a
  dependency: prefer fixing them upstream; keep attribution (see `NOTICE`).
- **`video/frames.py`** — GeoWeb's own OpenCV sampler (scene change + dHash
  dedupe → contact sheet).
- **`mcp/geoweb_mcp.py`** — a Model Context Protocol server that reuses the same
  archive root and the same subprocess jobs, so the console and an AI assistant
  never write concurrently.

## The recon pipeline

Each step reads the image and writes a small artifact under `recon/`:

| step | artifact | contributes |
| --- | --- | --- |
| `meta` | `recon/meta/meta.json` | EXIF GPS/time, camera, dimensions |
| `intake` | `recon/intake/intake.json` | OCR text + reverse-image-search sheets |
| `textgeo` | `recon/textgeo.json` | text → candidate countries (log-LR) |
| `detect` | `recon/detect/detect.json` | objects + pixel coordinates |
| `calib` | `recon/calib.json` | field of view / 35 mm-equivalent focal length |
| `prior` | `recon/prior/prior.json`, `prior_map.png` | learned world priors + GeoCLIP map |

When the steps finish, `recon.py` renders `recon/recon.md`, the human summary the
console shows. The GeoCLIP **prior map** is served as `recon/prior/prior_map.png`
and, in GeoWeb, overlaid on the interactive map alongside cluster/point/guess
overlays parsed from `prior.json`.

## Archives

```
~/geoweb-photos/<session>/
  session.json            kind, status, original, result, truth
  original/<file>
  report.md               analyst report (optional)
  recon/…                 step artifacts + recon.md + prior/prior_map.png
  frames/…                video sessions: frames, contact sheet, samples.json
  .webui/jobs/<id>.log    job stdout
  .webui/jobs/<id>.json   job status record
```

Sessions are plain folders: portable, diffable, backup-friendly, git-ignored.

## Design choices

- **Stdlib-only server** keeps installs trivial and the surface auditable.
- **PEP-723 scripts + uv** mean heavy ML deps are pulled only when a step runs.
- **Vendored engine + NOTICE** cleanly separates *GeoWeb's* MIT code from the
  upstream engine it wraps, including licensing boundaries for the models.
- **No-build front end** so the whole UI is three files and a Leaflet drop-in.
