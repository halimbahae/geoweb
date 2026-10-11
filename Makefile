# GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
.PHONY: dev serve video test ci lint docker docs demos

# Run the console without installing anything (uses `uv` at runtime only).
serve:
	python3 web/app.py --open

dev:
	uv run --group dev python3 web/app.py --open

# Cut a video into frames locally:
#   make frames ARGS=demo.mp4
video:
	uv run video/frames.py $(ARGS)

test:
	uv run pytest

# The CI job, stripped down: what every contributor must pass.
ci: lint test pycheck
	@echo "ci ok"

lint:
	uvx ruff check .

pycheck:
	python3 -m compileall -q web video tests mcp
	node --check web/static/app.js
	node --check landing/assets/js/landing.js

docker:
	docker build -t geoweb .

# Seed the bundled demo archive (3 photos + 2 videos) and run the full recon on each.
#   make demos            → full recon (~/geoweb-photos)
#   make demos ARGS="--recon quick"
demos:
	uv run demos/seed.py $(ARGS)

docs:
	@echo "docs are in ./docs — see https://halimbahae.github.io/geoweb"