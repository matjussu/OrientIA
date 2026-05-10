"""Tests pour ``src.rewrite.prompts``."""

from __future__ import annotations

import json

from src.rewrite.prompts import (
    FEW_SHOT_EXAMPLES,
    SYSTEM_PROMPT,
    build_messages,
    get_system_prompt,
)


class TestSystemPrompt:
    def test_contains_5_rules(self):
        for rule in ("R1", "R2", "R3", "R4", "R5"):
            assert rule in SYSTEM_PROMPT, f"Missing {rule} in SYSTEM_PROMPT"

    def test_no_youth_language_instruction(self):
        # Anti-pattern : ne PAS demander un ton « jeune » ou « lycéen oral »
        bad_phrases = ("comme un jeune", "argot", "familiarité")
        for phrase in bad_phrases:
            # Soit absent soit explicitement *interdit* dans le prompt
            if phrase in SYSTEM_PROMPT.lower():
                # Doit être dans une formulation négative
                lines = [l for l in SYSTEM_PROMPT.lower().split("\n") if phrase in l]
                assert any(
                    any(neg in l for neg in ("pas d", "pas de", "pas l", "ni "))
                    for l in lines
                ), f"'{phrase}' présent sans négation : {lines}"

    def test_mentions_no_pipe_format(self):
        assert "|" in SYSTEM_PROMPT  # référence au format à éviter
        assert "ancien" in SYSTEM_PROMPT.lower() or "format" in SYSTEM_PROMPT.lower()

    def test_target_length_present(self):
        assert "80" in SYSTEM_PROMPT or "60" in SYSTEM_PROMPT
        assert "250" in SYSTEM_PROMPT or "300" in SYSTEM_PROMPT


class TestFewShot:
    def test_two_examples_minimum(self):
        assert len(FEW_SHOT_EXAMPLES) >= 2

    def test_each_example_has_input_and_output(self):
        for ex in FEW_SHOT_EXAMPLES:
            assert "input" in ex and "output" in ex
            assert len(ex["input"]) > 0
            assert len(ex["output"]) > 0

    def test_example_input_is_valid_json(self):
        for ex in FEW_SHOT_EXAMPLES:
            data = json.loads(ex["input"])
            assert isinstance(data, dict)
            assert "domain" in data

    def test_example_output_no_markdown(self):
        for ex in FEW_SHOT_EXAMPLES:
            assert "**" not in ex["output"]
            assert "##" not in ex["output"]
            assert "|" not in ex["output"]


class TestBuildMessages:
    def test_returns_list_of_messages(self):
        fiche = {"id": "test:1", "domain": "crous", "n_logements": 100}
        msgs = build_messages(fiche)
        assert isinstance(msgs, list)
        assert all("role" in m and "content" in m for m in msgs)

    def test_with_few_shot_includes_examples(self):
        fiche = {"id": "test:1", "domain": "crous"}
        msgs = build_messages(fiche, with_few_shot=True)
        # 2 examples × 2 messages (user + assistant) + 1 final user
        assert len(msgs) == 2 * len(FEW_SHOT_EXAMPLES) + 1
        assert msgs[-1]["role"] == "user"

    def test_without_few_shot_only_user(self):
        fiche = {"id": "test:1", "domain": "crous"}
        msgs = build_messages(fiche, with_few_shot=False)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_user_message_includes_serialized_fiche(self):
        fiche = {"id": "rome:M1402", "domain": "metier_detail", "code_rome": "M1402"}
        msgs = build_messages(fiche, with_few_shot=False)
        content = msgs[0]["content"]
        assert "M1402" in content
        assert "metier_detail" in content

    def test_skip_text_field_in_serialization(self):
        # Le champ `text` source ne doit PAS être passé dans le prompt
        # (c'est ce qu'on veut remplacer)
        fiche = {
            "id": "x",
            "domain": "crous",
            "n": 100,
            "text": "ANCIEN TEXTE QUI POLLUE",
        }
        msgs = build_messages(fiche, with_few_shot=False)
        content = msgs[0]["content"]
        assert "ANCIEN TEXTE QUI POLLUE" not in content


class TestGetSystemPrompt:
    def test_returns_system_prompt(self):
        assert get_system_prompt() == SYSTEM_PROMPT
