<!-- GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/> -->
# GeoWeb Console

A local browser interface around the photo & video geolocation scripts — upload a photo, run the
recon pass, read the evidence, run the smaller lookups, and finish or score the
per-photo archive, all without touching a terminal.

Everything runs on this machine. The server is a single dependency-free Python
file (`app.py`, standard library only); every real pipeline still goes through the
existing `scripts/*.py` tools via `uv run`. Reads/writes only touch the photo archive root (default
`~/geoweb-photos`).

## Run

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
python3 web/app.py                      # → http://127.0.0.1:8787
python3 web/app.py --port 8788          # different port
python3 web/app.py --root /data/photos  # a different archive root
python3 web/app.py --open               # open the browser
```

The server prints a ready-to-open `…/?token=…` URL at startup — use it (or
`--open`) once per browser: it sets the `geoweb_token` cookie that authenticates
every `/api/*` call. Pin the token with `--token` / `$GEOWEB_TOKEN`.

Then drag a photo into the drop zone. **Quick recon** runs the fast first pass
(metadata, OCR + text→country, edge/corner crops, Yandex + Baidu reverse image
search) with no local models. **Full recon (ML)** also runs the world-prior models,
object detection and camera calibration; the first full run downloads several GB of
model weights into `~/.cache` (same downloads as `doctor.py --models`).

## What you can do

- **Upload** a photo → creates the timestamped archive via `photo_session.py start`.
- **Recon** → `recon.py`, streamed to a live log; the Overview tab renders the
  `recon.md` summary plus the structured outputs (metadata digest, OCR, text→country
  signals, world prior, calibration, detections).
- **Evidence** → every image the pipeline produced (edge crops, OCR boxes, reverse
  search screenshots, detector sheet, prior map, reference sheets) with a lightbox.
- **Tools** → parameterised, no-shell wrappers for `textgeo.py`, `geodata.py`,
  `board.py` (init / apply / clue / ingest / rank / next / check / report) and
  `refsheet.py`, plus a free-form `argv` runner for the other scripts.
- **Sources** → the Google Lens capture (overview sentence, exact vs visual
  matches, screenshot) and the venue dossier (website, address, phone/e-mail,
  socials, press mentions, photo grid). If Google walls the automated browser the
  tab hands you the photo and a paste box instead of inventing a result.
- **Assistant** → ask this session anything in plain language; answers come only
  from its report, recon summary, Lens capture and dossier, via local Ollama
  (`GEOWEB_CHAT_MODEL`, `GEOWEB_OLLAMA`). A concluded session opens here first.
- **Report** → edit `report.md` in place and **Finish archive**
  (`photo_session.py finish`, renames the folder with the answer) or
  **Record ground truth** (`photo_session.py truth`, scores the guess).

Up to `--max-jobs` GeoWeb jobs run at once (default 3; a full recon is expensive),
so slow steps from different sessions run in parallel rather than blocking the tab;
oversubscribing returns `409` until a slot frees up.

## Layout

```
web/
  app.py          local HTTP server + job runner (stdlib only)
  static/         index.html / app.js / styles.css (no build step)
  README.md       this file
```

Job state lives in `<session>/.webui/jobs/` (git-invisible next to each archive),
so a restarted server still sees finished jobs.

## Notes

- Binds to `127.0.0.1` by default — a local-only tool, not for public hosting.
- **Access control** — `/api/*` requires the access token (generated at startup
  and printed as the `?token=…` URL, or pinned with `--token` / `$GEOWEB_TOKEN`).
  A loopback-bound server only answers loopback `Host` headers (anti
  DNS-rebinding) and a non-GET request carrying a foreign `Origin` is refused.
  `GET /api/health` stays public but then reports `"authenticated": false` and
  no machine paths. See [SECURITY.md](../SECURITY.md).
- The server never evaluates shell; all script invocations go through
  `subprocess` argument lists.
- `test_photo.jpg` and the `~/geoweb-photos` archives are just your local test data,
  not part of the repo.