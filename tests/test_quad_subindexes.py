"""Tests pour les nouvelles méthodes quad sub-indexes du pipeline (étape 5).

Cible :
- _build_quad_subindices : load depuis disque OU rebuild en mémoire
- _retrieve_from_sub_indexes : single-sub-index + multi-sub-index RRF
- Préservation des méthodes existantes (_build_double_subindices intacte)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest

from src.rag.pipeline import (
    OrientIAPipeline,
    QUAD_INDEX_K_PER_SUB,
    QUAD_MANIFEST_DEFAULT_PATH,
)


ROOT = Path(__file__).resolve().parents[1]


# ────────────────────────── Fixtures ──────────────────────────


def _make_test_fiche(idx: int, domain: str | None = None) -> dict:
    """Fabrique une fiche test minimale (champs requis par embeddings.py
    fiche_to_text + cohérent avec le pipeline).
    """
    f: dict = {
        "id": f"test-{idx}",
        "nom": f"Formation Test {idx}",
        "etablissement": f"Étab {idx}",
        "ville": "Paris",
        "region": "ile-de-france",
    }
    if domain:
        f["domain"] = domain
    return f


def _make_test_fiches() -> list[dict]:
    """Mini-corpus test : 8 formations + 4 metiers + 2 stats + 3 aides + 2 exclus."""
    fiches: list[dict] = []
    # 8 formations sans domain
    for i in range(8):
        fiches.append(_make_test_fiche(i))
    # 4 metiers
    for i in range(4):
        f = _make_test_fiche(8 + i, domain="metier")
        fiches.append(f)
    # 2 stats
    for i in range(2):
        f = _make_test_fiche(12 + i, domain="insee_salaire")
        fiches.append(f)
    # 3 aides
    for i in range(3):
        f = _make_test_fiche(14 + i, domain="crous")
        fiches.append(f)
    # 2 exclus retrieval_eligible=False
    for i in range(2):
        f = _make_test_fiche(17 + i, domain="competences_certif")
        f["retrieval_eligible"] = False
        fiches.append(f)
    return fiches


def _make_pipeline_with_index() -> OrientIAPipeline:
    """Pipeline minimal avec un FAISS index de vecteurs aléatoires
    correspondant aux fiches test."""
    fiches = _make_test_fiches()
    np.random.seed(42)
    # Embeddings aléatoires (1024 dims pour cohérence avec Mistral)
    n = len(fiches)
    d = 1024
    embeddings = np.random.randn(n, d).astype("float32")
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)

    client = MagicMock()
    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
    )
    pipeline.index = index
    return pipeline


# ────────────────────────── _build_quad_subindices ──────────────────────────


def test_build_quad_subindices_in_memory_when_no_manifest(tmp_path: Path) -> None:
    """Sans manifest sur disque, rebuild en mémoire à partir de l'index unifié."""
    pipeline = _make_pipeline_with_index()
    # Force un manifest_path inexistant
    fake_manifest = tmp_path / "nonexistent_manifest.json"
    ok = pipeline._build_quad_subindices(manifest_path=fake_manifest)

    assert ok is True
    assert pipeline._quad_indices is not None
    assert pipeline._quad_indices_orig is not None
    # 4 groupes attendus
    assert set(pipeline._quad_indices.keys()) == {
        "formations", "metiers", "statistiques", "aides_territoires"
    }
    # Counts attendus (cf _make_test_fiches : 8 formations, 4 metiers,
    # 2 stats, 3 aides ; les 2 exclus ne sont nulle part)
    assert pipeline._quad_indices["formations"].ntotal == 8
    assert pipeline._quad_indices["metiers"].ntotal == 4
    assert pipeline._quad_indices["statistiques"].ntotal == 2
    assert pipeline._quad_indices["aides_territoires"].ntotal == 3
    # Total partition + exclus = total fiches
    total_partitioned = sum(
        idx.ntotal for idx in pipeline._quad_indices.values()
    )
    assert total_partitioned == len(pipeline.fiches) - 2  # 2 exclus


