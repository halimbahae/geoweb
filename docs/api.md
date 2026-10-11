# GeoWeb HTTP API

The GeoWeb server (`web/app.py`) is a small **standard-library-only** HTTP server
that (a) serves the no-build console under `/`, and (b) drives the recon pipeline
over JSON. Everything is local — default bind `127.0.0.1:8787`, archive root
`~/geoweb-photos`.

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

```bash
python3 web/app.py --root ~/geoweb-photos --port 8787 --open
BASE=http://127.0.0.1:8787
```

Conventions:

- Session names match `^[0-9A-Za-z_.+\-]+$` and are the folder names under the
  archive root.
- Jobs are asynchronous. A `POST` that starts work returns `202` with a job
  descriptor `{job, session, kind, command, started, log, ...}`; poll status to
  see it finish.
- Errors are `{"error": "..."}` with `400` (bad input), `404` (not found),
  `409` (conflict, e.g. session busy), `429` (too many concurrent jobs).
- Limits: uploads ≤ 150 MB; at most `--max-jobs` (default 3) concurrent jobs.

---

## Pages

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/` , `/index.html` | the console |
| `GET` | `/static/*` | CSS, JS, images, vendored Leaflet (nested paths allowed, `..` blocked) |

---

## Health

```bash
curl $BASE/api/health
# {"ok": true, "repo": "/abs/path/geoweb", "uv": "/Users/you/.local/bin/uv"}
```

---

## Sessions

### `GET /api/sessions`

```json
{
  "root": "/Users/you/geoweb-photos",
  "sessions": [
    {
      "name": "2026-10-11_21-02-52-308076+0000",
      "kind": "video",
      "started_at": "2026-10-11T21:02:52.308076+00:00",
      "completed_at": null,
      "status": "pending",
      "result": null,
      "truth": null,
      "photo": "original/demo_two_scenes.mp4",
      "thumb": "files?path=frames/contact_sheet.jpg",
      "jobs": []
    }
  ]
}
```

### `POST /api/sessions` — upload

`multipart/form-data` with a single file field named `photo` (images **and**
videos). The server creates a session folder, byte-copies the file, checksums it,
and — for video — immediately queues frame extraction.

```bash
curl -sX POST $BASE/api/sessions -F photo=@duomo.jpg | jq
curl -sX POST $BASE/api/sessions -F photo=@clip.mp4   | jq
```

```json
{ "name": "2026-10-11_21-02-52-308076+0000", "folder": "...", "kind": "video", "started": true }
```

### `GET /api/session/<name>`

Full state:

```json
{
  "name": "...", "folder": "/abs/path",
  "meta": { "kind": "photo", "status": "pending", "original": {...}, "result": null },
  "result": null, "truth": null,
  "files":  [ { "path": "recon/prior/prior_map.png", "size": 12345 } ],
  "jobs":   [ { "job": "894adbb348c8", "kind": "recon", "status": "running" } ],
  "report": ""
}
```

### `GET /api/session/<name>/recon`

The recon payload used to render the recon view: `has`, `photo`, `steps`
(with `rc` + per-step digest), `md` (the rendered `recon.md`), `prior`
(GeoCLIP clusters / points / guess), and artifact listings.

### `GET /api/session/<name>/recon/status`

```json
{ "running": {"job": "...", "kind": "recon", "started": "..."},
  "jobs": [...], "log_tail": "…last 4 KB…",
  "live": {"steps": [{"key":"meta","state":"done","digest":"4000x3000 · GPS …"}], "done": 6, "total": 6, "finished": true},
  "global_running": 1, "max_jobs": 3, "now": "2026-10-11T21:20:00+00:00" }
```

`live.steps[].state` ∈ `run | done | err`. Poll this to drive a progress bar.

### `GET /api/session/<name>/frames` — video

```json
{ "kind": "video", "done": true, "running": null,
  "video": { "path": "...", "width": 960, "height": 540, "fps": 30, "n_frames": 180, "duration": 6.0 },
  "count": 3,
  "samples": [ { "index": 0, "t_sec": 0.0, "file": "frame_000000.jpg", "ts": "00:00" }, … ],
  "contact": "frames/contact_sheet.jpg",
  "log_path": "/job/<id>/log" }
```

### `GET /api/session/<name>/files?path=<rel>`

Streams any file inside the session (images, `recon.md`, `prior_map.png`, …).
Path is resolved and must stay inside the session folder.

### `GET /api/session/<name>/report` → `{ "content": "...markdown..." }`

### `GET /api/session/<name>/export?fmt=md|json` — download a report

Returns a self-contained, branded export as an attachment
(`Content-Disposition`). `fmt=md` (default) is a Markdown bundle — session
metadata, the answer/ground-truth block, the analyst report and the full
`recon.md`. `fmt=json` is the structured bundle
(`{ schema, exported_at, name, session, report_md, recon }`).

```bash
curl -sOJ "$BASE/api/session/$S/export?fmt=md"     # → <name>-geoweb-report.md
curl -sOJ "$BASE/api/session/$S/export?fmt=json"   # → <name>-geoweb-report.json
```

The console also builds branded **HTML** (logo + author, print stylesheet) and
**PDF** (via the browser's print dialog) client-side from the JSON bundle.

### `GET /api/session/<name>/tools` → `{ "tools": [ …curated tools… ] }`

### `GET /api/session/<name>/job/<jobid>` → `{ "content": "…log tail…" }`

---

## Actions (`POST /api/session/<name>/<action>`)

### `recon` — start a recon

```jsonc
// photo (no body needed for defaults)
{ "no_ml": true, "no_rev": false, "skip": ["prior"] }

// video — analyse one extracted frame
{ "frame": "frame_000075.jpg" }
```

| body key | meaning |
| --- | --- |
| `frame` | video only; `frame_XXXXXX.jpg` from the Frames tab |
| `no_ml` | quick pass: skip the learned world-prior models |
| `no_rev` | skip reverse-image search (Yandex/Baidu) |
| `skip` | list of step names to skip (`meta`, `detect`, `calib`, `prior`, `intake`, `textgeo`) |

```bash
curl -sX POST $BASE/api/session/$S/recon \
  -H 'content-type: application/json' -d '{"no_ml":true}' | jq
```

### `recon/stop` — stop the running recon

### `extract` — re-run video frame extraction

### `report` — save the analyst report

```json
{ "content": "# Report\n…" }
```

### `tools` — run a curated CLI tool

```json
{ "name": "textgeo", "argv": ["--text", "Piazza del Duomo"] }
```

Supported `name`: `textgeo`, `geodata`, `board`, `refsheet`, `image` (raw argv
into `scripts/`). Returns `202` + job descriptor; read output via
`GET /api/session/<name>/job/<jobid>`.

### `rename`

```json
{ "name": "milan-duomo" }
```

Renames the folder and rewrites stale paths inside text artifacts.

### `finish` — close a session with your call

```json
{ "country": "Italy", "region": "Lombardy", "city": "Milan",
  "lat": 45.4642, "lon": 9.19, "confidence": "high" }
```

### `truth` — record ground truth (for scoring)

```json
{ "lat": 45.4642, "lon": 9.19 }
```

### `job/<jobid>/stop` — kill one job

---

## `DELETE /api/session/<name>`

Deletes the session folder and terminates its running jobs.

```bash
curl -sX DELETE $BASE/api/session/$S | jq
```

---

## MCP

Prefer a typed interface for an AI assistant? The same archive is exposed as MCP
tools by `mcp/geoweb_mcp.py` (`sessions`, `session`, `start_recon`,
`recon_status`, `read_file`, `frames`, `tools`). See
[`../mcp/README.md`](../mcp/README.md).
