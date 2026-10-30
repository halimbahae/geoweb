"""Shared, dependency-free helpers for the GeoWeb source gatherers.

Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

`dossier.py` and `lens.py` both need to answer the same question — "what kind of
source is this URL?" — and both need the same tolerant text normalisation. This
module holds only that, so the two tools label links identically and the tests
can pin the classification down in one place.

Stdlib only.
"""

from __future__ import annotations

import html
import urllib.parse

AUTHOR = "Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>"

SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "tiktok.com": "tiktok",
    "twitter.com": "x",
    "x.com": "x",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "linkedin.com": "linkedin",
    "pinterest.com": "pinterest",
    "snapchat.com": "snapchat",
    "wa.me": "whatsapp",
}

# Known outlets are labelled; anything else stays "other" rather than guessed.
PRESS_HOSTS = {
    "hespress.com", "le360.ma", "lematin.ma", "h24info.ma", "medias24.com",
    "telquel.ma", "yabiladi.com", "aujourdhui.ma", "libe.ma", "menara.ma",
    "moroccoworldnews.com", "leconomiste.com", "challenge.ma", "lopinion.ma",
    "maroc-hebdo.press.ma", "lesiteinfo.com", "bladi.net", "maroc24.com",
    "sam.ma", "sortiraumaroc.com", "culturama.ma", "cinenews.ma",
    "nouvelleobs.com", "lnt.ma", "2m.ma", "snrtnews.com", "al3omk.com",
}

SKIP_HOSTS = {
    "accounts.google.com", "policies.google.com", "support.google.com",
    "google.com", "gstatic.com", "youtube-nocookie.com", "duckduckgo.com",
    "bing.com", "go.microsoft.com", "w3.org",
}

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def is_engine(host: str) -> bool:
    """True for search-engine chrome (Google's own pages, accounts, apps) — never evidence."""
    h = (host or "").lower().removeprefix("www.")
    if not h:
        return True
    if h in SKIP_HOSTS:
        return True
    if h.endswith((".google.com", ".gstatic.com")):
        return True
    if h.startswith(("google.", "about.google", "mail.google", "accounts.google",
                     "support.google", "policies.google", "maps.google")):
        return True
    return any(part in h for part in (".google.", ".gstatic.", ".googleusercontent."))


def norm(s: str) -> str:
    return " ".join(html.unescape(s or "").split())


def absolute(base: str, href: str) -> str:
    try:
        return urllib.parse.urljoin(base, (href or "").strip())
    except ValueError:
        return ""


def host_of(url: str) -> str:
    try:
        h = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""
    return h.lower().removeprefix("www.")


def kind_of(url: str, venue_host: str = "") -> str:
    """Classify a URL so the console can label it (official / social / press / …)."""
    h = host_of(url)
    if not h:
        return "other"
    if venue_host and (h == venue_host or h.endswith("." + venue_host)):
        return "official"
    for domain, kind in SOCIAL_HOSTS.items():
        if h == domain or h.endswith("." + domain):
            return kind
    if h.endswith(".press.ma") or any(h == d or h.endswith("." + d) for d in PRESS_HOSTS):
        return "press"
    if "wikipedia.org" in h or "wikidata.org" in h:
        return "encyclopedia"
    if "openstreetmap.org" in h or "nominatim" in h:
        return "map"
    if "google." in h and "/maps" in url:
        return "map"
    return "other"