def test_build_quad_subindices_idempotent() -> None:
    """Appel multiple → 1 seul build (lazy cache)."""
    pipeline = _make_pipeline_with_index()
    fake_manifest = Path("/tmp/nonexistent_xyz_manifest.json")

    pipeline._build_quad_subindices(manifest_path=fake_manifest)
    quad_first = pipeline._quad_indices

    pipeline._build_quad_subindices(manifest_path=fake_manifest)
    quad_second = pipeline._quad_indices
    # Même objet — pas de rebuild
    assert quad_first is quad_second


def test_build_quad_subindices_no_index_returns_false() -> None:
    """Pipeline sans index FAISS → False."""
    pipeline = _make_pipeline_with_index()
    pipeline.index = None
    ok = pipeline._build_quad_subindices(manifest_path=Path("/tmp/nope.json"))
    assert ok is False
    assert pipeline._quad_indices is None


def test_build_quad_subindices_loads_from_disk_when_manifest_present(tmp_path: Path) -> None:
    """Si manifest présent et fichiers sub-index présents → load (pas rebuild)."""
    pipeline = _make_pipeline_with_index()

    # Setup : crée un faux manifest + 4 sub-index files dans tmp_path.
    # On rebuild en mémoire d'abord pour avoir des sub-index réels à
    # sauvegarder, puis on sauvegarde + on crée le manifest, puis on
    # ré-instancie un pipeline frais pour tester le load_from_disk.
    pipeline._build_quad_subindices(manifest_path=tmp_path / "no_such_yet.json")
    assert pipeline._quad_indices is not None

    # Sauvegarde les 4 sub-index dans un sous-dossier mimant la structure
    # repo (manifest dans data/embeddings/, sub-index pareil).
    embeddings_dir = tmp_path / "data" / "embeddings"
    embeddings_dir.mkdir(parents=True)
    manifest_groups: dict[str, dict] = {}
    for name, idx in pipeline._quad_indices.items():
        path = embeddings_dir / f"formations_v7_{name}.index"
        faiss.write_index(idx, str(path))
        manifest_groups[name] = {
            "path": f"data/embeddings/formations_v7_{name}.index",
            "fiches_count": idx.ntotal,
            "orig_indices": pipeline._quad_indices_orig[name],
        }

    manifest_path = embeddings_dir / "formations_partition_manifest.json"
    manifest_data = {
        "version": "test",
        "groups": manifest_groups,
    }
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Pipeline frais → load depuis le manifest
    pipeline2 = _make_pipeline_with_index()
    ok = pipeline2._build_quad_subindices(manifest_path=manifest_path)
    assert ok is True
    assert pipeline2._quad_indices is not None
    # Sanity : counts identiques
    for name in ("formations", "metiers", "statistiques", "aides_territoires"):
        assert pipeline2._quad_indices[name].ntotal == pipeline._quad_indices[name].ntotal


# ────────────────────────── _retrieve_from_sub_indexes ──────────────────────────


def _patch_embed(pipeline: OrientIAPipeline, q_emb: np.ndarray) -> None:
    """Patch embed_texts pour retourner un embedding fixe (déterministe).
    Évite d'appeler le client Mistral (mock)."""
    def _fake_embed(client, texts, **kwargs):
        return [q_emb for _ in texts]

    # Le pipeline.py importe embed_texts en haut, donc on patche le module
    import src.rag.pipeline as pipeline_mod  # noqa: F401
    # En fait `_retrieve_from_sub_indexes` fait `from src.rag.embeddings
    # import embed_texts` localement (lazy) → on patche l'origine.
    import src.rag.embeddings as embeddings_mod
    embeddings_mod.embed_texts = _fake_embed  # type: ignore[assignment]


def test_retrieve_from_sub_indexes_single() -> None:
    """Single sub-index → retrieve standard, results triés par score desc."""
    pipeline = _make_pipeline_with_index()
    pipeline._build_quad_subindices(manifest_path=Path("/tmp/nope.json"))

    np.random.seed(7)
    q_emb = np.random.randn(1024).astype("float32")
    _patch_embed(pipeline, q_emb)

    results = pipeline._retrieve_from_sub_indexes(
        question="test", sub_index_names=["metiers"], k_per_sub=10
    )
    # 4 metiers présents → max 4 results
    assert 1 <= len(results) <= 4
    # Tous les results sont du sub-index metiers
    for r in results:
        assert r["fiche"].get("domain") == "metier"
    # Tri par score décroissant
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    # Format compatible : embedding non-null, score == base_score
    for r in results:
        assert r["embedding"] is not None
        assert r["score"] == r["base_score"]


