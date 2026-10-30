# GeoWeb — source gatherer tests (pure functions; no network, no Playwright).
# Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from sources.dossier import (  # noqa: E402  (needs REPO on sys.path)
    clean_title,
    find_emails,
    find_phones,
    looks_like_address,
    name_tokens,
    relevant,
)
from sources.lens import classify_sections, parse_text, place_sentence, urls_in  # noqa: E402


# ---------------------------------------------------------------- classify
def test_kind_of_labels_socials_and_press():
    from sources.classify import kind_of

    assert kind_of("https://www.instagram.com/lecoliseemarrakech/") == "instagram"
    assert kind_of("https://news.le360.ma/article") == "press"
    assert kind_of("https://fr.wikipedia.org/wiki/Marrakech") == "encyclopedia"
    assert kind_of("https://example.org/an-article") == "other"


def test_kind_of_prefers_the_venue_itself():
    from sources.classify import kind_of

    assert kind_of("https://www.lecolisee.ma/contact/", venue_host="lecolisee.ma") == "official"
    assert kind_of("https://www.instagram.com/x", venue_host="lecolisee.ma") == "instagram"


def test_is_engine_rejects_search_chrome_but_keeps_real_sites():
    from sources.classify import is_engine

    assert is_engine("mail.google.com")
    assert is_engine("about.google")
    assert is_engine("google.co.ma")
    assert is_engine("accounts.google.com")
    assert not is_engine("lecolisee.ma")
    assert not is_engine("instagram.com")


# ----------------------------------------------------------------- dossier
def test_find_phones_accepts_dialable_numbers():
    found = find_phones("Tél : +212 5 24 43 31 00 — contact")
    assert found == ["+212 5 24 43 31 00"]


def test_find_phones_rejects_css_integers_and_years():
    assert find_phones("1342177279 2024 19/06/2024") == []


def test_find_emails_dedupes_and_skips_asset_names():
    got = find_emails("Contact: Info@LeColisee.ma, info@lecolisee.ma logo@2x.png")
    assert got == ["Info@LeColisee.ma"]


def test_looks_like_address_requires_number_and_street_word():
    assert looks_like_address("Boulevard Mohammed Zerktouni, Guéliz, Marrakech 40200")
    assert not looks_like_address("Nos films à l'affiche cette semaine")


def test_name_tokens_drop_generic_words():
    assert name_tokens("Cinéma Le Colisée") == ["colisee"]


def test_relevant_keeps_only_results_naming_the_place():
    tokens = name_tokens("Cinéma Le Colisée")
    assert relevant("Le Colisée, cinéma à Marrakech | SAM.ma", "https://sam.ma/x", tokens)
    assert not relevant("Cinémas Pathé Maroc", "https://pathe.ma/fr", tokens)


def test_clean_title_strips_engine_chrome():
    assert clean_title("culturama.mahttps://culturama.ma › agenda › cinema") == "culturama.ma"
    assert clean_title("Le Colisée, cinéma à Marrakech ...") == "Le Colisée, cinéma à Marrakech"


# -------------------------------------------------------------------- lens
LENS_PAGE = """Google Lens
Cinéma Le Colisée
L'image montre la salle de l'emblématique Cinéma Le Colisée situé à Marrakech, au Maroc.
Correspondances exactes
lecolisee.ma
https://www.lecolisee.ma/
Cinéma Le Colisée Marrakech
Résultats visuels
instagram.com
https://www.instagram.com/lecoliseemarrakech/
Cinéma Le Colisée on Instagram
accounts.google.com
https://accounts.google.com/signin
"""


def test_urls_in_trims_trailing_punctuation():
    assert urls_in("see https://a.example/x, and https://b.example/y.") == [
        "https://a.example/x", "https://b.example/y"]


def test_place_sentence_finds_the_overview_line():
    lines = [line.strip() for line in LENS_PAGE.splitlines() if line.strip()]
    assert "Cinéma Le Colisée" in place_sentence(lines)
    assert place_sentence(["just a caption"]) == ""


def test_parse_text_separates_exact_from_visual():
    parsed = parse_text(LENS_PAGE)
    buckets = classify_sections(parsed["links"])
    assert [link["domain"] for link in buckets["exact"]] == ["lecolisee.ma"]
    assert [link["domain"] for link in buckets["visual"]] == ["instagram.com"]
    assert parsed["links"][0]["title"] == "Cinéma Le Colisée Marrakech"


def test_parse_text_drops_search_engine_chrome():
    parsed = parse_text(LENS_PAGE)
    assert all("google" not in link["domain"] for link in parsed["links"])


def test_venue_name_prefers_the_entity_line_over_page_chrome():
    from sources.lens import venue_name

    parsed = parse_text(LENS_PAGE)
    parsed["hints"] = ["Passer directement au contenu principal", "Correspondances visuelles",
                       "Le Colisée, cinéma à Marrakech | SAM.ma"]
    parsed["place"] = "L'image montre la salle de l'emblématique Cinéma Le Colisée situé à Marrakech, au Maroc."
    assert venue_name(parsed) == "Le Colisée"


def test_venue_name_is_empty_when_nothing_names_a_place():
    from sources.lens import venue_name

    assert venue_name({"hints": ["Aperçu IA", "Résultats de recherche"], "place": ""}) == ""


def test_place_context_reads_the_city_from_the_overview_sentence():
    from sources.lens import place_context

    assert place_context({"place": "L'image montre la salle de l'emblématique Cinéma Le Colisée "
                                   "situé à Marrakech, au Maroc."}) == {"city": "Marrakech", "country": "Maroc"}
    assert place_context({"place": "This image shows the Colosseum located in Rome, Italy."}) == {
        "city": "Rome", "country": "Italy"}
    assert place_context({"place": ""}) == {"city": "", "country": ""}


# --------------------------------------------------------------- assistant
def test_context_text_marks_absent_phone_and_lists_sources():
    from assistant.chat import context_text

    ctx = {
        "name": "s", "kind": "photo", "status": "completed",
        "result": {"country": "MA", "city_or_nearest_locality": "Marrakech",
                   "latitude": 31.63, "longitude": -8.01, "confidence": "high"},
        "truth": {}, "report": "", "recon_summary": "",
        "lens": {"status": "imported", "place": "Le Colisée", "matches": []},
        "dossier": {"address": "Bd Zerktouni", "phone": [], "email": [],
                    "website": "https://www.lecolisee.ma",
                    "sources": [{"kind": "press", "title": "T", "url": "u", "site": "sam.ma"}],
                    "images": [], "warnings": []},
    }
    text = context_text(ctx)
    assert "ph" in text.lower() and "none published" in text
    assert "Le Colisée" in text and "sam.ma" in text
    assert "31.63" in text


def test_messages_include_evidence_and_history():
    from assistant.chat import messages

    ctx = {"name": "s", "kind": "photo", "status": "", "result": {}, "truth": {},
           "report": "R", "recon_summary": "", "lens": {}, "dossier": {}}
    msgs = messages(ctx, "where?", [{"role": "user", "content": "hi"}])
    assert msgs[0]["role"] == "system" and "EVIDENCE" in msgs[0]["content"]
    assert msgs[1] == {"role": "user", "content": "hi"}
    assert msgs[-1] == {"role": "user", "content": "where?"}
