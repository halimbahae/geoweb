"""GeoWeb assistant — a chat that answers from a session's own evidence.

Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

The console is chat-first: instead of hunting through tabs, you ask "what phone
number does the venue publish?" or "how sure are we, and why?" and the answer is
built from the files this session already produced — the report, the recon
summary, the Lens capture and the sources dossier.

It runs against a local Ollama server (no API key, nothing leaves the machine).
If the model is not there, the error says exactly what to run; it never silently
falls back to a canned answer, because a confident guess is worse than a gap.

Stdlib only, like `web/app.py` which imports it.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

AUTHOR = "Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>"

HOST = (os.environ.get("GEOWEB_OLLAMA") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("GEOWEB_CHAT_MODEL", "qwen3.5:4b")
PREFERRED = ("qwen3.5:4b", "qwen3.6:latest", "glm-4.7-flash:latest", "llama3.1:8b", "gemma4:e4b")
MAX_HISTORY = 8
MAX_REPORT = 6000
MAX_RECON = 3000

SYSTEM = """You are the GeoWeb assistant, inside a local-first photo geolocation console.

You answer questions about ONE session using the evidence block below: the analyst
report, the recon summary, the Google Lens capture and the sources dossier.

Rules:
- Answer from the evidence. Quote coordinates, confidence and file names exactly.
- If the evidence does not contain the answer, say so plainly and name the step that
  would produce it (Lens, sources dossier, OCR, world prior, a human check).
- Never invent a place, address, phone number, URL, date or score.
- Distinguish what is verified (a source says it) from what a model guessed.
- Be brief: 2 to 6 sentences, plain text, no markdown headings.
"""


class AssistantError(RuntimeError):
    """Raised when the assistant cannot answer (no model, no server, bad reply)."""


# --------------------------------------------------------------------------- #
# ollama
# --------------------------------------------------------------------------- #

def _post(url: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def list_models(host: str = HOST, timeout: int = 4) -> dict:
    """Which local models exist. Never raises: the UI needs a plain status."""
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        return {"available": False, "models": [], "host": host}
    names = [str(m.get("name") or "") for m in (data.get("models") or []) if m.get("name")]
    return {"available": bool(names), "models": names, "host": host,
            "default": pick_model(names)}


def pick_model(models: list[str], wanted: str = "") -> str:
    """The configured model if it is pulled, else the first preferred one present."""
    if wanted and wanted in models:
        return wanted
    for name in PREFERRED:
        if name in models:
            return name
    return models[0] if models else ""


# --------------------------------------------------------------------------- #
# context = what this session actually knows
# --------------------------------------------------------------------------- #

def _json(path: Path, default: dict | None = None) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default or {}


def _text(path: Path, limit: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def build_context(folder: Path) -> dict:
    """Collect the session's own files into one small, quotable context."""
    meta = _json(folder / "session.json")
    dossier = _json(folder / "recon" / "sources" / "dossier.json")
    lens = _json(folder / "recon" / "lens" / "lens.json")

    sources = []
    for s in (dossier.get("sources") or [])[:12]:
        label = s.get("publisher") or s.get("domain") or ""
        sources.append({"kind": s.get("kind"), "title": s.get("title"), "url": s.get("url"), "site": label})

    return {
        "name": folder.name,
        "kind": meta.get("kind") or "photo",
        "status": meta.get("status") or "",
        "result": meta.get("result") or {},
        "truth": meta.get("truth") or {},
        "report": _text(folder / "report.md", MAX_REPORT),
        "recon_summary": _text(folder / "recon" / "recon.md", MAX_RECON),
        "lens": {
            "status": lens.get("status") or "",
            "place": lens.get("place") or "",
            "matches": [{"title": link.get("title"), "url": link.get("url"), "kind": link.get("kind")}
                        for link in (lens.get("links") or [])[:10]],
        },
        "dossier": {
            "address": dossier.get("address") or "",
            "phone": dossier.get("phone") or [],
            "email": dossier.get("email") or [],
            "website": (dossier.get("site") or {}).get("url") or "",
            "sources": sources,
            "images": [img.get("file") for img in (dossier.get("images") or [])],
            "warnings": (dossier.get("warnings") or [])[:6],
        },
    }


