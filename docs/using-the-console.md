# Using the console

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

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
