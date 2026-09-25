"""Sliding-window quotas for Groq ``openai/gpt-oss-120b``.

Limits (do not exceed; refuse the call instead of waiting out a window):

- 30 requests / minute
- 1,000 requests / day
- 8,000 tokens / minute
- 200,000 tokens / day

``qwen/qwen3.6-27b`` is not governed by this file.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT

logger = logging.getLogger(__name__)

GPT_OSS_MODEL = "openai/gpt-oss-120b"
GPT_OSS_LIMITS = {
    "requests_per_minute": 30,
    "requests_per_day": 1000,
    "tokens_per_minute": 8000,
    "tokens_per_day": 200_000,
}
COMPLETION_CAP = 512
MIN_COMPLETION = 256
MINUTE_SECONDS = 60
DAY_SECONDS = 24 * 60 * 60
USAGE_PATH = REPO_ROOT / "data" / "groq-usage.json"


@dataclass
class UsageEvent:
    ts: float
    requests: int
    tokens: int


class UsageLimiter:
    """Persisted sliding windows. A refused call is never sent to Groq."""

    def __init__(
        self,
        path: Path | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._path = path
        self._clock = clock or time.time
        self._lock = threading.Lock()
        self._events = self._load()

    def completion_cap(self, prompt_tokens: int) -> int | None:
        """Return a safe max_completion_tokens, or None if the call must not run."""
        with self._lock:
            self._prune()
            if self._request_room(MINUTE_SECONDS) < 1 or self._request_room(DAY_SECONDS) < 1:
                return None
            room = min(
                self._token_room(MINUTE_SECONDS),
                self._token_room(DAY_SECONDS),
            )
            cap = min(COMPLETION_CAP, room - prompt_tokens)
            if cap < MIN_COMPLETION:
                return None
            return cap

    def reserve(self, tokens: int) -> UsageEvent | None:
        with self._lock:
            self._prune()
            if self._request_room(MINUTE_SECONDS) < 1 or self._request_room(DAY_SECONDS) < 1:
                return None
            if (
                self._token_room(MINUTE_SECONDS) < tokens
                or self._token_room(DAY_SECONDS) < tokens
            ):
                return None
            event = UsageEvent(self._clock(), 1, tokens)
            self._events.append(event)
            self._save()
            return event

    def settle(self, event: UsageEvent, actual_tokens: int | None) -> None:
        if actual_tokens is None:
            return
        with self._lock:
            event.tokens = max(0, actual_tokens)
            self._save()

    def _token_room(self, window: int) -> int:
        used = sum(event.tokens for event in self._in_window(window))
        limit = (
            GPT_OSS_LIMITS["tokens_per_minute"]
            if window == MINUTE_SECONDS
            else GPT_OSS_LIMITS["tokens_per_day"]
        )
        return limit - used

    def _request_room(self, window: int) -> int:
        used = sum(event.requests for event in self._in_window(window))
        limit = (
            GPT_OSS_LIMITS["requests_per_minute"]
            if window == MINUTE_SECONDS
            else GPT_OSS_LIMITS["requests_per_day"]
        )
        return limit - used

    def _in_window(self, window: int) -> list[UsageEvent]:
        cutoff = self._clock() - window
        return [event for event in self._events if event.ts >= cutoff]

    def _prune(self) -> None:
        cutoff = self._clock() - DAY_SECONDS
        self._events = [event for event in self._events if event.ts >= cutoff]

    def _load(self) -> list[UsageEvent]:
        if self._path is None or not self._path.is_file():
            return []
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.error("ignoring unreadable Groq usage file")
            return []
        events: list[UsageEvent] = []
        for item in payload.get("events", []):
            try:
                events.append(
                    UsageEvent(
                        float(item["ts"]),
                        int(item["requests"]),
                        int(item["tokens"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return events

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": GPT_OSS_MODEL,
            "events": [
                {
                    "ts": event.ts,
                    "requests": event.requests,
                    "tokens": event.tokens,
                }
                for event in self._events
            ],
        }
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(self._path)


def estimate_messages_tokens(messages: Sequence[dict[str, Any]]) -> int:
    """Overestimate prompt tokens so a call stays under Groq's tokenizer."""
    text = "".join(str(message.get("content", "")) for message in messages)
    return max(1, (len(text.encode("utf-8")) + 2) // 3) + 32 + 8 * len(messages)


_shared_limiter: UsageLimiter | None = None
_shared_limiter_lock = threading.Lock()


def shared_usage_limiter() -> UsageLimiter:
    global _shared_limiter
    with _shared_limiter_lock:
        if _shared_limiter is None:
            _shared_limiter = UsageLimiter(USAGE_PATH)
        return _shared_limiter


def reset_shared_usage_limiter() -> None:
    """Test helper: drop the process-wide limiter."""
    global _shared_limiter
    with _shared_limiter_lock:
        _shared_limiter = None
