# GeoWeb docs

GeoWeb is a local-first browser console that answers **"where was this taken?"**
for photos *and* videos, with a full evidence trail you can audit.

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

| Guide | What's inside |
| --- | --- |
| [Quickstart](quickstart.md) | install, run, first recon in 2 minutes |
| [Using the console](using-the-console.md) | sessions, the recon board, jobs, finishing |
| [Video guide](video-guide.md) | video → frames → recon on a chosen frame |
| [API reference](api.md) | every HTTP endpoint with curl examples |
| [Architecture](architecture.md) | how the server, engine and archives fit together |
| [Deployment](deployment.md) | Docker, reverse proxy, the GitHub Pages site |
| [Demos](../demos/README.md) | the bundled 5-photo + 2-video archive and how to seed it |
| [MCP server](../mcp/README.md) | drive your archive from an AI assistant |
| [Skill](../skills/geoweb/SKILL.md) | agent guidance for this repo |

## The idea

Most geolocation is either a black box or a pile of scripts. GeoWeb keeps the
analyst in the loop: it runs the pipeline, shows you **why** each candidate was
raised (metadata, OCR, reverse search, detector, camera calibration, world
priors), and lets you make the final call with the evidence in front of you.

Everything runs on your machine and nothing is uploaded anywhere.
