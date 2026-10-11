# Changelog

All notable changes to GeoWeb are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow
[SemVer](https://semver.org/).

GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## [Unreleased]

### Added

- **GeoWeb brand & author** — the whole project is rebranded from the GeoInt
  web console to **GeoWeb**, with the author header
  (`Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>`) on every source file.
- **GeoWeb-MCP** (`mcp/geoweb_mcp.py`) — Model Context Protocol server exposing
  `sessions`, `session`, `start_recon`, `recon_status`, `read_file`, `frames`
  and `tools` over stdio or SSE, read-only against the archive except for
  launching recon jobs through the same subprocess runner as the console.
- **GeoWeb skill** (`skills/geoweb/SKILL.md`) + `AGENTS.md` + `opencode.json`
  (registers the skill path and the MCP server).
- **API documentation** (`docs/api.md`) — every HTTP endpoint with examples.
- **Video frames feature** — `video/frames.py` (OpenCV scene-change + dHash
  dedupe → contact sheet), video sessions in the console, Frames tab, frame
  selection, and video recon.
- **Interactive GeoCLIP prior map** — Leaflet-based, OSM + prior-snapshot
  overlays, cluster chips, model point guess, fullscreen.
- Complete `docs/` set (quickstart, console guide, video guide, architecture,
  deployment), landing page + GitHub Pages publishing, Docker packaging,
  CI workflow, tests, and community files.
- **Bundled demo archive** (`demos/`) — `seed.py` imports five freely-licensed
  photos (Milan, Colosseum, Shibuya, Eiffel, Taj Mahal) and two **real** Pexels
  video clips, then runs the full recon on each. `make demos` seeds
  `~/geoweb-photos`; sources and licences are listed in `demos/README.md`.
- **Report export** — one-click **Markdown, HTML, PDF (print)** and **JSON**
  exports, branded with the GeoWeb logo/wordmark and the author link, via
  `GET /api/session/<name>/export?fmt=md|json` plus a client-side branded
  HTML/PDF builder.
- **Session kind badges** — 📷 photo / 🎬 video etiquette pills on session cards
  and an overlay badge on the session view; video sessions now preview their
  contact sheet instead of showing **"photo not found"**.
- **Browser-local report drafts** — the Report tab auto-saves drafts to
  `localStorage` per session and remembers the last opened session.
- **Dark / light theme switcher** — a sun/moon toggle in the console topbar
  (persisted to `localStorage`), with a full light token set.
- **Image zoom & click-to-play video** — click any evidence image or the main
  photo to open a full-screen lightbox (Esc / click-outside to close); video
  sessions show a **▶ play** affordance that opens the real clip in a
  `<video controls autoplay>` player.
- **Video uploads** — the dropzone now accepts video (`image/*,video/*`),
  copy updated to *"Drop a photo or video here"* (MP4 / MOV / WebM).
- **Footer branding** — *GeoWeb* links back to the project and the author name
  links to LinkedIn, readable in both themes.
- **Multi-assistant MCP docs** — copy-paste MCP configs for **opencode, Claude
  Code, Codex, GitHub Copilot CLI, Grok CLI, Cursor, Claude Desktop and
  VS Code / Windsurf** in [`mcp/README.md`](mcp/README.md).
- **Mobile layout fix** — the pinned session photo no longer overlays the
  Overview / Evidence / Tools / Report tabs on narrow screens (`position:
  static` + height cap under 900 px).
- **Non-spoiler demo sessions** — bundled demo sessions are named
  `demo-image-1..5` / `demo-video-1..2` (and their media files are opaque) so
  opening one doesn't reveal the answer.

### 2026-10-11

- Standalone repository `halimbahae/geoweb` created; engine vendored from
  marouane53/GeoINT (MIT, see NOTICE).