def test_retrieve_from_sub_indexes_multi_rrf() -> None:
    """Multi sub-indexes → fusion RRF, fiches uniques préservées."""
    pipeline = _make_pipeline_with_index()
    pipeline._build_quad_subindices(manifest_path=Path("/tmp/nope.json"))

    np.random.seed(11)
    q_emb = np.random.randn(1024).astype("float32")
    _patch_embed(pipeline, q_emb)

    results = pipeline._retrieve_from_sub_indexes(
        question="test", sub_index_names=["metiers", "statistiques"], k_per_sub=10
    )
    # Au max 4 metiers + 2 statistiques = 6 fiches uniques
    assert 1 <= len(results) <= 6
    # Domaines mixés possibles (au moins 1 de chaque sub-index si possible)
    domains = {r["fiche"].get("domain") for r in results}
    assert "metier" in domains or "insee_salaire" in domains


def test_retrieve_from_sub_indexes_empty_list() -> None:
    """sub_index_names=[] → retourne []."""
    pipeline = _make_pipeline_with_index()
    pipeline._build_quad_subindices(manifest_path=Path("/tmp/nope.json"))
    results = pipeline._retrieve_from_sub_indexes(
        question="test", sub_index_names=[]
    )
    assert results == []


def test_retrieve_from_sub_indexes_invalid_name_filtered() -> None:
    """Un nom de sub-index invalide est silencieusement filtré (pas d'exception)."""
    pipeline = _make_pipeline_with_index()
    pipeline._build_quad_subindices(manifest_path=Path("/tmp/nope.json"))

    np.random.seed(13)
    q_emb = np.random.randn(1024).astype("float32")
    _patch_embed(pipeline, q_emb)

    # 'hallucinated' inconnu, 'metiers' valide
    results = pipeline._retrieve_from_sub_indexes(
        question="test", sub_index_names=["hallucinated", "metiers"]
    )
    # Doit retourner les results de 'metiers' uniquement
    assert len(results) >= 1
    for r in results:
        assert r["fiche"].get("domain") == "metier"


def test_retrieve_from_sub_indexes_returns_empty_when_quad_unbuildable() -> None:
    """Pipeline sans index FAISS → []."""
    pipeline = _make_pipeline_with_index()
    pipeline.index = None
    results = pipeline._retrieve_from_sub_indexes(
        question="test", sub_index_names=["formations"]
    )
    assert results == []


# ────────────────────────── Préservation méthodes existantes ──────────────────────────


def test_existing_double_subindices_method_still_works() -> None:
    """_build_double_subindices reste fonctionnel (pas cassé par étape 5)."""
    pipeline = _make_pipeline_with_index()
    ok = pipeline._build_double_subindices()
    assert ok is True
    # main : 8 formations sans domain
    assert pipeline._main_subindex is not None
    assert pipeline._main_subindex.ntotal == 8
    # annex : 4 metiers + 2 stats + 3 aides = 9
    assert pipeline._annex_subindex is not None
    assert pipeline._annex_subindex.ntotal == 9


def test_quad_and_double_can_coexist() -> None:
    """Les 2 mécanismes (double + quad) peuvent coexister sur un même
    pipeline — pas d'interaction destructive."""
    pipeline = _make_pipeline_with_index()
    pipeline._build_double_subindices()
    pipeline._build_quad_subindices(manifest_path=Path("/tmp/nope.json"))

    # Double encore présent
    assert pipeline._main_subindex is not None
    assert pipeline._main_subindex.ntotal == 8
    # Quad présent
    assert pipeline._quad_indices is not None
    assert sum(idx.ntotal for idx in pipeline._quad_indices.values()) == 8 + 4 + 2 + 3
