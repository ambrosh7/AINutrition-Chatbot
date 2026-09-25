"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Repo root: .../AI Nutrition Chatbot/
REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(REPO_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env")

ALLOWED_GROQ_MODELS = frozenset(
    {
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
    }
)
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_DATABASE_URL = f"sqlite:///{REPO_ROOT / 'data' / 'app.db'}"


@dataclass(frozen=True)
class Settings:
    model_provider: str
    groq_api_key: str
    groq_model: str
    groq_api_base_url: str
    temperature: float
    database_url: str
    prompt_version: str
    allowed_origins: tuple[str, ...]
    history_message_limit: int


def _split_origins(raw: str) -> tuple[str, ...]:
    parts = [part.strip() for part in raw.split(",")]
    return tuple(part for part in parts if part)


def _resolve_database_url(raw: str) -> str:
    value = raw.strip()
    if value.startswith("sqlite:///./"):
        relative = value.removeprefix("sqlite:///./")
        return f"sqlite:///{REPO_ROOT / relative}"
    if value.startswith("sqlite:///") and not value.startswith("sqlite:////"):
        # sqlite:///relative → under repo root unless already absolute-looking
        path_part = value.removeprefix("sqlite:///")
        path = Path(path_part)
        if not path.is_absolute():
            return f"sqlite:///{REPO_ROOT / path_part}"
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()
    return Settings(
        model_provider=os.getenv("MODEL_PROVIDER", "groq").strip().lower(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=model,
        groq_api_base_url=os.getenv(
            "GROQ_API_BASE_URL", DEFAULT_GROQ_BASE_URL
        ).strip().rstrip("/"),
        temperature=float(os.getenv("TEMPERATURE", "0.2")),
        database_url=_resolve_database_url(
            os.getenv("DATABASE_URL", f"sqlite:///./data/app.db")
        ),
        prompt_version=os.getenv("PROMPT_VERSION", "m1-v1").strip(),
        allowed_origins=_split_origins(
            os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            )
        ),
        history_message_limit=int(os.getenv("HISTORY_MESSAGE_LIMIT", "20")),
    )
