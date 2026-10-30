# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.44"]
# ///
"""GeoWeb Lens — the visual-search fallback, run when the local models come up empty.

Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

The recon pipeline's world-prior models are a hint, not an answer: on an
anonymous interior they hand back a country with 9% confidence and a point
guess in the wrong country. A reverse image search is the step that actually
names the place, and it is the step this tool automates.

Two modes, because one of them cannot be automated honestly:

  browser  Drive Google Lens in Chromium through Playwright: upload the photo,
           wait for the results, capture the page text, the result links and a
           screenshot. Google may answer with a CAPTCHA wall; that is recorded
           as `blocked` rather than retried with tricks.

  import   Parse the results a human captured — the "Search with Google Lens"
           page text saved to a file, or a URL list. This is the honest path
           when the wall appears: the evidence is still real, it is only
           gathered by hand.

Both write `<session>/recon/lens/lens.json`, which the console's Sources tab
renders next to the venue dossier.

Usage:
    uv run sources/lens.py photo.jpg --out-dir recon/lens            # browser
    uv run sources/lens.py photo.jpg --out-dir recon/lens --headed   # solve the wall by hand
    python3 sources/lens.py --from-text lens.txt --out-dir recon/lens # import

Requires Playwright for the browser mode only (`make lens-install`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

try:  # imported as a package (tests) …
    from .classify import AUTHOR, host_of, is_engine, kind_of, norm
except ImportError:  # … or run as a script: python3 sources/lens.py
    from classify import AUTHOR, host_of, is_engine, kind_of, norm

# Google Lens ships every UI language; the headings below are matched in the
# ones the tool is likely to meet, so the parser does not depend on a locale.
EXACT_HEADINGS = ("correspondances exactes", "exact matches", "exakte übereinstimmungen",
                  "coincidencias exactas", "corrispondenze esatte", "exacte overeenkomsten")
VISUAL_HEADINGS = ("résultats visuels", "visual matches", "visuelle treffer", "coincidencias visuales",
                   "risultati visivi", "visuele overeenkomsten", "similar images", "images similaires")
WALL_MARKERS = ("unusual traffic", "not a robot", "recaptcha", "trafic inhabituel", "not your typical")

# Lines that only exist as page chrome; they are not evidence of anything.
CHROME_LINES = {
    "google", "lens", "images", "all", "shopping", "news", "videos", "tools", "search",
    "connexion", "sign in", "paramètres", "settings", "confidentialité", "privacy",
    "à propos", "about", "aide", "help", "envoyer des commentaires", "feedback",
}


# --------------------------------------------------------------------------- #
# text parsing (shared by both modes, and the only part with unit tests)
# --------------------------------------------------------------------------- #

def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def urls_in(text: str) -> list[str]:
    """Every http(s) URL in a text, de-duplicated, without trailing punctuation."""
    found = re.findall(r"https?://[^\s\"'<>()\[\]]+", text or "")
    out: list[str] = []
    for u in found:
        u = u.rstrip(".,;:!?…»\"'")
        if u not in out:
            out.append(u)
    return out


def place_sentence(lines: list[str]) -> str:
    """The sentence where Lens names what the photo shows, if it wrote one.

    Lens' overview reads like "L'image montre l'intérieur de la salle de cinéma
    Le Colisée située à Marrakech, au Maroc." — that single line is the whole
    answer, and it is worth more than every result thumbnail.
    """
    pattern = re.compile(
        r"\b(l['’]image|la photo|cette image|the image|this image|the photo|this photo|das bild|"
        r"la imagen|esta imagen|l['’]immagine)\b.{0,80}?\b(montre|pr[ée]sente|repr[ée]sente|shows?|"
        r"depicts?|is|zeigt|muestra|mostra)\b", re.I)
    for line in lines:
        if pattern.search(line) and len(line) > 25:
            return norm(line)
    return ""


def parse_text(text: str) -> dict:
    """Turn a captured Lens page (text or imported paste) into structured results.

    Returns `{"place", "summary", "links": [{title, url, domain, kind}]}`.
    Links are attributed to the "exact" section when the exact-match heading
    appears before the visual heading, which is how Lens orders a real hit.
    """
    raw_lines = [norm(ln) for ln in (text or "").splitlines()]
    lines = [ln for ln in raw_lines if ln]
    folded = [_fold(ln) for ln in lines]

    def first_index(words: tuple[str, ...]) -> int:
        folded_words = [_fold(w) for w in words]
        for i, ln in enumerate(folded):
            if any(w in ln for w in folded_words):
                return i
        return -1

    exact_at = first_index(EXACT_HEADINGS)
    visual_at = first_index(VISUAL_HEADINGS)

    links: list[dict] = []
    seen: set[str] = set()
    for i, line in enumerate(lines):
        for url in urls_in(line):
            domain = host_of(url)
            if not domain or is_engine(domain):
                continue
            key = domain + urllib.parse.urlparse(url).path.rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            # A Lens result is a domain line followed by its page title; take
            # the next non-URL, non-chrome line as the title, else the domain.
            title = ""
            for nxt in lines[i + 1:i + 3]:
                if urls_in(nxt) or _fold(nxt) in CHROME_LINES or len(nxt) < 6:
                    continue
                title = nxt
                break
            section = "other"
            if exact_at >= 0 and visual_at >= 0:
                section = "exact" if exact_at <= i < visual_at else "visual"
            elif exact_at >= 0 and i >= exact_at:
                section = "exact"
            links.append({"title": title or domain, "url": url, "domain": domain,
                          "kind": kind_of(url), "section": section})

    # URL-less lines that look like place names ("Le Colisée, Marrakech") are
    # kept as hints: Lens often prints the entity above the result list.
    headings = [_fold(w) for w in EXACT_HEADINGS + VISUAL_HEADINGS]
    hints = [ln for ln in lines
             if not urls_in(ln) and _fold(ln) not in CHROME_LINES
             and not any(h in _fold(ln) for h in headings)
             and 8 < len(ln) < 90 and len(ln.split()) >= 2]

    return {
        "place": place_sentence(lines),
        "summary": lines[:40],
        "hints": hints[:8],
        "links": links,
    }


def classify_sections(links: list[dict]) -> dict:
    """Split parsed links into 'exact matches' and 'visual matches' buckets."""
    return {
        "exact": [ln for ln in links if ln.get("section") == "exact"],
        "visual": [ln for ln in links if ln.get("section") == "visual"],
        "other": [ln for ln in links if ln.get("section") == "other"],
    }


# Words that say what kind of place it is, used to prefer the entity line
# ("Le Colisée, cinéma à Marrakech") over unrelated page chrome.
TYPE_WORDS = ("cinema", "cinéma", "theatre", "théâtre", "musee", "musée", "hotel", "hôtel",
              "restaurant", "cafe", "café", "salle", "palais", "marche", "marché", "gare",
              "stade", "stadium", "eglise", "église", "mosquee", "mosquée", "universite",
              "university", "school", "ecole", "école", "centre", "mall", "museum")


def venue_name(parsed: dict) -> str:
    """The name of the place itself, for the sources dossier to search.

    Lens prints the entity in the overview sentence and above its results
    ("Le Colisée, cinéma à Marrakech | SAM.ma"). The dossier needs a name, not a
    paragraph, so take the head of the most name-like line and drop site suffixes.
    """
    place = parsed.get("place") or ""
    best = ""
    best_score = float("-inf")
    for line in list(parsed.get("hints") or []) + ([place] if place else []):
        text = re.split(r"\s*(?:\||•|—|–)\s*", line)[0]
        head = text.split(",")[0].strip(" .:;-'\"«»")
        words = head.split()
        if not (2 <= len(head) <= 48 and 1 <= len(words) <= 5):
            continue
        if not re.search(r"[A-ZÀ-Ý]", head):
            continue
        folded = _fold(line)
        score = 2 * sum(1 for w in TYPE_WORDS if w in folded)
        score += 1 if head and head in place else 0
        score -= len(words) / 10
        if score > best_score:
            best_score, best = score, head
    return best if best_score > 0 else ""


def place_context(parsed: dict) -> dict:
    """City/country of the place, read off the overview sentence.

    "…Le Colisée situé à Marrakech, au Maroc." → {city: Marrakech, country: Maroc}.
    A venue name on its own is ambiguous (there is a Le Colisée in Chalon-sur-Saône
    too); the sentence usually says where, and the dossier needs that to avoid
    researching the wrong building.
    """
    place = parsed.get("place") or ""
    m = re.search(r"\b(?:situ[ée]e?s?\s+à|located\s+in|se\s+trouve\s+à|in)\s+(.+)$", place, re.I)
    tail = m.group(1) if m else ""
    parts = [part.strip(" .;") for part in tail.split(",") if part.strip(" .;")]
    city = parts[0] if parts else ""
    country = ""
    if len(parts) > 1:
        country = re.sub(r"^(au|aux|en|à|in|the)\s+", "", parts[1], flags=re.I).strip()
    return {"city": city[:60], "country": country[:60]}


# --------------------------------------------------------------------------- #
# browser mode
# --------------------------------------------------------------------------- #

def run_browser(image: Path, out_dir: Path, headed: bool, profile: str, timeout: int = 60) -> dict:
    """Drive Google Lens with Playwright and capture what the page says."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "status": "unavailable",
            "error": "playwright is not installed — run `make lens-install` "
                     "(or `uv run --with playwright sources/lens.py ...`)",
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    browser = None
    try:
        with sync_playwright() as pw:
            ctx_kwargs: dict = {"locale": "fr-FR",
                                "viewport": {"width": 1280, "height": 900},
                                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
            if profile:
                ctx = pw.chromium.launch_persistent_context(profile, headless=not headed, **ctx_kwargs)
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
            else:
                browser = pw.chromium.launch(headless=not headed)
                ctx = browser.new_context(**ctx_kwargs)
                page = ctx.new_page()
            try:
                page.goto("https://lens.google.com/", wait_until="domcontentloaded", timeout=timeout * 1000)
                box = page.locator('input[type="file"]').first
                box.set_input_files(str(image), timeout=timeout * 1000)
                page.wait_for_timeout(2500)
                # Lens first shows the upload form, then streams results. Waiting
                # for the result sections — not for "some link" — is what keeps a
                # half-loaded page from being recorded as evidence.
                deadline = time.time() + timeout
                text = ""
                while time.time() < deadline:
                    if "sorry/index" in page.url:
                        break
                    text = page.inner_text("body")
                    folded_text = _fold(text)
                    if any(_fold(h) in folded_text for h in EXACT_HEADINGS + VISUAL_HEADINGS):
                        break
                    page.wait_for_timeout(1500)
                text = page.inner_text("body")
                links = page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => ({href: e.href, text: (e.innerText || '').trim()}))")
                screenshot = out_dir / "lens.png"
                try:
                    page.screenshot(path=str(screenshot), full_page=False)
                except Exception:  # noqa: BLE001 — a screenshot is a bonus, not the result
                    screenshot = None
                final_url = page.url
            finally:
                ctx.close()
    except Exception as exc:  # noqa: BLE001 — a missing browser is a normal, reportable state
        msg = str(exc).strip().splitlines()[0] if str(exc).strip() else "playwright could not start"
        hint = ""
        if "executable doesn't exist" in msg.lower() or "playwright install" in str(exc).lower():
            hint = " — run `make lens-install` to download Chromium for this Playwright version"
        return {"status": "unavailable", "error": msg + hint, "image": str(image),
                "seconds": round(time.time() - started, 1)}
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass

    parsed = parse_text(text)
    blocked = "sorry/index" in final_url or any(m in _fold(text) for m in WALL_MARKERS)
    # The DOM gives cleaner titles than the text stream; merge both.
    for link in links:
        url = link.get("href") or ""
        if not url.startswith("http"):
            continue
        domain = host_of(url)
        if not domain or is_engine(domain):
            continue
        if any(x["url"] == url for x in parsed["links"]):
            continue
        parsed["links"].append({"title": norm(link.get("text") or "") or domain, "url": url,
                                "domain": domain, "kind": kind_of(url), "section": "other"})
    sections = classify_sections(parsed["links"])
    useful = bool(parsed["place"] or sections["exact"] or sections["visual"])
    if blocked:
        status, error = "blocked", "Google answered with a CAPTCHA wall — retry with --headed, or import the page by hand"
    elif useful:
        status, error = "ok", ""
    else:
        status = "empty"
        error = "Lens returned no result sections — retry with --headed, or import the page by hand"
    return {
        "status": status,
        "url": final_url,
        "image": str(image),
        "seconds": round(time.time() - started, 1),
        "screenshot": str(screenshot.name) if screenshot else "",
        "text_excerpt": text[:4000],
        "error": error,
        **parsed,
    }


