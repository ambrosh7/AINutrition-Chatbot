"""Quota tests for openai/gpt-oss-120b usage limiter."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.groq_usage import (
    COMPLETION_CAP,
    GPT_OSS_LIMITS,
    MIN_COMPLETION,
    UsageLimiter,
    estimate_messages_tokens,
)
from app.services.llm import LLMUnavailable, _call_groq
from app.config import Settings


def _limiter(tmp_path: Path, clock=None) -> UsageLimiter:
    return UsageLimiter(tmp_path / "usage.json", clock=clock or (lambda: 1_000_000.0))


def test_limits_match_gpt_oss_120b() -> None:
    assert GPT_OSS_LIMITS["requests_per_minute"] == 30
    assert GPT_OSS_LIMITS["requests_per_day"] == 1000
    assert GPT_OSS_LIMITS["tokens_per_minute"] == 8000
    assert GPT_OSS_LIMITS["tokens_per_day"] == 200_000
    assert COMPLETION_CAP == 512
    assert MIN_COMPLETION == 256


def test_refuses_when_minute_request_cap_hit(tmp_path: Path) -> None:
    now = {"t": 1_000_000.0}
    limiter = _limiter(tmp_path, clock=lambda: now["t"])
    for _ in range(30):
        assert limiter.reserve(1) is not None
    assert limiter.completion_cap(100) is None
    now["t"] += 61
    assert limiter.completion_cap(100) is not None


def test_refuses_when_day_request_cap_hit(tmp_path: Path) -> None:
    now = {"t": 1_000_000.0}
    limiter = _limiter(tmp_path, clock=lambda: now["t"])
    for index in range(1000):
        if index and index % 30 == 0:
            now["t"] += 61
        assert limiter.reserve(1) is not None
    assert limiter.reserve(1) is None


def test_refuses_when_minute_token_cap_hit(tmp_path: Path) -> None:
    limiter = _limiter(tmp_path)
    assert limiter.reserve(8000) is not None
    assert limiter.completion_cap(100) is None


def test_refuses_when_day_token_cap_would_be_exceeded(tmp_path: Path) -> None:
    now = {"t": 1_000_000.0}
    limiter = _limiter(tmp_path, clock=lambda: now["t"])
    # 25 * 8000 = 200_000 day tokens, spaced across minutes.
    for _ in range(25):
        assert limiter.reserve(8000) is not None
        now["t"] += 61
    assert limiter.completion_cap(100) is None


def test_settle_replaces_reserved_estimate(tmp_path: Path) -> None:
    limiter = _limiter(tmp_path)
    event = limiter.reserve(7000)
    assert event is not None
    limiter.settle(event, 100)
    assert limiter.reserve(7000) is not None


def test_completion_cap_shrinks_with_prompt_size(tmp_path: Path) -> None:
    limiter = _limiter(tmp_path)
    used = 8000 - (400 + MIN_COMPLETION)
    assert limiter.reserve(used) is not None
    cap = limiter.completion_cap(400)
    assert cap == MIN_COMPLETION


def test_estimate_messages_tokens_grows_with_content() -> None:
    small = estimate_messages_tokens([{"role": "user", "content": "hi"}])
    large = estimate_messages_tokens(
        [{"role": "user", "content": "protein " * 500}]
    )
    assert large > small


def test_call_groq_skips_provider_when_quota_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limiter = _limiter(tmp_path)
    assert limiter.reserve(8000) is not None

    def boom(*_args, **_kwargs):
        raise AssertionError("OpenAI client must not be constructed")

    monkeypatch.setattr("openai.OpenAI", boom)

    settings = Settings(
        model_provider="groq",
        groq_api_key="fake-key",
        groq_model="openai/gpt-oss-120b",
        groq_api_base_url="https://api.groq.com/openai/v1",
        temperature=0.2,
        database_url="sqlite:///:memory:",
        prompt_version="m1-v1",
        allowed_origins=("http://localhost:5173",),
        history_message_limit=20,
    )
    with pytest.raises(LLMUnavailable):
        _call_groq(
            [{"role": "user", "content": "How long does rice keep?"}],
            settings=settings,
            repair=False,
            limiter=limiter,
        )


def test_qwen_model_does_not_use_gpt_oss_limiter(tmp_path: Path) -> None:
    from app.services.llm import _active_limiter

    limiter = _limiter(tmp_path)
    assert limiter.reserve(8000) is not None
    # Even with an exhausted limiter object passed, qwen bypasses gating.
    assert _active_limiter("qwen/qwen3.6-27b", limiter) is None
    assert _active_limiter("openai/gpt-oss-120b", limiter) is limiter
