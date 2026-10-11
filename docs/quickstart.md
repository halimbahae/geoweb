# Quickstart

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## What you need

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** — the scripts declare their own
  dependencies as PEP-723 headers, so `uv run` fetches them on demand
  (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **ffmpeg** — only for video (`brew install ffmpeg` on macOS).

The web server itself needs **no third-party packages**.

## Run

```bash
git clone https://github.com/halimbahae/geoweb
cd geoweb
python3 web/app.py --open
```

Open <http://127.0.0.1:8787>, drop a photo, pick **Quick** recon, and read the
evidence as it arrives. Your archive lives in `~/geoweb-photos` by default:

```bash
python3 web/app.py --root /mnt/photos --port 8788 --host 0.0.0.0 --open
```

## Video

```bash
curl -sX POST http://127.0.0.1:8787/api/sessions -F photo=@clip.mp4
```

Or just drag a clip into the console — GeoWeb cuts it into a contact sheet of
distinct frames, you pick one, and recon runs as usual. Details:
[video-guide.md](video-guide.md).

## Docker

```bash
docker compose up --build          # then open http://127.0.0.1:8787
# with the ML world-prior models baked in:
docker compose build --build-arg BUILD_ML=1
```

## MCP

```bash
GEOWEB_ROOT=~/geoweb-photos uv run mcp/geoweb_mcp.py
```

Point opencode, Claude Code, Codex, GitHub Copilot CLI, Grok CLI, Cursor or
Claude Desktop at it and ask *"where were my last three photos taken?"*. Copy-paste
configs for each are in [../mcp/README.md](../mcp/README.md).

## Make targets

```bash
make serve     # run the console
make ci        # ruff + pytest + py_compile + node --check
make video     # cut a video into frames
make docker    # build the image
```
