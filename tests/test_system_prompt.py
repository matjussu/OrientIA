from src.prompt.system import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_contains_neutrality_rules():
    assert "SecNumEdu" in SYSTEM_PROMPT or "labels officiels" in SYSTEM_PROMPT
    assert "biais marketing" in SYSTEM_PROMPT.lower()


def test_system_prompt_contains_realism_thresholds():
    assert "10" in SYSTEM_PROMPT and "30" in SYSTEM_PROMPT
    assert "taux d'accès" in SYSTEM_PROMPT.lower()


def test_system_prompt_forbids_yes_man():
    assert "tout est possible" in SYSTEM_PROMPT.lower()


def test_build_user_prompt_injects_context():
    context = "FICHE 1: Master Cyber Rennes..."
    question = "Quelles formations cyber ?"
    result = build_user_prompt(context, question)
    assert context in result
    assert question in result