def context_text(ctx: dict) -> str:
    """Render the context as the plain text block the model reads."""
    r = ctx.get("result") or {}
    t = ctx.get("truth") or {}
    lines = [f"SESSION: {ctx['name']} ({ctx['kind']}, status {ctx['status'] or 'open'})"]
    if r:
        lines.append("RECORDED ANSWER: " + json.dumps({
            "country": r.get("country"), "region": r.get("region"), "city": r.get("city_or_nearest_locality"),
            "lat": r.get("latitude"), "lon": r.get("longitude"), "confidence": r.get("confidence"),
        }, ensure_ascii=False))
    if t.get("latitude") is not None:
        lines.append(f"VERIFIED TRUTH ON FILE: {t.get('latitude')}, {t.get('longitude')}")
    lens = ctx.get("lens") or {}
    if lens.get("place") or lens.get("matches"):
        lines.append(f"LENS CAPTURE ({lens.get('status') or 'ok'}):")
        if lens.get("place"):
            lines.append("  overview: " + str(lens["place"]))
        for m in lens.get("matches") or []:
            lines.append(f"  - [{m.get('kind')}] {m.get('title')} — {m.get('url')}")
    d = ctx.get("dossier") or {}
    if any([d.get("address"), d.get("phone"), d.get("website"), d.get("sources")]):
        lines.append("SOURCES DOSSIER:")
        if d.get("website"):
            lines.append("  website: " + str(d["website"]))
        if d.get("address"):
            lines.append("  address: " + str(d["address"]))
        if d.get("phone"):
            lines.append("  phone: " + ", ".join(str(p) for p in d["phone"]))
        if d.get("email"):
            lines.append("  email: " + ", ".join(str(e) for e in d["email"]))
        for s in d.get("sources") or []:
            lines.append(f"  - [{s.get('kind')}] {s.get('title')} ({s.get('site')}) {s.get('url')}")
        if d.get("phone") == []:
            lines.append("  phone: none published by the venue (checked site, OSM tags, JSON-LD)")
    if ctx.get("report"):
        lines.append("ANALYST REPORT:\n" + ctx["report"])
    if ctx.get("recon_summary"):
        lines.append("RECON SUMMARY:\n" + ctx["recon_summary"])
    return "\n".join(lines)


def messages(ctx: dict, question: str, history: list[dict] | None = None) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM + "\n\nEVIDENCE\n" + context_text(ctx)}]
    for turn in (history or [])[-MAX_HISTORY:]:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        text = str(turn.get("content") or "").strip()
        if text:
            msgs.append({"role": role, "content": text})
    msgs.append({"role": "user", "content": question.strip()})
    return msgs


# --------------------------------------------------------------------------- #
# ask
# --------------------------------------------------------------------------- #

def ask(folder: Path, question: str, history: list[dict] | None = None,
        model: str = "", host: str = HOST, timeout: int = 180) -> dict:
    """Answer one question about `folder`. Raises AssistantError when it cannot."""
    question = (question or "").strip()
    if not question:
        raise AssistantError("ask a question first")
    if len(question) > 2000:
        raise AssistantError("question is too long (2000 characters max)")

    status = list_models(host)
    if not status["available"]:
        raise AssistantError(
            f"no local model answered at {host} — start Ollama (`ollama serve`) "
            f"and pull a model (`ollama pull {DEFAULT_MODEL}`), or set GEOWEB_CHAT_MODEL")
    chosen = pick_model(status["models"], model or DEFAULT_MODEL)

    ctx = build_context(folder)
    started = time.time()
    try:
        reply = _post(host + "/api/chat", {
            "model": chosen,
            "messages": messages(ctx, question, history),
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192},
        }, timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300] if hasattr(exc, "read") else str(exc)
        raise AssistantError(f"model '{chosen}' refused the request: {detail or exc}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AssistantError(f"lost the model server at {host}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AssistantError("the model server sent something that is not JSON") from exc

    answer = str((reply.get("message") or {}).get("content") or "").strip()
    if not answer:
        raise AssistantError("the model returned an empty answer — try again or use a larger model")
    return {
        "answer": answer,
        "model": chosen,
        "seconds": round(time.time() - started, 1),
        "context": {
            "has_report": bool(ctx["report"]),
            "has_recon": bool(ctx["recon_summary"]),
            "lens": ctx["lens"]["status"] or "absent",
            "sources": len(ctx["dossier"]["sources"]),
            "phone": ctx["dossier"]["phone"],
        },
    }
