# Security Policy

GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems. Report by
opening a private advisory at:

<https://github.com/halimbahae/geoweb/security/advisories>

or by emailing the author via their site (<https://www.linkedin.com/in/halimbahae/>).

You can expect an acknowledgement within **72 hours** and a fix plan within a
week.

## Access control

The console is single-user and local, but it is **not unauthenticated**:

- **Token auth** — every `/api/*` call needs the access token, generated at
  startup (or pinned with `--token` / `$GEOWEB_TOKEN`). The browser gets it in one
  step: open the `…/?token=…` URL printed in the server log, which trades the
  token for an `HttpOnly; SameSite=Strict` cookie and redirects to the clean URL.
  Non-browser clients send the `X-GeoWeb-Token` header instead.
- **Host check (anti DNS-rebinding)** — a server bound to a loopback address only
  answers loopback `Host` headers, so a hostile page that resolves
  `evil.example → 127.0.0.1` cannot reach the API from the victim's browser.
- **Origins** — a non-GET request carrying a foreign `Origin` is refused.
- `/api/health` stays reachable without a token (container healthcheck) and then
  returns `{"ok": true, "authenticated": false}` — no paths, no archive data.

Binding to a non-loopback address (`--host 0.0.0.0`) still removes the Host
check, because there is no name to pin down; keep the token secret there and put
a reverse proxy with TLS + auth in front. See `docs/deployment.md`.

## Scope

In scope:

- Path traversal or file disclosure through the HTTP API
  (`/static/*`, `/api/session/*/files`, `'..'` escapes)
- Authentication or Host/Origin bypass of the access controls above
- Remote code execution via tool/recon subprocess argument injection
- Upload handling (size limits, content sniffing, path safety)

Out of scope:

- The console is meant for single-user local use. Exposing `--host 0.0.0.0` to the
  internet without a reverse proxy in front is a misconfiguration, not a bug.

## Supported versions

| Version | Supported |
| --- | --- |
| `main` | ✅ |

## Thanks

- The vendored engine under `scripts/` is from marouane53/GeoINT (MIT) — report
  engine bugs there too.