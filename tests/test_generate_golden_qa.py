"""Tests unitaires Sprint 9-data — scripts/generate_golden_qa_v1.py.

Couvre :
- Parsing YAML config (51 prompts, fields requis)
- Decision policy (keep / flag / drop boundaries 85 / 70)
- Detection 429 / rate limit (stderr + stdout patterns)
- Backoff exponential + retry stats (consecutive_429, total_*, lock thread-safe)
- Stop condition >10 consecutive 429
- Checkpointing skip déjà fait via ThreadSafeJsonlAppender
- Append concurrent thread-safe (no race condition)
- parse_json_safe robuste (markdown fence, préambule, JSON imbriqué)
- 4-phase orchestration end-to-end avec subprocess mocké
- CLI parsing + filtering --filter-prompt-id

Mocks :
- subprocess.run remplacé par MagicMock pour zero appel real `claude --print`
- _shutdown_event reset entre tests
"""
from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Import via path manipulation (le script est dans scripts/, pas un module pip-installable)
import sys
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_golden_qa_v1 as gqa  # noqa: E402


# ───────────────────── Fixtures ─────────────────────


@pytest.fixture(autouse=True)
def reset_shutdown_event():
    """Reset le shutdown event entre tests (sinon test pollue le suivant)."""
    gqa._shutdown_event.clear()
    yield
    gqa._shutdown_event.clear()


@pytest.fixture
def yaml_path():
    return Path(__file__).resolve().parents[1] / "config" / "diverse_prompts_50.yaml"


@pytest.fixture
def sample_prompt_config():
    return {
        "id": "TEST",
        "category": "test",
        "axe_couvert": 1,
        "persona": "test persona",
        "context": "test context",
        "constraints": {"region": "variable"},
        "tone": "tutoiement",
        "sources_priority": ["ONISEP", "Parcoursup"],
        "questions_seed": ["seed q 1", "seed q 2", "seed q 3"],
    }


@pytest.fixture
def cfg_minimal(tmp_path):
    return gqa.GenerateConfig(
        yaml_config_path=Path("config/diverse_prompts_50.yaml"),
        output_jsonl=tmp_path / "out.jsonl",
        parallel=1,
        rate_limit_delay=0.0,
        max_retries=2,
    )


# ───────────────────── YAML config loader ─────────────────────


