"""GeoWeb dossier — sources, contacts and photographs for an identified place.

Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

Runs after (or instead of) the visual models: given a place name and/or the
answer of a session, it gathers the material a human would open by hand —

  * the venue's own website: address, phone numbers, e-mail, socials, photos;
  * OpenStreetMap / Nominatim tags for the same place (phone, website, wikidata);
  * press and social mentions found by a plain HTML search (DuckDuckGo, Bing);
  * a handful of reference photographs downloaded next to the dossier.

Everything is written to `<session>/recon/sources/dossier.json` plus
`<session>/recon/sources/img/*`, which the console's Sources tab renders.

Stdlib only, deliberately: `web/app.py` must stay dependency-free, and this
runs as the same kind of subprocess job as the recon pipeline. Network access
is best-effort — every failure is recorded under `warnings` instead of raised,
because a half-filled dossier is still useful evidence.

Usage:
    python3 sources/dossier.py --name "Cinéma Le Colisée" --city Marrakech \
        --country MA --lat 31.635786 --lon -8.015242 --out-dir recon/sources
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

try:  # imported as a package (tests) …
    from .classify import AUTHOR, IMAGE_EXT, SKIP_HOSTS, SOCIAL_HOSTS, absolute, host_of, kind_of, norm
except ImportError:  # … or run as a script: python3 sources/dossier.py
    from classify import AUTHOR, IMAGE_EXT, SKIP_HOSTS, SOCIAL_HOSTS, absolute, host_of, kind_of, norm

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
TIMEOUT = 15
MAX_BYTES = 4_000_000

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


# --------------------------------------------------------------------------- #
# text / html helpers
# --------------------------------------------------------------------------- #

class _Links(HTMLParser):
    """Collect (href, text) pairs and <img src> plus JSON-LD script bodies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.images: list[str] = []
        self.scripts: list[str] = []
        self.text_parts: list[str] = []
        self._href: str | None = None
        self._buf: list[str] = []
        self._in_script = False
        self._in_ld = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in ("style", "noscript"):
            self._skip_depth += 1
        elif tag == "script":
            self._in_script = True
            self._in_ld = "ld+json" in (a.get("type") or "").lower()
            self._buf = []
        elif tag == "a":
            self._href = a.get("href")
            self._buf = []
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or a.get("data-lazy-src")
            srcset = a.get("srcset") or a.get("data-srcset") or ""
            if src:
                self.images.append(src)
            if srcset:
                for part in srcset.split(","):
                    cand = part.strip().split(" ")[0]
                    if cand:
                        self.images.append(cand)
        elif tag == "meta":
            if (a.get("property") or a.get("name") or "").lower() in ("og:image", "twitter:image"):
                self.images.append(a.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "noscript") and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "script":
            if self._in_ld and self._buf:
                self.scripts.append("".join(self._buf))
            self._in_script = False
            self._in_ld = False
            self._buf = []
        elif tag == "a" and self._href is not None:
            text = " ".join("".join(self._buf).split())
            if text or self._href:
                self.links.append((self._href, text))
            self._href = None
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            if self._in_ld:
                self._buf.append(data)
            return
        if self._skip_depth:
            return
        if self._href is not None:
            self._buf.append(data)
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        return "\n".join(line.strip() for line in "".join(self.text_parts).splitlines() if line.strip())


GENERIC_WORDS = {
    "cinema", "cinéma", "theatre", "théâtre", "theater", "salle", "club", "hotel", "hôtel",
    "cafe", "café", "restaurant", "museum", "musée", "centre", "maison", "palais", "marrakech",
}


def name_tokens(name: str) -> list[str]:
    """Distinctive words of a place name, accent-folded so search matches both spellings."""
    folded = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", folded.lower())
    return [w for w in words if len(w) > 3 and w not in GENERIC_WORDS]


