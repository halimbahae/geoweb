# AGENTS.md

Guidance for coding agents working in the GeoWeb repository.

## Project

GeoWeb = local-first browser console for photo & video geolocation. Repo:
`halimbahae/geoweb`. Author: **Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>**.

## Layout

- `web/app.py` — HTTP server + job runner, **stdlib-only Python** (never add
  third-party imports here).
- `web/static/` — no-build front end (`index.html`, `app.js`, `styles.css`,
  vendored Leaflet under `vendor/`).
- `scripts/` — **vendored** from marouane53/GeoINT (MIT). Preferred edits happen
  upstream; local fixes are permitted but keep attribution (see NOTICE).
- `video/frames.py` — OpenCV frame sampler (PEP-723 deps).
- `mcp/geoweb_mcp.py` — MCP server (PEP-723 deps, `mcp<2`).
- `landing/` — static GitHub Pages marketing site.
- `docs/`, `tests/`, `.github/`, `Dockerfile`, `Makefile`.

## Commands

```bash
python3 web/app.py --open --root ~/geoweb-photos    # console (port 8787)
uv run video/frames.py clip.mp4 --out-dir frames    # cut frames
uv run mcp/geoweb_mcp.py                            # MCP server
make ci   # ruff + pytest + py_compile + node --check
make lint / make test / make pycheck / make docker / make serve
```

## Conventions

- Ruff (E/F/I/UP), line-length 120, target py3.10+.
- Scripts/MCP/video use PEP-723 inline `# /// script` dependency headers.
- Recon writes into the session folder `<root>/<session>/recon/...`; finished
  recon shows `recon.md`; the GeoCLIP map is `recon/prior/prior_map.png`.
- Video uploads → `kind=video` sessions → auto-extract frames; recon runs on a
  single chosen `frame_XXXXXX.jpg`.
- Author header line on every our-authored file:
  `Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>`.
- Never commit user media or session archives.

## Verify before finishing

`make ci`. For doc/branding changes also run a server smoke test locally.