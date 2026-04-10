import os
import pytest
from src.config import Config, load_config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral_test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic_test")
    monkeypatch.setenv("ONISEP_EMAIL", "a@b.c")
    monkeypatch.setenv("ONISEP_PASSWORD", "pw")
    monkeypatch.setenv("ONISEP_APP_ID", "app123")

    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.mistral_api_key == "mistral_test"
    assert cfg.anthropic_api_key == "anthropic_test"
    assert cfg.onisep_email == "a@b.c"


def test_load_config_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        load_config()
