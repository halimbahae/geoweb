## What

Short description of the change.

## Why

Motivation and (if relevant) links to the issue.

## How to test

```bash
make ci
# manual smoke if UI changed:
python3 web/app.py --open
```

## Checklist

- [ ] `make ci` passes (ruff + pytest + py_compile + node --check)
- [ ] No third-party imports added to `web/app.py`
- [ ] Author header retained/added on changed source files
- [ ] User media / test archives not committed

GeoWeb — Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>