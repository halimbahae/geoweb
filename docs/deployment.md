# Deployment

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

GeoWeb is designed to run **on your machine**. The two things you can deploy are
the server (Docker or a systemd unit) and the static landing site (GitHub Pages).

## Docker

```bash
docker compose up --build               # http://127.0.0.1:8787
docker compose build --build-arg BUILD_ML=1   # bake the world-prior models
```

`docker-compose.yml` mounts `./data` as the archive root and publishes `8787`.
The image is `python:3.12-slim` + `ffmpeg` + `uv`; `BUILD_ML=1` additionally runs
the model warm-up so the first full recon is fast.

```bash
docker run --rm -p 8787:8787 -v /host/photos:/geoweb-photos geoweb
# ML edition
docker build --build-arg BUILD_ML=1 -t geoweb-ml . && docker run --rm -p 8787:8787 -v /host/photos:/geoweb-photos geoweb-ml
```

## systemd (bare metal)

```ini
# /etc/systemd/system/geoweb.service
[Unit]
Description=GeoWeb console
After=network.target

[Service]
User=analyst
WorkingDirectory=/opt/geoweb
ExecStart=/usr/bin/python3 web/app.py --host 0.0.0.0 --port 8787 --root /srv/geoweb-photos
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`sudo systemctl enable --now geoweb`. Put it behind a reverse proxy if you expose
it; note the server has **no authentication** — keep it on localhost or a trusted
network.

## Reverse proxy (nginx)

```nginx
location / {
    proxy_pass http://127.0.0.1:8787;
    client_max_body_size 160m;
    proxy_read_timeout 3600s;
}
```

The upload limit must exceed GeoWeb's 150 MB cap, and the long read timeout
covers full recon runs.

## The landing site (GitHub Pages)

`landing/` is a static site with no build step. The workflow
`.github/workflows/pages.yml` publishes it to GitHub Pages on every push to
`main`:

1. Repository → **Settings → Pages → Source: GitHub Actions** (once).
2. Push to `main`; the `pages` workflow deploys `landing/`.
3. Live at <https://halimbahae.github.io/geoweb>.

## MCP

For remote use, run the MCP server over SSE:

```bash
GEOWEB_ROOT=/srv/geoweb-photos uv run mcp/geoweb_mcp.py --transport sse --port 8989
```

and point a client at `http://host:8989/sse`. Prefer stdio for local assistants.
