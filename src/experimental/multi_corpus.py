"""Multi-corpus retrievable RAG — convergence Axe 1.A+B (ADR-048 DRAFT).

Module qui gère plusieurs corpus retrievables en parallèle pour le RAG
OrientIA, sans toucher à `fiche_to_text` (protected file CLAUDE.md) ni
au pipeline existant `formations.json`.

## Constat (cf PR #56 Axe 1.A pivot)

Tentative initiale d'intégrer ROME + format_court dans `formations.json`
via merger v2 → couverture <5 % (8 codes ROME inter sur 25 dans
formations vs 408 dans ideo). Pivot vers **N corpus retrievables
parallèles** :

| Corpus | Records | Domain | Source |
|---|---:|---|---|
| `formations.json` | 48 914 | formation | Parcoursup + ONISEP fusionnés |
| `metiers_corpus.json` | 1 075 | metier | ONISEP Idéo-Fiches XML |
| `parcours_bacheliers_corpus.json` | 151 | parcours_bacheliers | MESRI |
| `apec_regions_corpus.json` | 13 | apec_region | APEC observatoire 2026 |

Total : 50 153 records sur 4 domains.

## Stratégie (cette PR)

**Loader unifié + extraction texte pour embedding** — pas de rebuild
FAISS dans cette PR (coût $5-10 lié au bench v5 chiffré reporté à la
PR convergence + bench, budget validé Matteo 2026-04-25).

Ce module pose les fondations :
- `Corpus` : dataclass holding records + domain + path source
- `MultiCorpusLoader` : load_all() / load_one() avec graceful skip si
  fichier absent
- `extract_texts_for_embedding(corpus)` : retourne list[(id, text)] prêts
  pour `embed_texts_batched(client, texts)`
- Helpers stats (count_by_domain, total)

Intégration côté retriever (FAISS multi-index OU index unifié avec
`metadata.domain`) → PR suivante après bench v5 validé.

## Compatibilité

- Préserve `fiche_to_text` v3 (formations.json inchangé)
- Préserve `retrieve_top_k` (signature inchangée)
- Additif zéro régression : si un corpus est absent du disque, il est
  simplement skippé (fresh clone fonctionnel)

## Liens

- ADR-048 (DRAFT) RAG multi-corpus : à formaliser à la PR convergence
- ADR-033 ROME masking generator : préservé
- Protected file note CLAUDE.md `fiche_to_text` : non modifié
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# Paths par défaut des corpus retrievables (relatifs au repo root)
DEFAULT_CORPUS_PATHS: dict[str, Path] = {
    "formation": Path("data/processed/formations.json"),
    "metier": Path("data/processed/metiers_corpus.json"),
    "parcours_bacheliers": Path("data/processed/parcours_bacheliers_corpus.json"),
    "apec_region": Path("data/processed/apec_regions_corpus.json"),
}


@dataclass
class Corpus:
    """Représente un corpus retrievable chargé en mémoire."""

    domain: str
    path: Path
    records: list[dict[str, Any]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.records)

    @property
    def is_empty(self) -> bool:
        return not self.records


def _extract_text(record: dict[str, Any], domain: str) -> str:
    """Récupère le texte retrievable d'un record selon son domain.

    - `formation` : pas de champ `text` pré-calculé, on retourne `nom`
      par défaut (l'embedding réel passe par `fiche_to_text` v3,
      pas par cette fonction). Cas séparé du multi-corpus.
    - `metier`, `parcours_bacheliers`, `apec_region` : champ `text`
      pré-calculé par les builders `build_metiers_corpus`,
      `parcours_bacheliers`, `apec_regions`.
    """
    if domain == "formation":
        # Cas spécial : formations.json n'a pas de `text` pré-calculé.
        # L'embedding réel passe par `fiche_to_text` v3 (cf retriever).
        # Retourne le `nom` comme placeholder safe pour usage non-RAG.
        return record.get("nom") or ""
    return record.get("text") or ""


class MultiCorpusLoader:
    """Charge les corpus retrievables OrientIA depuis le disque.

    Usage:

    ```python
    loader = MultiCorpusLoader()
    corpora = loader.load_all()  # dict {domain: Corpus}
    print(loader.summary())
    ```

    Si un fichier corpus est absent, le `Corpus` correspondant est créé
    vide et un log est émis (silent en prod). Permet aux fresh clones de
    fonctionner même sans tous les pipelines exécutés.
    """

    def __init__(self, paths: dict[str, Path] | None = None):
        self.paths = paths or dict(DEFAULT_CORPUS_PATHS)
        self.corpora: dict[str, Corpus] = {}

    def load_one(self, domain: str, path: Path | None = None) -> Corpus:
        target = path or self.paths.get(domain)
        if target is None:
            raise KeyError(f"Domain inconnu : {domain}")
        if not target.exists():
            corpus = Corpus(domain=domain, path=target, records=[])
            self.corpora[domain] = corpus
            return corpus
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  [multi_corpus] {domain}: erreur lecture {target} ({e}) — skip")
            corpus = Corpus(domain=domain, path=target, records=[])
            self.corpora[domain] = corpus
            return corpus
        if not isinstance(data, list):
            print(f"  [multi_corpus] {domain}: {target} pas une liste — skip")
            data = []
        corpus = Corpus(domain=domain, path=target, records=data)
        self.corpora[domain] = corpus
        return corpus

    def load_all(self) -> dict[str, Corpus]:
        for domain in self.paths:
            self.load_one(domain)
        return self.corpora

    def get(self, domain: str) -> Corpus:
        if domain not in self.corpora:
            return self.load_one(domain)
        return self.corpora[domain]

    def count_by_domain(self) -> dict[str, int]:
        return {d: len(c) for d, c in self.corpora.items()}

    def total(self) -> int:
        return sum(len(c) for c in self.corpora.values())

    def summary(self) -> str:
        lines = ["MultiCorpus state :"]
        for d, c in self.corpora.items():
            lines.append(f"  - {d:24s} {len(c):>6} records ({c.path})")
        lines.append(f"  TOTAL                    {self.total():>6} records")
        return "\n".join(lines)


def extract_texts_for_embedding(
    corpus: Corpus,
    skip_empty: bool = True,
) -> list[tuple[str, str]]:
    """Retourne list[(id, text)] prêts pour `embed_texts_batched(client, texts)`.

    Pour le domain `formation`, retourne `(record_idx_or_id, nom)` (placeholder
    car l'embedding réel passe par `fiche_to_text`). Pour les autres domains,
    retourne `(record['id'], record['text'])`.

    Si `skip_empty=True` (par défaut), skip les records sans `text` non-vide.
    """
    out: list[tuple[str, str]] = []
    for i, record in enumerate(corpus.records):
        text = _extract_text(record, corpus.domain)
        if skip_empty and not text:
            continue
        # `formation` n'a pas de champ id stable → utilise idx; les autres
        # corpus ont un `id` pré-défini.
        identifier = str(record.get("id") or f"{corpus.domain}:{i}")
        out.append((identifier, text))
    return out


def merge_for_embedding(
    corpora: Iterable[Corpus],
    domains: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Fusionne les corpus en records uniformes prêts pour un index FAISS unifié.

    Format de sortie (compatible avec les builders existants) :
    `{id, domain, text, source_corpus_path, original_record}`.

    Le champ `original_record` permet au generator/reranker d'accéder aux
    métadonnées domain-spécifiques (codes_rome, niveau_acces, etc.).
    """
    domains_set = set(domains) if domains else None
    out: list[dict[str, Any]] = []
    for corpus in corpora:
        if domains_set and corpus.domain not in domains_set:
            continue
        for i, record in enumerate(corpus.records):
            text = _extract_text(record, corpus.domain)
            if not text:
                continue
            identifier = str(record.get("id") or f"{corpus.domain}:{i}")
            out.append(
                {
                    "id": identifier,
                    "domain": corpus.domain,
                    "text": text,
                    "source_corpus_path": str(corpus.path),
                    "original_record": record,
                }
            )
    return out


def main() -> None:  # pragma: no cover
    loader = MultiCorpusLoader()
    loader.load_all()
    print(loader.summary())


if __name__ == "__main__":  # pragma: no cover
    main()
