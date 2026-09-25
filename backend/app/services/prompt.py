"""Load the versioned system prompt from disk."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "system.txt"

# Section headings required by Phase 5 / problem statement.
REQUIRED_SECTION_MARKERS: tuple[str, ...] = (
    "Role (what you do)",
    "How you answer",
    "Length",
    "What you will not touch",
    "Uncertainty",
    "Output contract",
)


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    if not _PROMPT_PATH.is_file():
        raise FileNotFoundError(f"system prompt missing: {_PROMPT_PATH}")
    text = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("system prompt file is empty")
    return text


def clear_prompt_cache() -> None:
    load_system_prompt.cache_clear()


def prompt_has_required_sections(text: str | None = None) -> list[str]:
    """Return missing required section markers (empty list = ok)."""
    body = text if text is not None else load_system_prompt()
    return [marker for marker in REQUIRED_SECTION_MARKERS if marker not in body]


def build_messages(
    user_message: str, *, history: list[dict[str, str]] | None = None
) -> list[dict[str, str]]:
    """Assemble chat messages: system prompt + history + new user turn."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": load_system_prompt()}
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages
