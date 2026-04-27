"""Corrections factuelles — corpus retrievable Sprint 8 Wave 1.

Source : `data/raw/corrections_factuelles/sprint8_w1_corrections.json`
(JSON curé manuellement). Corrections d'erreurs persistantes
identifiées via retours humains user_test_v3.

## Dimension unique

Ce corpus est **prioritaire** dans le retrieval (boost 1.5 via
intent classifier extension Sprint 8 W1). Quand une query touche
un sujet où le LLM a une erreur récurrente (HEC AST, VAE, bac S
supprimé, coûts EPITA/INSEEC), la cell de correction est priorisée
top-K → le LLM s'appuie dessus pour générer une réponse correcte.

## Stratégie aggregation

1 cell par correction (pas de granularité multiple — les corrections
sont des unités atomiques d'autorité).

Domain `correction_factuelle` (nouveau, prioritaire). Granularité
implicite `correction`.

## Pattern anti-hallu défensif Sprint 6 Action 4

Chaque correction inclut :
- `subject` clair (sujet de l'erreur)
- `erreur_persistante` : ce qui était observé (pour debug futur)
- `correction_authoritative` : la version correcte avec fourchettes
  approximatives + "consulter source officielle pour montant exact"
- `source_officielle` : URL gouv.fr / edu.fr / org officiel
- `ref_user_test` : trace de la signalisation (user_test_v3 Qx)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/raw/corrections_factuelles/sprint8_w1_corrections.json")
CORPUS_PATH = Path("data/processed/corrections_factuelles_corpus.json")


def load_raw(path: Path | None = None) -> dict[str, Any]:
    target = path or RAW_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def aggregate_corrections(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """1 cell par correction. Ordre original préservé."""
    out: list[dict[str, Any]] = []
    for c in raw.get("corrections", []):
        subject = c.get("subject", "")
        erreur = c.get("erreur_persistante", "")
        correction = c.get("correction_authoritative", "")
        public = c.get("public_cible", "")
        source = c.get("source_officielle", "")
        ref = c.get("ref_user_test", "")

        parts = [
            f"Correction factuelle — {subject}",
        ]
        if correction:
            parts.append(f"Information correcte (autorité) : {correction}")
        if public:
            parts.append(f"Public cible : {public}")
        if erreur:
            parts.append(f"Erreur fréquente à éviter : {erreur}")
        if source:
            parts.append(f"Source officielle (montant/règle exacte année en cours) : {source}")
        parts.append("Note : cette correction est prioritaire pour OrientIA. Toujours préférer cette information à toute autre source dans la réponse au public cible.")

        out.append({
            "id": f"correction:{c['id']}",
            "domain": "correction_factuelle",
            "source": "corrections_factuelles_curated",
            "granularity": "correction",
            "subject": subject,
            "ref_user_test": ref,
            "source_officielle": source,
            "text": " | ".join(parts),
        })
    return out


def build_corpus(raw: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if raw is None:
        raw = load_raw()
    return aggregate_corrections(raw)


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[CORRECTIONS] loading {RAW_PATH}")
    raw = load_raw()
    n = len(raw.get("corrections", []))
    print(f"[CORRECTIONS] {n} corrections raw, version {raw.get('version', 'n/a')}")

    corpus = build_corpus(raw)
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    print(f"[CORRECTIONS] {len(corpus)} cells aggregées → {CORPUS_PATH}")
    print(f"[CORRECTIONS] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
