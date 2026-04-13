import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    mistral_api_key: str
    anthropic_api_key: str
    onisep_email: str
    onisep_password: str
    onisep_app_id: str
    # Optional: only required for Phase F (7-system benchmark with OpenAI).
    # Empty string when not configured — callers must check before use.
    openai_api_key: str = ""


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _optional(key: str) -> str:
    return os.environ.get(key, "")


def load_config() -> Config:
    load_dotenv()
    return Config(
        mistral_api_key=_require("MISTRAL_API_KEY"),
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        onisep_email=_require("ONISEP_EMAIL"),
        onisep_password=_require("ONISEP_PASSWORD"),
        onisep_app_id=_require("ONISEP_APP_ID"),
        openai_api_key=_optional("OPENAI_API_KEY"),
    )
