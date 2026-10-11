# Security Policy

GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems. Report by
opening a private advisory at:

<https://github.com/halimbahae/geoweb/security/advisories>

or by emailing the author via their site (<https://www.linkedin.com/in/halimbahae/>).

You can expect an acknowledgement within **72 hours** and a fix plan within a
week.

## Scope

In scope:

- Path traversal or file disclosure through the HTTP API
  (`/static/*`, `/api/session/*/files`, `'..'` escapes)
- Remote code execution via tool/recon subprocess argument injection
- Upload handling (size limits, content sniffing, path safety)

Out of scope:

- The console has **no authentication** by design: it binds to `127.0.0.1` and
  is meant for single-user local use. Do not expose it to the internet without
  putting a reverse proxy + auth in front. See `docs/deployment.md`.

## Supported versions

| Version | Supported |
| --- | --- |
| `main` | ✅ |

## Thanks

- The vendored engine under `scripts/` is from marouane53/GeoINT (MIT) — report
  engine bugs there too.