# GeoWeb HTTP API

The GeoWeb server (`web/app.py`) is a small **standard-library-only** HTTP server
that (a) serves the no-build console under `/`, and (b) drives the recon pipeline
over JSON. Everything is local — default bind `127.0.0.1:8787`, archive root
`~/geoweb-photos`.

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

```bash
python3 web/app.py --root ~/geoweb-photos --port 8787 --open
BASE=http://127.0.0.1:8787
TOKEN=Kx8…                        # the ?token=… the server printed at startup
AUTH="X-GeoWeb-Token: $TOKEN"     # every curl below sends it
```

## Authentication

The server is single-user but **not unauthenticated** (see
[SECURITY.md](../SECURITY.md)). It prints a ready-to-open URL at startup:

```
[webui] Open the console: http://127.0.0.1:8787/?token=Kx8…
```

- **Browser** — open that URL once: `GET /?token=…` answers `303` with an
  `HttpOnly; SameSite=Strict` `geoweb_token` cookie and redirects to `/`; every
  later `/api/*` call is then authenticated, no query token needed.
- **CLI / scripts** — send the token as a header:

```bash
curl -s $BASE/api/sessions -H "$AUTH"
```

Pin the token instead of generating one with `--token <value>` or
`$GEOWEB_TOKEN` (useful for a systemd unit or a reverse proxy).

Failures:

| Case | Response |
| --- | --- |
| Missing/invalid token on `/api/*` | `401 {"error": "unauthorized: …"}` |
| `Host` header is not loopback while bound to loopback (anti DNS-rebinding) | `403 {"error": "forbidden: unexpected Host header"}` |
| non-GET request with a foreign `Origin` | `403 {"error": "forbidden: cross-origin request"}` |

`GET /api/health` is the one exception: it answers `200` without a token but then
returns `{"ok": true, "authenticated": false}` (no `repo`/`uv`), so a container
healthcheck keeps working while nothing about the machine leaks.

Conventions:

- Session names match `^[0-9A-Za-z_.+\-]+$` and are the folder names under the
  archive root.
- Jobs are asynchronous. A `POST` that starts work returns `202` with a job
  descriptor `{job, session, kind, command, started, log, ...}`; poll status to
  see it finish.
- Errors are `{"error": "..."}` with `400` (bad input), `401` (no/invalid token),
  `403` (bad Host or cross-origin), `404` (not found), `409` (conflict, e.g.
  session busy), `429` (too many concurrent jobs).
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
curl -s $BASE/api/health -H "$AUTH"
# {"ok": true, "authenticated": true, "repo": "/abs/path/geoweb", "uv": "/Users/you/.local/bin/uv"}
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
curl -s $BASE/api/sessions -H "$AUTH" | jq
curl -sX POST $BASE/api/sessions -H "$AUTH" -F photo=@duomo.jpg | jq
curl -sX POST $BASE/api/sessions -H "$AUTH" -F photo=@clip.mp4   | jq
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
  "lens":   { "status": "ok", "place": "…", "links": [ … ] },
  "dossier": { "address": "…", "phone": [], "site": {…}, "sources": [ … ], "images": [ … ] },
  "report": ""
}
```

`lens` and `dossier` are `{}` until those steps have run.

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
curl -sOJ "$BASE/api/session/$S/export?fmt=md"   -H "$AUTH"   # → <name>-geoweb-report.md
curl -sOJ "$BASE/api/session/$S/export?fmt=json" -H "$AUTH"   # → <name>-geoweb-report.json
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
curl -sX POST $BASE/api/session/$S/recon -H "$AUTH" \
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

### `lens` — reverse-image search (Google Lens)

Drives Lens in Chromium through Playwright (`make lens-install`), captures the
overview sentence, the exact/visual match links and a screenshot into
`recon/lens/lens.json`. A CAPTCHA wall is recorded as `"status": "blocked"` —
it is never worked around or guessed.

```jsonc
{}                                   // start the browser job (202 + job descriptor)
{ "headed": true }                   // show the browser, so a human can pass the wall
{ "frame": "frame_000075.jpg" }      // analyse one video frame
```

If Google walls the automated browser, import a capture taken by hand — the
same parser writes the same evidence file:

```jsonc
{ "text": "…Lens results page text…", "url": "https://lens.google.com/search?…" }
```

That call is synchronous and returns `{ "ok": true, "imported": true, "lens": {…} }`.

### `dossier` — the venue's own sources, contacts and photographs

```jsonc
{ "name": "Cinéma Le Colisée", "city": "Marrakech", "country": "MA",
  "lat": 31.635786, "lon": -8.015242 }
```

`name` defaults to the session's recorded city. Collects the venue website
(address, `tel:` numbers, e-mails, socials, photos), OSM/Nominatim tags and
press mentions (Google News RSS + web results), dropping off-topic hits by name
relevance. Writes `recon/sources/dossier.json` + `recon/sources/img_*`, returns
`202` + a job descriptor.

### `chat` — ask this session a question

```jsonc
{ "message": "what phone number does the venue publish?",
  "history": [ { "role": "user", "content": "…" }, { "role": "assistant", "content": "…" } ] }
```

Synchronous. The answer is built only from this session's report, recon summary,
Lens capture and dossier, through a local Ollama model (`GEOWEB_CHAT_MODEL`,
`GEOWEB_OLLAMA`). Returns `{ "answer": "…", "model": "…", "seconds": 19.2 }`;
`503` with a message when Ollama is not reachable.

### `GET /api/assistant` — model availability

```json
{ "available": true, "models": ["qwen3.5:4b"], "default": "qwen3.5:4b",
  "host": "http://127.0.0.1:11434" }
```

---

## The automatic chain

When a recon finishes on a session with no recorded answer, the server starts
the Lens fallback by itself; a successful capture is then followed by the
sources dossier (named from the Lens entity line). A walled or unavailable
Lens stops the chain and the Sources tab offers the paste-in import instead.
Disable with `GEOWEB_AUTO_FALLBACK=0`.

---

## `DELETE /api/session/<name>`

Deletes the session folder and terminates its running jobs.

```bash
curl -sX DELETE $BASE/api/session/$S -H "$AUTH" | jq
```

---

## MCP

Prefer a typed interface for an AI assistant? The same archive is exposed as MCP
tools by `mcp/geoweb_mcp.py` (`sessions`, `session`, `start_recon`,
`recon_status`, `read_file`, `frames`, `lens`, `import_lens`, `sources`, `ask`,
`tools`). See
[`../mcp/README.md`](../mcp/README.md).