class TestYAMLConfig:
    def test_yaml_loads_51_prompts(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert len(data["prompts"]) == 51

    def test_yaml_metadata_consistent(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        meta = data["metadata"]
        assert meta["total_prompts"] == 51
        assert meta["iterations_per_prompt"] == 20
        assert meta["total_qa_target"] == 1020

    def test_each_prompt_has_required_fields(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        required = {"id", "category", "axe_couvert", "persona", "context",
                    "constraints", "tone", "sources_priority", "questions_seed"}
        for p in data["prompts"]:
            missing = required - set(p.keys())
            assert not missing, f"Prompt {p.get('id', '?')} missing: {missing}"

    def test_each_prompt_has_5_or_6_seeds(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        for p in data["prompts"]:
            n = len(p["questions_seed"])
            assert 5 <= n <= 6, f"Prompt {p['id']} has {n} seeds (expected 5-6)"

    def test_test_set_v3_q1_in_a2(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        a2 = next(p for p in data["prompts"] if p["id"] == "A2")
        seeds_text = " ".join(a2["questions_seed"])
        assert "11 de moyenne" in seeds_text and "HEC" in seeds_text

    def test_test_set_v3_q5_in_b1(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        b1 = next(p for p in data["prompts"] if p["id"] == "B1")
        seeds_text = " ".join(b1["questions_seed"])
        assert "L2 droit" in seeds_text and "informatique" in seeds_text

    def test_g_category_3_new_profiles(self, yaml_path):
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        g_prompts = [p for p in data["prompts"] if p["id"].startswith("G")]
        assert len(g_prompts) == 3
        assert {p["id"] for p in g_prompts} == {"G1", "G2", "G3"}


# ───────────────────── Decision policy ─────────────────────


class TestDecisionPolicy:
    def test_score_85_keeps(self):
        assert gqa.decision_from_score(85) == "keep"

    def test_score_84_flags(self):
        assert gqa.decision_from_score(84) == "flag"

    def test_score_70_flags(self):
        assert gqa.decision_from_score(70) == "flag"

    def test_score_69_drops(self):
        assert gqa.decision_from_score(69) == "drop"

    def test_score_100_keeps(self):
        assert gqa.decision_from_score(100) == "keep"

    def test_score_0_drops(self):
        assert gqa.decision_from_score(0) == "drop"


# ───────────────────── Rate limit detection ─────────────────────


class TestRateLimitDetection:
    @pytest.mark.parametrize("text", [
        "Error: rate limit exceeded",
        "HTTP 429 Too Many Requests",
        "quota exceeded for this period",
        "Too Many Requests",
        "rate-limit hit",
        "rate_limit",
        # Claude Max plan signatures (patterns ajoutés post-incident dry-run v2
        # quand le quota a hit avec message "You're out of extra usage · resets 5:40pm")
        "You're out of extra usage · resets 5:40pm (Europe/Paris)",
        "out of usage",
        "Approaching usage limit",
        "5-hour limit reached",
        "monthly limit reached",
        "resets at 17h00",
        "resets 5:40pm",
    ])
    def test_detects_rate_limit_in_stderr(self, text):
        assert gqa.is_rate_limit_error(text, "") is True

    @pytest.mark.parametrize("text", [
        "Error: rate limit exceeded",
        "HTTP 429 Too Many Requests",
    ])
    def test_detects_rate_limit_in_stdout(self, text):
        assert gqa.is_rate_limit_error("", text) is True

    @pytest.mark.parametrize("text", [
        "Connection refused",
        "Internal server error 500",
        "timeout after 300s",
        "",
    ])
    def test_does_not_false_positive_on_other_errors(self, text):
        assert gqa.is_rate_limit_error(text, text) is False


# ───────────────────── RetryStats thread-safe ─────────────────────


class TestRetryStats:
    def test_record_success_resets_consecutive_429(self):
        s = gqa.RetryStats()
        s.record_429()
        s.record_429()
        s.record_429()
        s.record_success()
        assert s.consecutive_429 == 0
        assert s.total_429 == 3
        assert s.total_success == 1

    def test_record_429_returns_consecutive_count(self):
        s = gqa.RetryStats()
        assert s.record_429() == 1
        assert s.record_429() == 2
        assert s.record_429() == 3

    def test_thread_safety_under_concurrent_writes(self):
        s = gqa.RetryStats()
        n_threads = 10
        n_increments = 100

        def worker():
            for _ in range(n_increments):
                s.record_success()

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert s.total_success == n_threads * n_increments


# ───────────────────── parse_json_safe ─────────────────────


class TestParseJsonSafe:
    def test_parses_clean_json(self):
        assert gqa.parse_json_safe('{"a": 1}') == {"a": 1}

    def test_strips_markdown_json_fence(self):
        assert gqa.parse_json_safe('```json\n{"a": 1}\n```') == {"a": 1}

    def test_strips_bare_markdown_fence(self):
        assert gqa.parse_json_safe('```\n{"a": 1}\n```') == {"a": 1}

    def test_extracts_json_with_preamble(self):
        text = 'Voici la réponse : {"score_total": 90, "decision_recommandée": "keep"}'
        result = gqa.parse_json_safe(text)
        assert result is not None
        assert result["score_total"] == 90

    def test_returns_none_on_invalid(self):
        assert gqa.parse_json_safe("not json at all") is None

    def test_returns_none_on_empty(self):
        assert gqa.parse_json_safe("") is None
        assert gqa.parse_json_safe(None) is None


# ───────────────────── ThreadSafeJsonlAppender ─────────────────────


class TestThreadSafeJsonlAppender:
    def test_append_writes_jsonl_line(self, tmp_path):
        path = tmp_path / "out.jsonl"
        appender = gqa.ThreadSafeJsonlAppender(path)
        appender.append({"prompt_id": "A1", "iteration": 0, "score": 90})
        content = path.read_text(encoding="utf-8")
        assert content.strip() == '{"prompt_id": "A1", "iteration": 0, "score": 90}'

    def test_existing_keys_returns_set_after_writes(self, tmp_path):
        path = tmp_path / "out.jsonl"
        appender = gqa.ThreadSafeJsonlAppender(path)
        appender.append({"prompt_id": "A1", "iteration": 0})
        appender.append({"prompt_id": "A1", "iteration": 1})
        appender.append({"prompt_id": "B2", "iteration": 0})
        keys = appender.existing_keys()
        assert keys == {("A1", 0), ("A1", 1), ("B2", 0)}

    def test_existing_keys_skip_invalid_json_lines(self, tmp_path):
        path = tmp_path / "out.jsonl"
        path.write_text(
            '{"prompt_id": "A1", "iteration": 0}\n'
            'INVALID JSON LINE\n'
            '{"prompt_id": "A2", "iteration": 0}\n',
            encoding="utf-8",
        )
        appender = gqa.ThreadSafeJsonlAppender(path)
        keys = appender.existing_keys()
        assert keys == {("A1", 0), ("A2", 0)}

    def test_existing_keys_empty_for_new_file(self, tmp_path):
        path = tmp_path / "out.jsonl"
        appender = gqa.ThreadSafeJsonlAppender(path)
        assert appender.existing_keys() == set()

    def test_concurrent_append_no_corruption(self, tmp_path):
        path = tmp_path / "out.jsonl"
        appender = gqa.ThreadSafeJsonlAppender(path)
        n_threads = 10
        n_writes = 50

        def worker(tid):
            for i in range(n_writes):
                appender.append({"prompt_id": f"T{tid}", "iteration": i})

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Lecture : tous les writes doivent parser proprement (pas de ligne tronquée)
        with path.open("r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == n_threads * n_writes


# ───────────────────── Subprocess wrapper + retry ─────────────────────


class TestCallClaudeSubprocess:
    def test_returns_stdout_on_success(self):
        mock_result = MagicMock(stdout="response text", stderr="", returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            stdout, stderr, rc = gqa.call_claude_subprocess("test prompt")
        assert stdout == "response text"
        assert rc == 0

    def test_returns_timeout_marker_on_subprocess_timeout(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 300)):
            stdout, stderr, rc = gqa.call_claude_subprocess("test", timeout_s=300)
        assert rc == -1
        assert "timeout" in stderr.lower()

    def test_returns_filenotfound_marker_when_cli_missing(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            stdout, stderr, rc = gqa.call_claude_subprocess("test")
        assert rc == -2
        assert "not found" in stderr.lower()

    def test_passes_allowed_tools_flag(self):
        mock_result = MagicMock(stdout="ok", stderr="", returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            gqa.call_claude_subprocess("p", allowed_tools=["WebSearch", "WebFetch"])
        cmd = mock_run.call_args.args[0]
        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert cmd[idx + 1] == "WebSearch,WebFetch"

    def test_passes_model_flag(self):
        mock_result = MagicMock(stdout="ok", stderr="", returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            gqa.call_claude_subprocess("p", model="claude-opus-4-7")
        cmd = mock_run.call_args.args[0]
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4-7"


class TestCallClaudeWithRetry:
    def test_success_on_first_call(self, cfg_minimal):
        retry_stats = gqa.RetryStats()
        with patch.object(gqa, "call_claude_subprocess", return_value=("response", "", 0)):
            result = gqa.call_claude_with_retry("test", cfg_minimal, retry_stats)
        assert result == "response"
        assert retry_stats.total_success == 1

    def test_retries_on_429_then_succeeds(self, cfg_minimal):
        retry_stats = gqa.RetryStats()
        responses = [
            ("", "rate limit exceeded", 1),
            ("", "rate limit exceeded", 1),
            ("ok finally", "", 0),
        ]
        with patch.object(gqa, "call_claude_subprocess", side_effect=responses):
            result = gqa.call_claude_with_retry("test", cfg_minimal, retry_stats)
        assert result == "ok finally"
        assert retry_stats.total_429 == 2
        assert retry_stats.total_success == 1
        assert retry_stats.consecutive_429 == 0  # reset après success

    def test_raises_after_max_retries_on_other_error(self, cfg_minimal):
        retry_stats = gqa.RetryStats()
        responses = [("", "weird error", 1)] * (cfg_minimal.max_retries + 1)
        with patch.object(gqa, "call_claude_subprocess", side_effect=responses):
            with pytest.raises(RuntimeError, match="failed after"):
                gqa.call_claude_with_retry("test", cfg_minimal, retry_stats)
        assert retry_stats.total_other_errors >= 1

    def test_stop_condition_on_too_many_consecutive_429(self, cfg_minimal):
        retry_stats = gqa.RetryStats()
        # Pré-charger consecutive_429 à 10 pour déclencher la stop condition au prochain 429
        for _ in range(10):
            retry_stats.record_429()
        with patch.object(gqa, "call_claude_subprocess",
                          return_value=("", "rate limit", 1)):
            with pytest.raises(RuntimeError, match="Stop condition"):
                gqa.call_claude_with_retry("test", cfg_minimal, retry_stats)

    def test_dry_run_no_subprocess_returns_fake(self, cfg_minimal):
        """En mode dry-run, subprocess n'est jamais appelé et le helper
        fake renvoie une réponse pseudo-cohérente selon le schema détecté
        dans le prompt (markers `"score_total"` et `"scores_par_axe"`
        → critique fake JSON, autres patterns → autres fake responses)."""
        cfg_minimal.dry_run_no_subprocess = True
        retry_stats = gqa.RetryStats()
        # Prompt contenant les markers de schema critique
        critique_prompt = (
            'Évalue cette Q&A.\n'
            'Output JSON STRICT :\n'
            '{"score_total": <int>, "scores_par_axe": {...}, ...}'
        )
        with patch.object(gqa, "call_claude_subprocess") as mock:
            result = gqa.call_claude_with_retry(critique_prompt, cfg_minimal, retry_stats)
        # subprocess JAMAIS appelé en mode dry-run
        mock.assert_not_called()
        # Result doit être un JSON parseable contenant score_total
        parsed = json.loads(result)
        assert "score_total" in parsed
        assert isinstance(parsed["score_total"], int)


# ───────────────────── Phase 2 prompt content (anti-régression patch v2) ─────


class TestPhase2DraftPromptContent:
    """Vérifie que le prompt Phase 2 inclut les directives critiques :
    anti-chiffres non sourcés (modif Matteo msg 2807, post-dryrun v1) +
    lisibilité mobile obligatoire (250-350 mots, bullets, sauts ligne).

    Stratégie test : mock `call_claude_with_retry`, capture le prompt
    construit par `phase2_draft`, asserte présence des marqueurs.
    """

    def test_prompt_contains_interdiction_stricte_chiffres(
        self, sample_prompt_config, cfg_minimal
    ):
        retry_stats = gqa.RetryStats()
        captured: dict = {}

        def fake_call(prompt, cfg, stats, allowed_tools=None):
            captured["prompt"] = prompt
            return '{"question": "Q", "answer": "A"}'

        with patch.object(gqa, "call_claude_with_retry", side_effect=fake_call):
            gqa.phase2_draft(
                sample_prompt_config,
                "research result text",
                sample_prompt_config["questions_seed"][0],
                cfg_minimal,
                retry_stats,
            )

        assert "INTERDICTION STRICTE de chiffres précis" in captured["prompt"]
        # Sample des exemples qualitatif → vérifier au moins 1 transformation
        assert "→" in captured["prompt"]
        assert "registre qualitatif obligatoire" in captured["prompt"]
        # Justification anti-marker estimation (raison du durcissement)
        assert "Mistral en inférence finale peut perdre le marker" in captured["prompt"]

    def test_prompt_contains_lisibilite_mobile_obligatoire(
        self, sample_prompt_config, cfg_minimal
    ):
        retry_stats = gqa.RetryStats()
        captured: dict = {}

        def fake_call(prompt, cfg, stats, allowed_tools=None):
            captured["prompt"] = prompt
            return '{"question": "Q", "answer": "A"}'

        with patch.object(gqa, "call_claude_with_retry", side_effect=fake_call):
            gqa.phase2_draft(
                sample_prompt_config,
                "research result text",
                sample_prompt_config["questions_seed"][0],
                cfg_minimal,
                retry_stats,
            )

        assert "LISIBILITÉ MOBILE OBLIGATOIRE" in captured["prompt"]
        assert "smartphone" in captured["prompt"]
        # Limite mots explicit (250-350 max)
        assert "250-350 mots" in captured["prompt"]
        # Bullet points obligatoires + sauts ligne respiration
        assert "BULLET POINTS COURTS" in captured["prompt"]
        assert "Bloc texte massif INTERDIT" in captured["prompt"]


# ───────────────────── 4-phase orchestration end-to-end ─────────────────


class TestGenerateQaOrchestration:
    def test_generate_qa_returns_record_with_required_fields(
        self, sample_prompt_config, cfg_minimal
    ):
        cfg_minimal.dry_run_no_subprocess = True
        retry_stats = gqa.RetryStats()
        rec = gqa.generate_qa(sample_prompt_config, 0, cfg_minimal, retry_stats)
        assert rec["prompt_id"] == "TEST"
        assert rec["iteration"] == 0
        assert "research_sources_text" in rec
        assert "draft" in rec
        assert "critique" in rec
        assert "final_qa" in rec
        assert rec["score_total"] == 90  # fake helper renvoie 90
        assert rec["decision"] == "keep"
        assert rec["error"] is None
        assert rec["elapsed_s"] >= 0

    def test_generate_qa_iterates_seeds_modulo(
        self, sample_prompt_config, cfg_minimal
    ):
        """iteration_idx % len(seeds) → on tourne sur les seeds"""
        cfg_minimal.dry_run_no_subprocess = True
        retry_stats = gqa.RetryStats()
        seeds = sample_prompt_config["questions_seed"]
        rec0 = gqa.generate_qa(sample_prompt_config, 0, cfg_minimal, retry_stats)
        rec3 = gqa.generate_qa(sample_prompt_config, 3, cfg_minimal, retry_stats)  # back to seed 0
        assert rec0["question_seed"] == seeds[0]
        assert rec3["question_seed"] == seeds[0]  # 3 % 3 == 0

    def test_generate_qa_handles_pipeline_error_gracefully(
        self, sample_prompt_config, cfg_minimal
    ):
        retry_stats = gqa.RetryStats()
        with patch.object(gqa, "phase1_research", side_effect=RuntimeError("research crashed")):
            rec = gqa.generate_qa(sample_prompt_config, 0, cfg_minimal, retry_stats)
        assert rec["error"] is not None
        assert "research crashed" in rec["error"]
        assert rec["decision"] == "drop"
        assert rec["score_total"] == 0


# ───────────────────── build_jobs + filter ─────────────────


class TestBuildJobs:
    def test_filter_prompt_id_returns_only_matching(self, cfg_minimal):
        yaml_data = {
            "prompts": [
                {"id": "A1", "questions_seed": ["q"]},
                {"id": "A2", "questions_seed": ["q"]},
            ],
            "metadata": {"iterations_per_prompt": 5},
        }
        cfg_minimal.filter_prompt_id = "A2"
        jobs = gqa.build_jobs(yaml_data, cfg_minimal)
        assert all(p["id"] == "A2" for p, _i in jobs)
        assert len(jobs) == 5  # 1 prompt × 5 iters

    def test_filter_prompt_id_raises_on_unknown_id(self, cfg_minimal):
        yaml_data = {
            "prompts": [{"id": "A1", "questions_seed": ["q"]}],
            "metadata": {"iterations_per_prompt": 5},
        }
        cfg_minimal.filter_prompt_id = "Z99"
        with pytest.raises(ValueError, match="Aucun prompt"):
            gqa.build_jobs(yaml_data, cfg_minimal)

    def test_max_iterations_overrides_metadata(self, cfg_minimal):
        yaml_data = {
            "prompts": [{"id": "A1", "questions_seed": ["q"]}],
            "metadata": {"iterations_per_prompt": 20},
        }
        cfg_minimal.max_iterations = 3
        jobs = gqa.build_jobs(yaml_data, cfg_minimal)
        assert len(jobs) == 3

    def test_target_caps_total_jobs(self, cfg_minimal):
        yaml_data = {
            "prompts": [{"id": "A1", "questions_seed": ["q"]},
                        {"id": "A2", "questions_seed": ["q"]}],
            "metadata": {"iterations_per_prompt": 10},
        }
        cfg_minimal.target = 7
        jobs = gqa.build_jobs(yaml_data, cfg_minimal)
        assert len(jobs) == 7
