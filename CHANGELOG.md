# Changelog

All notable changes to GeoWeb are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow
[SemVer](https://semver.org/).

GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## [Unreleased]

### Security

- **Access control on the console server** (`web/app.py`) — the HTTP server no
  longer serves `/api/*` to anyone who can reach the port. It now:
  - requires a random per-run **token** (`--token` / `$GEOWEB_TOKEN` to pin it)
    on every `/api/*` call, sent as the `X-GeoWeb-Token` header or held as the
    `geoweb_token` `HttpOnly; SameSite=Strict` cookie a browser gets from the
    `/?token=…` URL the server prints at startup;
  - refuses **cross-origin** writes (`Origin` check) so a visited page can't
    drive your archive;
  - rejects **non-loopback `Host` headers** when bound to loopback, defeating
    DNS-rebinding;
  - keeps `/api/health` public for the Docker healthcheck but answers it with
    `{"ok": true, "authenticated": false}` when unauthenticated (no machine paths
    leaked). The console UI shows a **token required** state until signed in.

### Added

- **Google Lens fallback** (`sources/lens.py`) — the step that actually names a
  place. Drives Lens in Chromium through Playwright (`make lens-install`), captures
  the overview sentence, the exact/visual match links and a screenshot, and records
  a CAPTCHA wall as `blocked` instead of pretending. A second mode imports a capture
  taken by hand (`--from-text`), so a human-bypassed wall still yields real evidence.
  Endpoint: `POST /api/session/<name>/lens` (job, or `{text, url}` to import).
- **Sources dossier** (`sources/dossier.py`) — given the identified place, gathers
  what a human would open by hand: the venue site (address, `tel:` numbers, e-mails,
  socials, downloadable photographs), OSM/Nominatim extratags, and press mentions via
  Google News RSS + web results (off-topic hits are dropped by name relevance). Written
  to `recon/sources/dossier.json` + `recon/sources/img/*`. Endpoint:
  `POST /api/session/<name>/dossier`.
- **Sources tab** — renders the Lens capture (overview, exact vs visual matches) and
  the dossier (website, address, phone, e-mail, socials, press/directory links, venue
  photo grid) with one-click "Run Google Lens" / "Run Sources dossier".
- **Assistant tab (chat-first console)** (`assistant/chat.py`) — ask questions about a
  session in plain language; answers are built only from that session's report, recon
  summary, Lens capture and dossier, through a **local Ollama** model (no key, nothing
  leaves the machine; `GEOWEB_CHAT_MODEL` / `GEOWEB_OLLAMA` to configure). Says what is
  missing instead of guessing. Endpoints: `GET /api/assistant`, `POST
  /api/session/<name>/chat`.
- **Source classification helpers** (`sources/classify.py`) and 25 unit tests
  (`tests/test_sources.py`) covering phone/email extraction, relevance filtering,
  engine-title cleanup, Lens section + venue parsing and the assistant's evidence block.
- **The automatic chain** — a recon that ends without an answer now runs Lens by
  itself, and a successful capture is followed by the sources dossier, named from
  the Lens entity line (`venue_name`). A walled/unavailable Lens stops the chain and
  the Sources tab switches to the paste-in import. `GEOWEB_AUTO_FALLBACK=0` opts out.
- **Paste-in Lens import in the UI** — when Google walls the automated browser, the
  Sources tab offers the photo, a link to `lens.google.com` and a textarea; the pasted
  page is parsed into the same `lens.json` and the dossier then runs automatically.
- **Toolbar shortcuts** — `📸 Lens` and `🔗 Sources` next to the recon buttons.
- **MCP tools** — `lens`, `import_lens`, `sources` and `ask` (plus `lens`/`dossier` in
  the `session` payload), so agents get the same fallback, dossier and chat.
- **Docs** — `docs/api.md` covers the new endpoints and the automatic chain;
  `docs/using-the-console.md` gains "Ask first" and "Sources" sections.

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
- **Landing page: glassmorphism + quickstart** — frosted-glass cards and code
  blocks, a no-flash dark/light theme toggle (persisted), a **Copy** button on
  every code block, and an MCP quickstart with per-agent copy-paste configs
  (**ChatGPT, Claude, opencode, Cursor, Codex, GitHub Copilot CLI, Grok CLI**).
  `mcp/README.md` gains a remote-SSE section for ChatGPT Connectors / Claude web.
- **Dev dependency group** — `pytest`/`ruff` moved to a `[dependency-groups] dev`
  table so `uv run`, `uv sync --group dev` and CI resolve them consistently.

### Changed

- **Chat-first console** — the Assistant tab sits second and a session that already
  has a recorded answer opens on it; the active tab now survives session refreshes.
- **Lens quality gates** — the capture waits for the result sections (not for "some
  link"), filters Google's own chrome (`is_engine`), reports `empty`/`blocked`/
  `unavailable` honestly, and a missing Playwright browser is a message, not a crash.

### Fixed

- **Concluded sessions no longer advertise void model guesses** — once a session
  has a recorded answer, the *World prior* block says **✔ Superseded** with the
  identified place, coordinates and Maps link, fades the country percentages, labels
  the ★ point guess **void**, and the prior map opens centred on the answer with the
  GeoCLIP layers available in the layer control but not drawn. Previously an
  uninformative prior (flat distribution, e.g. 9% top country) still presented its
  CZ/NL/RO clusters and a ★ point guess as if they were candidates.


### 2026-10-11

- Standalone repository `halimbahae/geoweb` created; engine vendored from
  marouane53/GeoINT (MIT, see NOTICE).