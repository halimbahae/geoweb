# GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
# syntax=docker/dockerfile:1
# GeoWeb — local-first photo & video geolocation console.
#
#   docker build -t geoweb .
#   docker compose up
#   → http://127.0.0.1:8787
#
# The ML extras (torch, StreetCLIP, GeoCLIP) are baked in when you build with
#   docker build --build-arg BUILD_ML=1 -t geoweb .
# otherwise full recon downloads them into the volume on first use, same as
# running on a bare machine.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_CACHE=1

# uv for the PEP-723 script runner the engine relies on, + ffmpeg for OpenCV.
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
COPY --link pyproject.toml ./
RUN uv pip install --system "numpy>=1.26" "pillow>=10" ruff pytest

COPY --link web/ ./web/
COPY --link scripts/ ./scripts/
COPY --link video/ ./video/

ARG BUILD_ML=0
RUN if [ "$BUILD_ML" = "1" ]; then \
      uv pip install --system "torch" "torchvision" "transformers" "geoclip" "safetensors" "opencv-python-headless>=4.8,<5"; \
    else \
      uv pip install --system "opencv-python-headless>=4.8,<5"; \
    fi

# GeoWeb never needs the git helpers; keep the engine's local caches here.
ENV GEO_PHOTOS=/geoweb-photos
VOLUME ["/geoweb-photos"]

EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD curl -fs http://127.0.0.1:8787/api/health || exit 1

ENTRYPOINT ["python3", "web/app.py", "--host", "0.0.0.0", "--root", "/geoweb-photos"]