# --------------------------------------------------------------------------- #
# import mode
# --------------------------------------------------------------------------- #

def run_import(text_file: Path, image: str, source_url: str) -> dict:
    text = text_file.read_text(encoding="utf-8", errors="replace")
    parsed = parse_text(text)
    return {
        "status": "imported" if parsed["links"] or parsed["place"] else "empty",
        "url": source_url,
        "image": image,
        "imported_from": text_file.name,
        **parsed,
    }


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Reverse-image search fallback for a GeoWeb session.")
    ap.add_argument("image", nargs="?", help="photo (or video frame) to search")
    ap.add_argument("--from-text", help="import a captured Lens page instead of driving the browser")
    ap.add_argument("--source-url", default="", help="where the imported text came from")
    ap.add_argument("--out-dir", default="recon/lens")
    ap.add_argument("--headed", action="store_true", help="show the browser (solve a CAPTCHA by hand)")
    ap.add_argument("--profile", default="", help="persistent Chromium profile directory")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    if args.from_text:
        result = run_import(Path(args.from_text), args.image or "", args.source_url)
        if args.image:
            result["image"] = str(Path(args.image).resolve())
    else:
        if not args.image:
            ap.error("give a photo, or --from-text to import captured results")
        image = Path(args.image)
        if not image.is_file():
            ap.error(f"no such image: {image}")
        result = run_browser(image.resolve(), out_dir, args.headed, args.profile, args.timeout)

    result["tool"] = "lens.py"
    result["author"] = AUTHOR
    result["engine"] = "google-lens"
    result["mode"] = "import" if args.from_text else "browser"
    result["captured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lens.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "lens": str(out_dir / "lens.json"),
        "status": result["status"],
        "place": result.get("place", ""),
        "links": len(result.get("links", [])),
        "error": result.get("error", ""),
    }, ensure_ascii=False))
    return 0 if result["status"] in ("ok", "imported") else 2


if __name__ == "__main__":
    sys.exit(main())
