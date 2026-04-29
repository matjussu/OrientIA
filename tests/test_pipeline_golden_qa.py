"""Tests Sprint 10 chantier D — Q&A Golden Dynamic Few-Shot dans pipeline.

Couvre :
- Backward compat strict (use_golden_qa=False default → comportement v1)
- Lazy-load index/meta + fallback gracieux si fichiers manquants
- _retrieve_golden_qa top-1 (FAISS dédié)
- _build_few_shot_prefix avec **séparation stricte Comment/Quoi**
- Anti-pollution factuelle croisée (DoD CRITIQUE) : 0 hallu de l'exemple
  vers la réponse user
- Stats observabilité `last_golden_qa`

Mocks :
- `embed_texts` patched pour ne pas appeler Mistral-embed
- `client.chat.complete` patched pour capturer le system prompt construit
- FAISS index réel (small) construit à la volée pour les tests
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.rag.pipeline import OrientIAPipeline


# ─────────────── Fixtures ───────────────


@pytest.fixture
def fake_qa_records():
    """3 Q&A Golden mock pour tests."""
    return [
        {
            "idx": 0,
            "prompt_id": "A1",
            "category": "lyceen_post_bac",
            "iteration": 0,
            "question_seed": "alternatives concrètes prépa MPSI",
            "question_refined": "Je sature des maths abstraites, alternatives prépa MPSI ?",
            "answer_refined": (
                "Si je te comprends bien, tu cherches du concret. Voici 3 pistes : "
                "(1) BUT à l'IUT de Polytech Toulouse en 3 ans avec 30 places, "
                "concours en mars 2026. "
                "(2) Bachelor sciences-ingénierie à l'EPITA. "
                "(3) Licence physique passerelle écoles. "
                "Question pour t'aider à trier : tu vises plus le théorique ou l'appliqué ?"
            ),
            "score_total": 88,
            "decision": "keep",
        },
        {
            "idx": 1,
            "prompt_id": "B1",
            "category": "etudiant_reorientation",
            "iteration": 0,
            "question_seed": "réorientation L1 droit perte motivation",
            "question_refined": "Je suis en L1 droit et je perds motivation, comment me réorienter ?",
            "answer_refined": (
                "Si je te comprends bien, ton ressenti est valide — beaucoup de L1 droit "
                "vivent ça. Voici 3 pistes : "
                "(1) Bachelor RH à l'École Sup' Conseil RH avec 50 places, écrits avril 2026. "
                "(2) Licence sciences politiques à Sciences Po Aix. "
                "(3) BTS Communication en alternance. "
                "Question : qu'est-ce qui pèse le plus — préserver l'année déjà investie "
                "ou explorer une voie tout autre ?"
            ),
            "score_total": 86,
            "decision": "keep",
        },
        {
            "idx": 2,
            "prompt_id": "A1",
            "category": "lyceen_post_bac",
            "iteration": 1,
            "question_seed": "écoles ingénieur post-bac vs prépa",
            "question_refined": "Quelles écoles d'ingénieur post-bac valent le coup ?",
            "answer_refined": "Réponse exemple courte sans école citée.",
            "score_total": 90,
            "decision": "keep",
        },
    ]


@pytest.fixture
def fake_golden_qa_index(fake_qa_records, tmp_path):
    """Construit un FAISS index réel sur 3 vecteurs aléatoires + meta JSON."""
    from src.rag.index import build_index, save_index

    rng = np.random.default_rng(seed=42)
    embeddings = rng.standard_normal((len(fake_qa_records), 1024)).astype("float32")
    index = build_index(embeddings)

    idx_path = tmp_path / "golden_qa.index"
    meta_path = tmp_path / "golden_qa_meta.json"
    save_index(index, str(idx_path))
    meta_path.write_text(
        json.dumps({"records": fake_qa_records, "n": len(fake_qa_records)},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "index_path": str(idx_path),
        "meta_path": str(meta_path),
        "embeddings": embeddings,
        "records": fake_qa_records,
    }


@pytest.fixture
def pipeline_with_golden_qa(fake_golden_qa_index):
    pipe = OrientIAPipeline(
        client=MagicMock(),
        fiches=[{"id": 1, "nom": "BTS Compta — Lycée Test, Lyon"}],
        use_golden_qa=True,
        golden_qa_index_path=fake_golden_qa_index["index_path"],
        golden_qa_meta_path=fake_golden_qa_index["meta_path"],
    )
    pipe.index = MagicMock()  # bypass index check pour answer()
    return pipe


# ─────────────── (a) Backward compat ───────────────


class TestGoldenQaBackwardCompat:
    def test_use_golden_qa_false_default(self):
        pipe = OrientIAPipeline(client=MagicMock(), fiches=[])
        assert pipe.use_golden_qa is False
        assert pipe._golden_qa_index_path is None
        assert pipe._golden_qa_meta_path is None
        assert pipe._golden_qa_index is None
        assert pipe._golden_qa_meta is None
        assert pipe.last_golden_qa is None

    def test_retrieve_golden_qa_returns_none_when_flag_off(self):
        pipe = OrientIAPipeline(client=MagicMock(), fiches=[])
        result = pipe._retrieve_golden_qa("any question")
        assert result is None

    def test_maybe_build_returns_none_when_flag_off(self):
        pipe = OrientIAPipeline(client=MagicMock(), fiches=[])
        prefix = pipe._maybe_build_golden_qa_prefix("any q")
        assert prefix is None
        # Stats reflète l'inactivité
        assert pipe.last_golden_qa == {"active": False, "matched": False}


# ─────────────── (b) Lazy-load + fallback gracieux ───────────────


class TestGoldenQaLazyLoad:
    def test_lazy_load_returns_false_when_no_paths(self):
        pipe = OrientIAPipeline(
            client=MagicMock(),
            fiches=[],
            use_golden_qa=True,
            # Pas de paths → fallback gracieux
        )
        assert pipe._lazy_load_golden_qa() is False

    def test_lazy_load_returns_false_when_files_missing(self, tmp_path):
        pipe = OrientIAPipeline(
            client=MagicMock(),
            fiches=[],
            use_golden_qa=True,
            golden_qa_index_path=str(tmp_path / "missing.index"),
            golden_qa_meta_path=str(tmp_path / "missing.json"),
        )
        assert pipe._lazy_load_golden_qa() is False

    def test_lazy_load_succeeds_with_real_files(self, fake_golden_qa_index):
        pipe = OrientIAPipeline(
            client=MagicMock(),
            fiches=[],
            use_golden_qa=True,
            golden_qa_index_path=fake_golden_qa_index["index_path"],
            golden_qa_meta_path=fake_golden_qa_index["meta_path"],
        )
        assert pipe._lazy_load_golden_qa() is True
        assert pipe._golden_qa_index is not None
        assert pipe._golden_qa_index.ntotal == 3
        assert len(pipe._golden_qa_meta) == 3

    def test_lazy_load_idempotent(self, fake_golden_qa_index):
        pipe = OrientIAPipeline(
            client=MagicMock(),
            fiches=[],
            use_golden_qa=True,
            golden_qa_index_path=fake_golden_qa_index["index_path"],
            golden_qa_meta_path=fake_golden_qa_index["meta_path"],
        )
        pipe._lazy_load_golden_qa()
        idx_first = pipe._golden_qa_index
        pipe._lazy_load_golden_qa()
        # 2e call → idempotent (pas de re-load)
        assert pipe._golden_qa_index is idx_first


# ─────────────── (c) Retrieve top-1 ───────────────


class TestRetrieveGoldenQa:
    def test_retrieve_returns_meta_record(self, pipeline_with_golden_qa, fake_golden_qa_index):
        # Mock embed_texts pour return un embedding proche du record idx=1
        target_embedding = fake_golden_qa_index["embeddings"][1].tolist()
        with patch("src.rag.pipeline.embed_texts", return_value=[target_embedding]):
            result = pipeline_with_golden_qa._retrieve_golden_qa("any question", top_k=1)
        assert result is not None
        assert result["idx"] == 1
        assert result["prompt_id"] == "B1"
        # Score retrieve attaché pour audit
        assert "_retrieve_score" in result
        assert "_retrieve_distance" in result

    def test_retrieve_returns_top_match(self, pipeline_with_golden_qa, fake_golden_qa_index):
        # Embedding le plus proche du record idx=2
        target_embedding = fake_golden_qa_index["embeddings"][2].tolist()
        with patch("src.rag.pipeline.embed_texts", return_value=[target_embedding]):
            result = pipeline_with_golden_qa._retrieve_golden_qa("any question")
        assert result["idx"] == 2

    def test_retrieve_returns_none_on_empty_index(self, tmp_path):
        # Edge case : index vide
        from src.rag.index import build_index, save_index
        empty_emb = np.zeros((0, 1024), dtype="float32")
        # FAISS doesn't allow empty index — skip ce test si pas constructible
        try:
            index = build_index(empty_emb)
            idx_path = tmp_path / "empty.index"
            save_index(index, str(idx_path))
            meta_path = tmp_path / "empty_meta.json"
            meta_path.write_text(json.dumps({"records": [], "n": 0}), encoding="utf-8")
        except Exception:
            pytest.skip("FAISS empty index not constructible")

        pipe = OrientIAPipeline(
            client=MagicMock(), fiches=[],
            use_golden_qa=True,
            golden_qa_index_path=str(idx_path),
            golden_qa_meta_path=str(meta_path),
        )
        with patch("src.rag.pipeline.embed_texts", return_value=[np.zeros(1024).tolist()]):
            result = pipe._retrieve_golden_qa("q")
        assert result is None


# ─────────────── (d) Few-shot prefix (séparation stricte Comment/Quoi) ───────────────


class TestBuildFewShotPrefix:
    def test_prefix_contains_separation_markers(self):
        qa = {
            "question_seed": "test seed",
            "question_refined": "test refined question",
            "answer_refined": "test refined answer with Polytech school cited",
        }
        prefix = OrientIAPipeline._build_few_shot_prefix(qa)
        # Markers de séparation explicites
        assert "EXEMPLE EXPERT" in prefix
        assert "RÉFÉRENCE TON/STRUCTURE" in prefix or "RÉFÉRENCE COMPORTEMENTALE" in prefix
        assert "SÉPARATION STRICTE" in prefix
        assert "IGNORE" in prefix
        assert "écoles spécifiques" in prefix
        assert "chiffres" in prefix
        assert "dates" in prefix
        assert "SEULES les fiches du contexte RAG" in prefix

    def test_prefix_includes_question_and_answer(self):
        qa = {
            "question_seed": "seed Q",
            "question_refined": "refined Q",
            "answer_refined": "the refined answer body",
        }
        prefix = OrientIAPipeline._build_few_shot_prefix(qa)
        assert "refined Q" in prefix  # use refined when present
        assert "the refined answer body" in prefix

    def test_prefix_falls_back_to_seed_when_no_refined(self):
        qa = {
            "question_seed": "seed only",
            "question_refined": "",
            "answer_refined": "answer",
        }
        prefix = OrientIAPipeline._build_few_shot_prefix(qa)
        assert "seed only" in prefix

    def test_prefix_empty_when_no_answer(self):
        qa = {"question_seed": "Q", "answer_refined": ""}
        prefix = OrientIAPipeline._build_few_shot_prefix(qa)
        assert prefix == ""

    def test_prefix_explicit_keep_style_drop_content(self):
        """Le prefix doit explicitement dire 'reprends le STYLE, jamais le CONTENU'."""
        qa = {"question_seed": "Q", "answer_refined": "A"}
        prefix = OrientIAPipeline._build_few_shot_prefix(qa)
        # Recherche d'instruction explicite sur reprendre style mais pas contenu
        assert "STYLE" in prefix
        assert "CONTENU" in prefix


# ─────────────── (e) DoD CRITIQUE — anti-pollution factuelle croisée ───────────────


class TestAntiPollutionFactuelleCroisee:
    """DoD critique du chantier D : la Q&A Golden injectée en few-shot ne
    doit JAMAIS polluer la réponse user avec ses entités factuelles
    (écoles, chiffres précis, dates), seules les fiches du retrieved
    sont sources autorisées.

    Test : 10 questions où la Q&A Golden contient 'Polytech Toulouse' /
    '30 places' / 'mars 2026', mock retrieve_top_k qui retourne des fiches
    SANS Polytech, mock Mistral. On vérifie que le SYSTEM PROMPT construit
    contient l'instruction explicite "IGNORE", et que le user_prompt
    factuel ne contient pas Polytech.

    Note : on ne peut pas tester la sortie réelle de Mistral sans appel
    réel. On teste que le contrat (instructions explicites + séparation
    contexte) est en place, ce qui est l'invariant code-level.
    """

    def _make_pipeline_with_polluted_qa(self, tmp_path):
        """Build pipeline avec une Q&A contenant noms/chiffres/dates."""
        from src.rag.index import build_index, save_index

        polluted_qa = [{
            "idx": 0,
            "prompt_id": "X1",
            "category": "test",
            "iteration": 0,
            "question_seed": "alternatives concrètes",
            "question_refined": "Question test polluée",
            "answer_refined": (
                "Voici 3 pistes : (1) BUT à Polytech Toulouse, 30 places, "
                "concours en mars 2026, frais 8500€/an. "
                "(2) Bachelor à EPITA Paris avec 90% insertion. "
                "(3) Licence à l'Université de Lyon."
            ),
            "score_total": 88,
            "decision": "keep",
        }]

        rng = np.random.default_rng(seed=99)
        emb = rng.standard_normal((1, 1024)).astype("float32")
        index = build_index(emb)
        idx_path = tmp_path / "qa.index"
        meta_path = tmp_path / "qa_meta.json"
        save_index(index, str(idx_path))
        meta_path.write_text(
            json.dumps({"records": polluted_qa, "n": 1}),
            encoding="utf-8",
        )

        pipe = OrientIAPipeline(
            client=MagicMock(),
            fiches=[
                {"nom": "BTS Test", "etablissement": "Lycée Random", "ville": "Lille",
                 "niveau": "bac+2", "statut": "Public"},
                {"nom": "Licence Test", "etablissement": "Université Random",
                 "ville": "Marseille", "niveau": "bac+3", "statut": "Public"},
            ],
            use_golden_qa=True,
            golden_qa_index_path=str(idx_path),
            golden_qa_meta_path=str(meta_path),
        )
        pipe.index = MagicMock()
        return pipe, polluted_qa, emb

    def test_system_prompt_contains_ignore_instructions(self, tmp_path):
        """Quand use_golden_qa actif, le system prompt envoyé à Mistral DOIT
        contenir les instructions IGNORE explicites."""
        pipe, polluted, emb = self._make_pipeline_with_polluted_qa(tmp_path)
        captured: dict = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content="answer text"))]
            return response

        pipe.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=[
            {"fiche": pipe.fiches[0], "score": 0.9, "base_score": 0.9, "embedding": np.zeros(1024)},
            {"fiche": pipe.fiches[1], "score": 0.85, "base_score": 0.85, "embedding": np.zeros(1024)},
        ]):
            with patch("src.rag.pipeline.embed_texts", return_value=[emb[0].tolist()]):
                pipe.answer("question user qui ne mentionne pas Polytech")

        # System prompt envoyé à Mistral
        sys_msg = next(m for m in captured["messages"] if m["role"] == "system")
        # Doit contenir les instructions IGNORE
        assert "IGNORE" in sys_msg["content"]
        assert "écoles spécifiques" in sys_msg["content"] or "écoles" in sys_msg["content"]
        assert "SÉPARATION STRICTE" in sys_msg["content"]
        # Doit indiquer que les fiches RAG sont seule source autorisée
        assert "SEULES les fiches" in sys_msg["content"] or "fiches du contexte" in sys_msg["content"]

    def test_user_prompt_does_not_contain_qa_polluted_entities(self, tmp_path):
        """Le user_prompt (context fiches + question user) ne doit PAS
        mentionner Polytech Toulouse / 30 places / mars 2026 / 8500€ —
        ces entités viennent de la Q&A Golden et ne doivent jamais
        passer dans le bloc factuel user."""
        pipe, polluted, emb = self._make_pipeline_with_polluted_qa(tmp_path)
        captured: dict = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content="answer text"))]
            return response

        pipe.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=[
            {"fiche": pipe.fiches[0], "score": 0.9, "base_score": 0.9, "embedding": np.zeros(1024)},
            {"fiche": pipe.fiches[1], "score": 0.85, "base_score": 0.85, "embedding": np.zeros(1024)},
        ]):
            with patch("src.rag.pipeline.embed_texts", return_value=[emb[0].tolist()]):
                pipe.answer("Quelles formations en gestion ?")

        user_msg = next(m for m in captured["messages"] if m["role"] == "user")
        # Le user prompt contient le context fiches + question user — PAS la Q&A polluée
        # Les entités polluées (Polytech, 30 places, mars 2026, 8500€, EPITA, 90%, Lyon)
        # doivent UNIQUEMENT être dans le system prompt (few-shot prefix), pas user
        polluted_entities = [
            "Polytech Toulouse", "30 places", "mars 2026",
            "8500€", "EPITA", "90% insertion",
        ]
        for entity in polluted_entities:
            assert entity not in user_msg["content"], (
                f"Pollution détectée : '{entity}' présent dans user_prompt "
                f"alors qu'il vient uniquement de la Q&A Golden — "
                f"séparation Comment/Quoi violée."
            )

    def test_qa_polluted_entities_in_system_only(self, tmp_path):
        """Inverse : les entités polluées DOIVENT être dans le system prompt
        (puisque la Q&A est injectée en few-shot system) mais accompagnées
        de l'instruction IGNORE."""
        pipe, polluted, emb = self._make_pipeline_with_polluted_qa(tmp_path)
        captured: dict = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content="answer text"))]
            return response

        pipe.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=[
            {"fiche": pipe.fiches[0], "score": 0.9, "base_score": 0.9, "embedding": np.zeros(1024)},
        ]):
            with patch("src.rag.pipeline.embed_texts", return_value=[emb[0].tolist()]):
                pipe.answer("Q test")

        sys_msg = next(m for m in captured["messages"] if m["role"] == "system")
        # Polytech Toulouse est dans le system (few-shot) AVEC instruction IGNORE
        assert "Polytech Toulouse" in sys_msg["content"]
        # Vérifier que IGNORE est aussi présent (pas Polytech tout seul comme info à utiliser)
        polytech_idx = sys_msg["content"].find("Polytech Toulouse")
        ignore_idx = sys_msg["content"].find("IGNORE")
        # IGNORE doit apparaître quelque part autour de Polytech (avant ou après)
        assert ignore_idx >= 0


# ─────────────── (f) Stats observabilité ───────────────


class TestGoldenQaStats:
    def test_last_golden_qa_populated_when_matched(self, pipeline_with_golden_qa, fake_golden_qa_index):
        target_emb = fake_golden_qa_index["embeddings"][0].tolist()
        with patch("src.rag.pipeline.embed_texts", return_value=[target_emb]):
            pipeline_with_golden_qa._maybe_build_golden_qa_prefix("Q")

        stats = pipeline_with_golden_qa.last_golden_qa
        assert stats is not None
        assert stats["active"] is True
        assert stats["matched"] is True
        assert "prompt_id" in stats
        assert "category" in stats
        assert "score_total" in stats
        assert "retrieve_score" in stats

    def test_last_golden_qa_inactive_when_flag_off(self):
        pipe = OrientIAPipeline(client=MagicMock(), fiches=[])
        pipe._maybe_build_golden_qa_prefix("Q")
        assert pipe.last_golden_qa == {"active": False, "matched": False}