def relevant(title: str, url: str, tokens: list[str]) -> bool:
    """Keep a result only when the place's own name appears in it.

    Search engines happily answer "cinema Marrakech" with every other cinema in
    the country; those results are noise in a dossier about one venue.
    """
    if not tokens:
        return True
    hay = (title or "") + " " + urllib.parse.unquote(url or "")
    hay = unicodedata.normalize("NFKD", hay).encode("ascii", "ignore").decode().lower()
    return any(t in hay for t in tokens)


def find_phones(text: str) -> list[str]:
    """Phone numbers a human could dial, from visible text or contact metadata.

    Rejects the two things that dominate raw page text: CSS/JSON integers and
    years. A number qualifies if it carries a country prefix (+NN / 00NN) or a
    separator, which is what separates "05 22 27 16 07" from "1342177279".
    """
    out: list[str] = []
    for raw in re.findall(r"(?:\+|00)?\d[\d\s().\-]{7,}\d", text or ""):
        shown = norm(raw).strip(" .-")
        digits = re.sub(r"\D", "", shown)
        if not 9 <= len(digits) <= 15:
            continue
        has_prefix = shown.startswith(("+", "00"))
        has_sep = bool(re.search(r"[\s().\-]", shown))
        if not (has_prefix or has_sep):
            continue
        if re.fullmatch(r"(19|20)\d{2}[\s.\-/]?(19|20)?\d{0,2}", shown):
            continue  # a year or a date, not a number
        if not has_prefix and len(digits) > 10 and len(re.findall(r"\d+", shown)) == 1:
            continue  # one long digit run: an id, not a phone
        if shown not in out:
            out.append(shown)
    return out[:8]


def find_emails(text: str) -> list[str]:
    found = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text or "")
    seen: list[str] = []
    for e in found:
        e = e.strip(".")
        if e.lower() not in [s.lower() for s in seen] and not e.lower().endswith((".png", ".jpg")):
            seen.append(e)
    return seen[:6]


def looks_like_address(line: str) -> bool:
    if len(line) > 120 or len(line) < 8:
        return False
    return bool(re.search(r"\b(bd|boulevard|avenue|av\.|rue|street|route|place|quartier|gueliz|guéliz|n°|no\.?)\b",
                          line, re.I)) and bool(re.search(r"\d", line))


