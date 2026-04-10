"""Scraper for cyber.gouv.fr SecNumEdu labeled formation pages.

Parses the formation initiale (FI) and formation continue (FC) pages and
extracts (name, etablissement, diplome) triples into a flat JSON file that
downstream pipeline code reads via src.collect.secnumedu.load_secnumedu.

Structure of both pages (Drupal / Sites Conformes):
- FI: cards use <h3 class="fr-card__title"> with <b>Diplôme :</b>
- FC: cards use <h3 class="fr-card__title"> with <b>Domaine de formation :</b>
      (no Diplôme field — formation continue certifications don't map to a diploma)
"""
import json
import re
from pathlib import Path

import requests


FI_URL = (
    "https://cyber.gouv.fr/offre-de-service/formations-entrainement-et-decouverte-des-metiers/"
    "formations/formation-labellisees-par-lanssi/formation-secnumedu/"
)
FC_URL = (
    "https://cyber.gouv.fr/offre-de-service/formations-entrainement-et-decouverte-des-metiers/"
    "formations/formation-labellisees-par-lanssi/formation-secnumedu-fc/"
)

USER_AGENT = "Mozilla/5.0 OrientIA/0.1 (research)"

# Each page lists formations as download cards with a consistent structure:
#   <div class="fr-card fr-card--horizontal ...">
#     <h2|h3 class="fr-card__title"><a ...>FORMATION NAME</a></h3>
#     <p ...><b>Etablissement :</b> ETAB NAME</p>
#     <p ...><b>Diplôme :</b> DIPLOME</p>   ← FI only
#     <p ...><b>Domaine de formation :</b> DOMAIN</p>  ← FC only
CARD_RE = re.compile(
    r'<div class="fr-card fr-card--horizontal'
    r'.*?(?=<div class="fr-card fr-card--horizontal|</main>)',
    re.DOTALL,
)
TITLE_RE = re.compile(
    r'<(?:h2|h3) class="fr-card__title">\s*<a[^>]*>\s*(.*?)\s*</a>',
    re.DOTALL,
)
ETAB_RE = re.compile(r'<b>Etablissement\s*:</b>\s*(.*?)</p>', re.DOTALL)
DIPLOME_RE = re.compile(r'<b>Dipl[oô]me\s*:</b>\s*(.*?)</p>', re.DOTALL)
DOMAINE_RE = re.compile(r'<b>Domaine de formation\s*:</b>\s*(.*?)</p>', re.DOTALL)


def _clean(s: str) -> str:
    """Strip HTML tags, decode common entities, and collapse whitespace."""
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&quot;", '"').replace("&apos;", "'")
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    return re.sub(r"\s+", " ", s).strip()


def parse_page(html: str, source_type: str) -> list[dict]:
    """Extract formation entries from a SecNumEdu list page.

    Args:
        html: Raw HTML of the page.
        source_type: ``"FI"`` (formation initiale) or ``"FC"`` (formation continue).

    Returns:
        List of dicts with keys ``nom``, ``etablissement``, ``diplome``,
        ``source_type``.
    """
    entries = []
    for card in CARD_RE.findall(html):
        title_m = TITLE_RE.search(card)
        etab_m = ETAB_RE.search(card)
        if not title_m or not etab_m:
            continue

        nom = _clean(title_m.group(1))
        etab = _clean(etab_m.group(1))

        # FI pages carry a Diplôme field; FC pages carry a Domaine de formation
        diplome_m = DIPLOME_RE.search(card)
        domaine_m = DOMAINE_RE.search(card)
        if diplome_m:
            diplome = _clean(diplome_m.group(1))
        elif domaine_m:
            diplome = _clean(domaine_m.group(1))
        else:
            diplome = ""

        if nom and etab:
            entries.append(
                {
                    "nom": nom,
                    "etablissement": etab,
                    "diplome": diplome,
                    "source_type": source_type,
                }
            )
    return entries


def fetch_all() -> list[dict]:
    """Fetch both SecNumEdu pages and return deduplicated formation entries."""
    headers = {"User-Agent": USER_AGENT}
    all_entries: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for url, source_type in ((FI_URL, "FI"), (FC_URL, "FC")):
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        for entry in parse_page(resp.text, source_type):
            sig = (entry["nom"], entry["etablissement"])
            if sig in seen:
                continue
            seen.add(sig)
            all_entries.append(entry)

    return all_entries


def main() -> None:
    entries = fetch_all()
    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "secnumedu.json"
    out_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(entries)} SecNumEdu entries to {out_path}")
    for e in entries[:5]:
        print(f"  - {e['nom'][:80]}")
        print(f"    etab={e['etablissement']} | dipl={e['diplome']} | type={e['source_type']}")


if __name__ == "__main__":
    main()
