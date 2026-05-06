"""Factory canonique pour OrientIAPipeline en mode production.

Une seule source de vérité — fini les flags éparpillés dans run_real_full,
mini_bench, scripts/* qui créent chacun un pipeline avec un sous-ensemble
de features actives ou désactivées.

`make_production_pipeline()` instancie le pipeline avec **toutes les
features câblées** (validator + golden_qa + post_process), avec des flags
opt-out individuels pour A/B et des défauts paths pour les artefacts
golden_qa.

Usage typique :

    from src.rag.factory import make_production_pipeline
    from mistralai.client import Mistral

    client = Mistral(api_key=...)
    fiches = json.loads(Path("data/processed/formations.json").read_text())
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from("data/embeddings/formations.index")
    text, sources = pipeline.answer("Ma question ?")

Pour A/B (désactiver une feature individuelle) :

    pipeline = make_production_pipeline(
        client, fiches,
        enable_golden_qa=False,  # mesurer l'impact du Golden QA
    )

Pour reproduire le baseline historique (comme run_real_full.py Phase F) :

    pipeline = make_production_pipeline(
        client, fiches,
        enable_validator=False,
        enable_golden_qa=False,
        enable_post_process=False,
    )

Cf plan refonte produit niveau 2 — Phase 2 (`~/.claude/plans/...`).
"""
from __future__ import annotations

from pathlib import Path

from mistralai.client import Mistral

from src.rag.pipeline import OrientIAPipeline
from src.rag.scope_classifier import ScopeClassifier
from src.validator import Validator
from src.validator.layer3 import Layer3Validator


# Paths par défaut pour les artefacts Golden QA (chantier D Sprint 10).
# Lazy-loadés au 1er .answer() — ces fichiers doivent exister sur disque
# pour que use_golden_qa=True soit effectif (sinon fallback gracieux + warning).
DEFAULT_GOLDEN_QA_INDEX = "data/embeddings/golden_qa.index"
DEFAULT_GOLDEN_QA_META = "data/processed/golden_qa_meta.json"


def make_production_pipeline(
    client: Mistral,
    fiches: list[dict],
    *,
    # Validator (couches 1+2 par défaut, +layer3 LLM en opt-in)
    enable_validator: bool = True,
    enable_layer3: bool = False,
    corpus_sim_threshold: float = 0.30,
    # Golden QA few-shot (Sprint 10 chantier D)
    enable_golden_qa: bool = True,
    golden_qa_index_path: str | None = None,
    golden_qa_meta_path: str | None = None,
    # Post-process déterministe (Sprint 8 Wave 1)
    enable_post_process: bool = True,
    # Étape 1 refonte 2026-05-06 — ScopeClassifier amont (in_scope/out_of_scope/urgent)
    enable_scope_classifier: bool = True,
    # Retrieval / generation tuning (rarement override)
    use_mmr: bool = True,
    use_intent: bool = True,
    use_metadata_filter: bool = True,
    model: str = "mistral-medium-latest",
) -> OrientIAPipeline:
    """Build a production-ready OrientIAPipeline.

    Args:
        client: Mistral client (gen + embed).
        fiches: list of formation/multi-corpus records (loaded from
            data/processed/formations.json).
        enable_validator: si True, instancie un Validator (rules + corpus_check
            + presence) attaché au pipeline. Default True (production).
        enable_layer3: si True (et enable_validator True), ajoute la couche 3
            LLM Mistral Small. Coût ~$0.001/q + 2-4s latency. Default False.
        corpus_sim_threshold: seuil similarité pour corpus_check (0.30 = très
            permissif, faux positifs rares mais faux négatifs probables).
        enable_golden_qa: si True, active le few-shot Q&A Golden retrieve top-1
            injecté en préfixe utilisateur. Default True (production). Files
            par défaut sur DEFAULT_GOLDEN_QA_INDEX/META.
        golden_qa_index_path: override path index FAISS Golden QA.
        golden_qa_meta_path: override path meta JSON Golden QA.
        enable_post_process: si True, applique strip_invented_urls +
            fix_broken_markdown_tables + validate_onisep_slugs post-validator.
            Déterministe (zéro LLM, zéro risque). Default True.
        use_mmr: diversification MMR post-rerank. Default True (Phase F.3).
        use_intent: classify_intent + intent_to_config. Default True (Phase F.3).
        use_metadata_filter: active le filter métadonnées si criteria fourni
            par l'appelant. Default True (chantier C Sprint 10).
        model: modèle Mistral pour la génération. Default mistral-medium-latest.

    Returns:
        OrientIAPipeline configuré, sans index FAISS chargé. L'appelant doit
        ensuite faire `pipeline.load_index_from(path)` ou `pipeline.build_index()`.
    """
    validator: Validator | None = None
    if enable_validator:
        layer3 = Layer3Validator(client=client) if enable_layer3 else None
        validator = Validator(
            fiches=fiches,
            corpus_sim_threshold=corpus_sim_threshold,
            layer3=layer3,
        )

    scope_classifier: ScopeClassifier | None = None
    if enable_scope_classifier:
        scope_classifier = ScopeClassifier(client=client)

    # Résolution paths Golden QA : si flag activé mais paths non fournis,
    # utiliser les défauts. Le pipeline lazy-loadera au 1er .answer() — si
    # les fichiers n'existent pas, fallback gracieux (warning + skip few-shot).
    gqa_idx = golden_qa_index_path
    gqa_meta = golden_qa_meta_path
    if enable_golden_qa:
        gqa_idx = gqa_idx or DEFAULT_GOLDEN_QA_INDEX
        gqa_meta = gqa_meta or DEFAULT_GOLDEN_QA_META

    return OrientIAPipeline(
        client=client,
        fiches=fiches,
        model=model,
        use_mmr=use_mmr,
        use_intent=use_intent,
        validator=validator,
        use_metadata_filter=use_metadata_filter,
        use_golden_qa=enable_golden_qa,
        golden_qa_index_path=gqa_idx,
        golden_qa_meta_path=gqa_meta,
        enable_post_process=enable_post_process,
        scope_classifier=scope_classifier,
    )


def golden_qa_artifacts_present(
    index_path: str = DEFAULT_GOLDEN_QA_INDEX,
    meta_path: str = DEFAULT_GOLDEN_QA_META,
) -> bool:
    """Helper diagnostic — retourne True si les 2 artefacts Golden QA sont
    présents sur disque, sinon False.

    Utile en démarrage (ex: API FastAPI lazy init) pour décider si on active
    Golden QA ou si on log un warning explicite.
    """
    return Path(index_path).exists() and Path(meta_path).exists()
