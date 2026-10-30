# Using the console

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## Ask first

The console is chat-first. Open a session that already has an answer and it lands
on the **💬 Assistant** tab: ask "what phone number does the venue publish?",
"how sure are we, and why?", "what did the press say?" and the answer is built
from this session's own files — report, recon summary, Lens capture, sources
dossier — through a local Ollama model. Nothing leaves the machine, and when the
evidence is missing the assistant says so instead of guessing. The other tabs
stay exactly where they were for when you want to read the raw evidence.

## Sessions

A **session** is one uploaded item plus everything derived from it, stored as a
folder under your archive root. The home view lists them newest-first with a
thumbnail, a status pill and — if you recorded ground truth — the error in km.

Each card has quick actions:

- **✎ rename** — give it a human name (`milan-duomo`); text artifacts are rewritten.
- **🗑 delete** — remove the folder and kill any running jobs.

## Running recon

A session is `pending` until you run recon. Two modes:

| Mode | Steps | Cost |
| --- | --- | --- |
| **Quick** | metadata, OCR, reverse search, detection, calibration (no ML priors) | seconds–minutes |
| **Full** | the above + the learned world-prior models (GeoCLIP/StreetCLIP) | minutes, needs the `ml` extra |

The **job bar** shows a live step list. Each finished step gets a one-line digest
(`4000x3000 · GPS 45.46,9.19`, `OCR 7 text item(s) · reverse 2/2 sheets`, …).
You can **stop** a job at any time; nothing is destroyed.

## Reading the evidence

The recon view is built for a gut call, then confirmation:

- **Metadata** — EXIF GPS/time, camera, and a loud warning when it's stripped.
- **Text / signs** — OCR crops; any place names become lookup candidates.
- **Reverse search** — Yandex/Baidu near-duplicate sheets to open first.
- **Detect** — objects and their coordinates in the frame.
- **Calibration** — estimated field of view / 35 mm-equivalent focal length.
- **Prior** — the **interactive map**: OSM tiles or the pipeline's prior
  snapshot, GeoCLIP clusters sized by mass, top points, and a star for the model
  guess. Click a chip to fly there; go **fullscreen** for detail.

## Sources: Lens, contacts, photographs

The **Sources** tab holds two things:

- **Google Lens** — the reverse-image search that actually names a place. The
  automated browser is honest about walls: if Google answers with a CAPTCHA the
  status says `blocked`, and the tab gives you the photo plus a paste box. Upload
  the photo at `lens.google.com` yourself, copy the results page, paste it, and
  the same parser writes the same evidence file.
- **Sources dossier** — the venue's own website (address, phone, e-mail, socials,
  photos), OpenStreetMap tags, and press/directory mentions. Off-topic hits are
  dropped by name relevance; "no phone published" is said plainly rather than
  filled in.

Both run automatically after a recon that ends without an answer: recon → Lens →
dossier. Turn the chain off with `GEOWEB_AUTO_FALLBACK=0`.

## Tools

The **Tools** tab exposes the curated CLI steps directly on the session:
`textgeo` (text → countries/phones/brands/places), `geodata` (GeoNames),
`board` (the reasoning board), `refsheet`, and a raw-argv runner for any
`scripts/*.py`. Output is a job log you can read inline.

## Finishing

When you've decided, fill **country / region / city / coordinates /
confidence** and **finish** the session. Save a short analyst **report**; it is
stored as `report.md` beside the evidence. Optionally record **truth** (the real
coordinates) to score the pipeline's accuracy over time.

## Exporting & local drafts

The **Report** tab has a **Save & export** block:

- **⬇ Markdown** / **⬇ JSON** — download a branded, self-contained report
  (analyst notes + recon summary + metadata) straight from the server.
- **⬇ HTML** / **⬇ PDF** — a standalone, print-ready page carrying the GeoWeb
  logo, the run summary and your report; PDF uses the browser's print dialog
  (choose *Save as PDF*).

Your in-progress notes are also **auto-saved to this browser** (`localStorage`)
per session, so a closed tab or a restart never loses a draft; the console shows
when a draft is local-only versus saved on the server.

## Photo & video sessions

Session cards and the session view carry a **kind badge** — 📷 photo or
🎬 video. Video sessions show their **contact sheet** as the preview and add a
**Frames** tab; pick the informative frame, then run recon exactly as for a
photo.

## Keyboard & habits

- Drag anywhere onto the dropzone, or click to browse.
- Jobs are capped (default 3 concurrent); a busy archive returns `429`.
- Sessions are plain folders — you can `rsync` or back them up wholesale.
