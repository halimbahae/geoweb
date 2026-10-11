<!-- GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/> -->
# Contributing to GeoWeb

GeoWeb is a friendly, open project. Thanks for helping. Here is the contract we
work under.

## Ground rules

1. **Local-first, private-first.** Everything runs on the user's machine by
   default; the "phone home" default is zero. Changes that flip that need a
   really good reason and a clear opt-out.
2. **Keep the server dependency-free.** `web/app.py` deliberately uses only the
   Python standard library. Pipeline work goes through the `scripts/` and
   `video/` tools via `uv run`; dependencies for those tools are declared as
   PEP-723 headers inside each script.
3. **Respect the licence layer.** `scripts/` is vendored from GeoINT (MIT) —
   change the method in its own repository unless it is a GeoWeb-side fix.
   Model licences (StreetCLIP is CC-BY-NC) are someone else's; do not weaken
   the notices.
4. **Evidence over opinion.** Recon output must be readable by a human who
   disagrees. Keep every claim connected to a file, a photo or a source.

## How to get in touch

- Bug report → [bug template](../../issues/new?template=bug_report.yml)
- Feature idea → [feature template](../../issues/new?template=feature_request.yml)
- Questions → GitHub Discussions (issues are fine too)

## Workflow

1. Fork the repo and branch from `main`: `git checkout -b feat/my-thing`.
2. Make small, readable commits. Messages follow the log style:
   `Video: sample frames with OpenCV`, `Fix: …`, `docs: …`.
3. Run the checks:
   ```bash
   make ci          # lint + tests + py_compile + node --check
   ```
4. Open a PR to `main`. Link the issue it fixes. One PR, one concern.
5. After review, the maintainer merges. Keep the branch updating if it takes
   a while: `git pull upstream main`.

## Running the checks

```bash
uv sync --group dev      # one-time setup
make lint                # ruff
make test                # pytest (video tests self-skip without ffmpeg)
make pycheck             # syntax checks for python + the front-end bundle
```

## What needs a test

- `video/frames.py` logic (scene pick, dedupe, contact sheet).
- The HTTP surface in `web/app.py` (upload, recon, stop, rename/delete).
- Anything that touches filesystem paths or user data.

## Releasing

- Bump `pyproject.toml` version, add a CHANGELOG entry, tag `vX.Y.Z`.
- The landing page deploys automatically to GitHub Pages on `main`.

## Licensing

By contributing you agree your work is licensed under the MIT License of this
project. Attribution is appreciated in the README for significant additions.