def jsonld_objects(scripts: list[str]) -> list[dict]:
    objs: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "@graph" in node:
                walk(node["@graph"])
            if any(k in node for k in ("telephone", "address", "sameAs", "image", "url")):
                objs.append(node)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for raw in scripts:
        try:
            walk(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            continue
    return objs


def address_from_jsonld(objs: list[dict]) -> str:
    for o in objs:
        addr = o.get("address")
        if isinstance(addr, dict):
            parts = [addr.get("streetAddress"), addr.get("addressLocality"), addr.get("postalCode"),
                     addr.get("addressCountry")]
            line = ", ".join(norm(p) for p in parts if isinstance(p, str) and p.strip())
            if line:
                return line
        elif isinstance(addr, str) and addr.strip():
            return norm(addr)
    return ""


# --------------------------------------------------------------------------- #
# network
# --------------------------------------------------------------------------- #

def fetch(url: str, *, timeout: int = TIMEOUT) -> tuple[str, bytes]:
    """GET with a browser UA; returns (final_url, body). Raises on hard failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(MAX_BYTES)
        ctype = r.headers.get("Content-Type", "")
        if "image/" not in ctype and len(body) > 400_000:
            body = body[:400_000]
        return r.geturl(), body


def fetch_text(url: str) -> tuple[str, str]:
    final, body = fetch(url)
    return final, body.decode("utf-8", errors="replace")


def _decode_engine_url(url: str) -> str:
    """Unwrap the redirect links search engines hand out (Bing ck/a, DDG l/?uddg)."""
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if parsed.hostname and "bing.com" in parsed.hostname and "u" in qs:
        raw = qs["u"][0]
        if raw.startswith("a1"):
            raw = raw[2:]
        try:
            return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
        except (ValueError, TypeError):
            return url
    if "uddg" in qs:
        return qs["uddg"][0]
    return url


def _tag(xml: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", xml, re.S | re.I)
    return norm(m.group(1)) if m else ""


def clean_title(title: str) -> str:
    """Turn engine chrome into a readable title.

    Bing's HTML anchors glue the domain and the breadcrumb onto the title
    ("culturama.mahttps://culturama.ma › agenda › cinema"), so both are cut off.
    """
    t = norm(title)
    m = re.match(r"^([a-z0-9.\-]+\.[a-z]{2,})(?:https?://\S*)?(?:\s*\u203a.*)?$", t, re.I)
    if m:
        t = m.group(1)
    if "\u203a" in t:
        t = t.split("\u203a")[0]
    t = re.sub(r"^https?://\S+\s*", "", t)
    return t.strip(" -\u2013|\u2026.")


def _rss_items(xml: str, limit: int = 20) -> list[dict]:
    items: list[dict] = []
    for raw in re.findall(r"<item>(.*?)</item>", xml, re.S):
        link = _tag(raw, "link")
        if not link:
            continue
        publisher = re.search(r'<source url="([^"]+)"[^>]*>(.*?)</source>', raw, re.S)
        items.append({
            "title": clean_title(_tag(raw, "title")),
            "url": link,
            "publisher": norm(re.sub(r"<[^>]+>", "", publisher.group(2))) if publisher else "",
            "publisher_url": publisher.group(1) if publisher else "",
            "date": _tag(raw, "pubDate"),
        })
    return items[:limit]


def wikipedia_search(query: str, limit: int = 5) -> list[dict]:
    """Encyclopedic fallback: Wikipedia search API, French then English."""
    hits: list[dict] = []
    for lang in ("fr", "en"):
        url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit={limit}"
               f"&srsearch=" + urllib.parse.quote(query))
        try:
            _, page = fetch_text(url)
            data = json.loads(page)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            continue
        for item in (data.get("query", {}).get("search") or [])[:limit]:
            title = str(item.get("title") or "").strip()
            if title:
                hits.append({"title": title, "url": f"https://{lang}.wikipedia.org/wiki/"
                             + urllib.parse.quote(title.replace(" ", "_")), "via": "wikipedia"})
    return hits


def search_news(query: str, country: str = "", limit: int = 10) -> tuple[list[dict], list[str]]:
    """Press mentions through Google News' RSS feed — plain XML, no key, no wall."""
    lang = "fr" if (country or "").upper() in {"MA", "FR", "TN", "DZ", "BE", "SN", "CA"} else "en"
    cc = (country or ("FR" if lang == "fr" else "US")).upper()
    url = (f"https://news.google.com/rss/search?hl={lang}&gl={cc}&ceid={cc}:{lang}&q="
           + urllib.parse.quote(query))
    try:
        _, body = fetch(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return [], [f"news: {exc}"]
    items = _rss_items(body.decode("utf-8", "replace"), limit)
    for it in items:
        it["via"] = "news"
        it["domain"] = host_of(it.get("publisher_url") or it["url"])
    if not items:
        return [], ["news: no mention found"]
    return items, []


def search_web(query: str, limit: int = 12) -> tuple[list[dict], list[str]]:
    """General web results.

    Bing answers `format=rss` with clean titles and real links; its HTML result
    page is only a fallback because it glues the domain onto the anchor text.
    DuckDuckGo is tried last: it answers automation with a wall more often than
    not, and a wall is reported, not hidden.
    """
    warnings: list[str] = []
    hits: list[dict] = []
    rss = "https://www.bing.com/search?format=rss&count=20&q=" + urllib.parse.quote(query)
    try:
        _, body = fetch(rss)
        for it in _rss_items(body.decode("utf-8", "replace"), limit):
            it["via"] = "bing"
            it["domain"] = host_of(it["url"])
            hits.append(it)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        warnings.append(f"bing: {exc}")

    if not hits:
        html_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        try:
            _, page = fetch_text(html_url)
            parser = _Links()
            parser.feed(page)
            for href in parser.links:
                u = _decode_engine_url(absolute(html_url, href[0]))
                h = host_of(u)
                if not u.startswith("http") or not h or h in SKIP_HOSTS:
                    continue
                if any(x in u for x in ("/search?", "?q=", "/aclk", "/url?q=")):
                    continue
                title = clean_title(href[1])
                if len(title) < 4:
                    continue
                hits.append({"title": title, "url": u, "domain": h, "via": "duckduckgo"})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            warnings.append(f"duckduckgo: {exc}")
    if not hits:
        warnings.append("web: no usable results")
    seen: set[str] = set()
    unique: list[dict] = []
    for hit in hits:
        key = (hit.get("domain") or host_of(hit["url"])) + urllib.parse.urlparse(hit["url"]).path.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
        if len(unique) >= limit:
            break
    return unique, warnings


def nominatim(name: str, city: str = "", near: tuple[float, float] | None = None,
              country: str = "") -> tuple[dict, list[str]]:
    """Look the place up in OSM, including its extratags (phone, website, wikidata)."""
    warnings: list[str] = []
    params: dict[str, str] = {"format": "jsonv2", "addressdetails": "1", "extratags": "1", "limit": "3"}
    if city:
        params["q"] = f"{name}, {city}" + (f", {country}" if country else "")
    elif near:
        params["q"] = name
        params["viewbox"] = f"{near[1] - 0.08},{near[0] + 0.08},{near[1] + 0.08},{near[0] - 0.08}"
        params["bounded"] = "0"
    else:
        params["q"] = name
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    try:
        _, page = fetch_text(url)
        data = json.loads(page)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {}, [f"nominatim: {exc}"]
    if not data:
        return {}, ["nominatim: no result"]
    best = data[0]
    addr = best.get("address") or {}
    extra = best.get("extratags") or {}
    place = {
        "display_name": best.get("display_name"),
        "lat": float(best["lat"]) if best.get("lat") else None,
        "lon": float(best["lon"]) if best.get("lon") else None,
        "type": best.get("type"),
        "address": ", ".join(norm(v) for k, v in addr.items()
                             if k in ("road", "house_number", "suburb", "city", "town", "postcode", "country")),
        "phone": extra.get("phone") or extra.get("contact:phone") or "",
        "website": extra.get("website") or extra.get("contact:website") or "",
        "email": extra.get("email") or extra.get("contact:email") or "",
        "wikipedia": extra.get("wikipedia") or "",
        "wikidata": extra.get("wikidata") or "",
        "opening_hours": extra.get("opening_hours") or "",
    }
    return place, warnings


def download_images(urls: list[str], out_dir: Path, page: str, limit: int = 6) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[dict] = []
    seen: set[str] = set()
    stems: set[str] = set()
    for url in urls:
        if len(saved) >= limit:
            break
        if url in seen:
            continue
        seen.add(url)
        # WordPress serves the same logo at -768x432, -300x169, …: one is enough
        stem = re.sub(r"-\d+x\d+(?=\.\w+$)", "", Path(urllib.parse.urlparse(url).path).name.lower())
        if stem in stems:
            continue
        stems.add(stem)
        try:
            final, body = fetch(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            continue
        if len(body) < 8_000:
            continue
        if not (body[:3] == b"\xff\xd8\xff" or body[:8] == b"\x89PNG\r\n\x1a\n" or body[:4] == b"RIFF"):
            continue
        ext = ".jpg" if body[:3] == b"\xff\xd8\xff" else ".png" if body[:4] == b"\x89PNG" else ".webp"
        name = f"img_{len(saved) + 1:02d}{ext}"
        try:
            (out_dir / name).write_bytes(body)
        except OSError:
            continue
        saved.append({"file": f"{out_dir.name}/{name}", "src": final, "page": page, "bytes": len(body)})
    return saved


# --------------------------------------------------------------------------- #
# dossier assembly
# --------------------------------------------------------------------------- #

def mine_page(url: str, page: str, venue_host: str) -> dict:
    """Everything contact-shaped on one page: text, phones, mails, socials, images."""
    parser = _Links()
    parser.feed(page)
    text = parser.text
    phones = []
    emails = []
    socials: list[dict] = []
    address = ""
    ld = jsonld_objects(parser.scripts)
    address = address_from_jsonld(ld)
    for o in ld:
        tel = o.get("telephone")
        if isinstance(tel, str):
            phones += find_phones(tel)
        same = o.get("sameAs") or []
        for one in (same if isinstance(same, list) else [same]):
            if isinstance(one, str) and kind_of(one, venue_host) in SOCIAL_HOSTS.values():
                socials.append({"kind": kind_of(one, venue_host), "url": one})
    for tel in re.findall(r'href="tel:([^"]+)"', page, re.I):
        phones += find_phones(urllib.parse.unquote(tel))
    for mail in re.findall(r'href="mailto:([^"?]+)', page, re.I):
        emails += find_emails(urllib.parse.unquote(mail))
    for line in text.splitlines():
        low = line.lower()
        if re.search(r"\b(t[ée]l|tel\.|t[ée]l[ée]phone|phone|whatsapp)\b", low):
            phones += find_phones(line)
        if not address and looks_like_address(line):
            address = norm(line)
    emails += find_emails(text)
    for href, _label in parser.links:
        u = absolute(url, href)
        k = kind_of(u, venue_host)
        if k in SOCIAL_HOSTS.values():
            socials.append({"kind": k, "url": u})
    imgs = [absolute(url, src) for src in parser.images]
    imgs = [u for u in imgs if u.startswith("http") and (
        urllib.parse.urlparse(u).path.lower().endswith(IMAGE_EXT) or "/uploads/" in u or "/wp-content/" in u)]
    title = norm((re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I) or [None, ""])[1])
    return {"text": text, "phones": phones, "emails": emails, "socials": socials,
            "address": address, "images": imgs, "title": title}


def build(name: str, city: str, region: str, country: str, lat: float | None, lon: float | None,
          url: str, out_dir: Path, max_images: int, offline: bool) -> dict:
    warnings: list[str] = []
    site: dict = {}
    if not city and lat is None:
        warnings.append("no city or coordinates given — the place lookup may match a different venue")
    place, w = nominatim(name, city=city, near=(lat, lon) if lat and lon else None, country=country)
    warnings += w
    if offline:
        warnings.append("offline: no search, no downloads")

    website = url or place.get("website") or ""
    venue_host = host_of(website)

    phones: list[str] = find_phones(place.get("phone", ""))
    emails: list[str] = find_emails(place.get("email", ""))
    address = place.get("address", "")
    images: list[dict] = []
    socials: list[dict] = []

    if website and not offline:
        try:
            final, page = fetch_text(website)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            warnings.append(f"site: {exc}")
            final, page = website, ""
        if page:
            home = mine_page(final, page, venue_host)
            site = {"url": final, "title": home["title"]}
            phones += [p for p in home["phones"] if p not in phones]
            emails += [e for e in home["emails"] if e.lower() not in [x.lower() for x in emails]]
            socials += home["socials"]
            address = home["address"] or address

            # One level down: contact / about / access pages carry the phone.
            extra = []
            parser = _Links()
            parser.feed(page)
            for href, label in parser.links:
                u = absolute(final, href)
                if kind_of(u, venue_host) != "official" or u.rstrip("/") == final.rstrip("/"):
                    continue
                if re.search(r"contact|nous|infos?|access|plan|about|cinema", (href + " " + label), re.I):
                    if u not in extra:
                        extra.append(u)
            pages: list[str] = []
            sub_images: list[str] = []
            for u in extra[:2]:
                try:
                    _, sub = fetch_text(u)
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
                    continue
                pages.append(u)
                mined = mine_page(u, sub, venue_host)
                phones += [p for p in mined["phones"] if p not in phones]
                emails += [e for e in mined["emails"] if e.lower() not in [x.lower() for x in emails]]
                socials += mined["socials"]
                sub_images += mined["images"]
                address = address or mined["address"]
            site["pages"] = pages
            emails = emails[:6]
            if not address:
                for line in home["text"].splitlines():
                    if city and city.lower() in line.lower() and looks_like_address(line):
                        address = norm(line)
                        break
            imgs = list(dict.fromkeys(home["images"] + sub_images))
            images = download_images(imgs[:max_images * 4], out_dir, final, limit=max_images)
            if not images:
                warnings.append("site: no downloadable photographs found (lazy-loading or CDN protection)")

    # one social per (kind, url): the same profile is linked from every page
    dedup: list[dict] = []
    for s in socials:
        u = s["url"].rstrip("/")
        if not any(x["url"].rstrip("/") == u for x in dedup):
            dedup.append({"kind": s["kind"], "url": u})
    socials = dedup

    sources: list[dict] = []
    tokens = name_tokens(name)
    dropped = 0
    if not offline:
        query = f'"{name}" {city}'.strip()
        news, w = search_news(query, country=country, limit=8)
        warnings += w
        for hit in news:
            if not relevant(hit["title"], hit["url"], tokens):
                dropped += 1
                continue
            sources.append({"kind": "press", "title": hit["title"], "url": hit["url"],
                            "domain": hit.get("domain") or host_of(hit["url"]),
                            "publisher": hit.get("publisher") or "", "date": hit.get("date") or ""})
        hits, w = search_web(query, limit=14)
        warnings += w
        if not hits and not news:
            hits = wikipedia_search(query)
            if hits:
                warnings.append("search engines blocked: encyclopedic results only")
        for hit in hits:
            u = hit["url"]
            k = kind_of(u, venue_host)
            if (k == "official" and site) or host_of(u) in SKIP_HOSTS:
                continue
            if k in ("other", "press") and not relevant(hit["title"], u, tokens):
                dropped += 1
                continue
            sources.append({"kind": k, "title": hit["title"], "url": u,
                            "domain": hit.get("domain") or host_of(u)})
        for s in socials:
            if not any(x["url"] == s["url"] for x in sources):
                sources.insert(0, {"kind": s["kind"], "title": f"{name} on {s['kind']}", "url": s["url"],
                                   "domain": host_of(s["url"])})

    order = {"official": 0, "instagram": 1, "facebook": 2, "tiktok": 3, "x": 4, "youtube": 5,
             "press": 6, "encyclopedia": 7, "map": 8, "other": 9}
    sources.sort(key=lambda s: order.get(s["kind"], 9))

    dossier = {
        "tool": "dossier.py",
        "author": AUTHOR,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query": {"name": name, "city": city, "region": region, "country": country, "lat": lat, "lon": lon},
        "site": site,
        "address": address,
        "phone": phones,
        "email": emails,
        "socials": socials,
        "place": place,
        "sources": sources[:40],
        "images": images,
        "warnings": warnings,
        "dropped_offtopic": dropped,
        "note": "Kind labels are a hint from the domain, not a verified fact. "
                "Instagram/Facebook are linked, never scraped; photos come from the venue site.",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dossier.json").write_text(json.dumps(dossier, indent=1, ensure_ascii=False), encoding="utf-8")
    return dossier


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gather sources, contacts and photos for an identified place.")
    ap.add_argument("--name", required=True, help='venue or place, e.g. "Cinéma Le Colisée"')
    ap.add_argument("--city", default="")
    ap.add_argument("--region", default="")
    ap.add_argument("--country", default="")
    ap.add_argument("--lat", type=float, default=None)
    ap.add_argument("--lon", type=float, default=None)
    ap.add_argument("--url", default="", help="venue website, if known")
    ap.add_argument("--out-dir", default="recon/sources")
    ap.add_argument("--max-images", type=int, default=6)
    ap.add_argument("--offline", action="store_true", help="skip search and downloads")
    args = ap.parse_args(argv)

    started = time.time()
    dossier = build(args.name, args.city, args.region, args.country, args.lat, args.lon, args.url,
                    Path(args.out_dir), args.max_images, args.offline)
    print(json.dumps({
        "dossier": str(Path(args.out_dir) / "dossier.json"),
        "sources": len(dossier["sources"]),
        "images": len(dossier["images"]),
        "phone": dossier["phone"],
        "warnings": len(dossier["warnings"]),
        "seconds": round(time.time() - started, 1),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
