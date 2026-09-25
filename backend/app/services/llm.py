"""Structured Groq LLM calls with schema validation and source=null contract guard."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import ALLOWED_GROQ_MODELS, Settings, get_settings
from app.schemas.response import Claim
from app.services.groq_usage import (
    GPT_OSS_MODEL,
    UsageLimiter,
    estimate_messages_tokens,
    shared_usage_limiter,
)

logger = logging.getLogger(__name__)

REPAIR_INSTRUCTION = (
    "Your previous reply was not valid for the required JSON schema. "
    "Return only valid JSON with non-empty string field 'answer' and "
    "array field 'claims' where each item has non-empty 'text' and "
    "'source' set to null."
)

JSON_INSTRUCTION = (
    "Respond with a single JSON object only (no markdown fences) matching: "
    '{"answer": string, "claims": [{"text": string, "source": null}, ...]}.'
)

STRUCTURED_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source": {"type": ["string", "null"]},
                },
                "required": ["text", "source"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answer", "claims"],
    "additionalProperties": False,
}

# Default completion budget when not on the gated gpt-oss model.
DEFAULT_MAX_COMPLETION_TOKENS = 1024


class LLMClaim(BaseModel):
    """Looser claim shape from the provider before the contract guard."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1)
    source: object | None = None


class LLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answer: str = Field(min_length=1)
    claims: list[LLMClaim]


class LLMError(Exception):
    """Base LLM failure."""


class LLMUnavailable(LLMError):
    """Provider missing, auth failure, timeout, quota, or outage → HTTP 503."""


class LLMSchemaError(LLMError):
    """Unparseable structured output after repair → HTTP 502."""


@dataclass(frozen=True)
class LLMResult:
    answer: str
    claims: list[Claim]
    model: str
    temperature: float
    prompt_version: str


class Completer(Protocol):
    def __call__(
        self, messages: list[dict[str, str]], *, repair: bool = False
    ) -> dict[str, Any]: ...


def apply_contract_guard(output: LLMOutput) -> tuple[str, list[Claim]]:
    """Force every claim source to null (Milestone 1 contract)."""
    claims = [Claim(text=claim.text.strip(), source=None) for claim in output.claims]
    claims = [claim for claim in claims if claim.text]
    answer = output.answer.strip()
    if not answer:
        raise LLMSchemaError("model returned an empty answer")
    return answer, claims


def parse_model_payload(raw: dict[str, Any] | str) -> LLMOutput:
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMSchemaError("model returned non-JSON content") from exc
    if not isinstance(raw, dict):
        raise LLMSchemaError("model returned a non-object payload")
    try:
        return LLMOutput.model_validate(raw)
    except ValidationError as exc:
        raise LLMSchemaError("model payload failed schema validation") from exc


def _prepare_messages(
    messages: list[dict[str, str]], *, repair: bool
) -> list[dict[str, str]]:
    call_messages = list(messages)
    if call_messages and call_messages[0].get("role") == "system":
        call_messages[0] = {
            "role": "system",
            "content": f"{call_messages[0]['content']}\n\n{JSON_INSTRUCTION}",
        }
    else:
        call_messages.insert(0, {"role": "system", "content": JSON_INSTRUCTION})
    if repair:
        call_messages.append({"role": "user", "content": REPAIR_INSTRUCTION})
    return call_messages


def _active_limiter(
    model: str, limiter: UsageLimiter | None | object = None
) -> UsageLimiter | None:
    """Return the gpt-oss quota limiter, or None for other models / injected skip."""
    if model != GPT_OSS_MODEL:
        return None
    if limiter is False:
        return None
    if isinstance(limiter, UsageLimiter):
        return limiter
    return shared_usage_limiter()


def _call_groq(
    messages: list[dict[str, str]],
    *,
    settings: Settings,
    repair: bool,
    limiter: UsageLimiter | None | object = None,
) -> dict[str, Any]:
    if settings.model_provider != "groq":
        raise LLMUnavailable("unsupported model provider")
    if not settings.groq_api_key:
        raise LLMUnavailable("model provider is not configured")
    if settings.groq_model not in ALLOWED_GROQ_MODELS:
        logger.error("GROQ_MODEL %r is not allowed; not calling Groq", settings.groq_model)
        raise LLMUnavailable("model provider is not configured")
    if not settings.groq_api_base_url:
        raise LLMUnavailable("model provider is not configured")

    call_messages = _prepare_messages(messages, repair=repair)

    active = _active_limiter(settings.groq_model, limiter)
    reservation = None
    max_completion = DEFAULT_MAX_COMPLETION_TOKENS

    if active is not None:
        prompt_tokens = estimate_messages_tokens(call_messages)
        cap = active.completion_cap(prompt_tokens)
        if cap is None:
            logger.error(
                "openai/gpt-oss-120b quota would be exceeded; not calling Groq"
            )
            raise LLMUnavailable("model provider unavailable")
        max_completion = cap
        reservation = active.reserve(prompt_tokens + max_completion)
        if reservation is None:
            logger.error(
                "openai/gpt-oss-120b quota would be exceeded; not calling Groq"
            )
            raise LLMUnavailable("model provider unavailable")

    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
    except ImportError as exc:
        raise LLMUnavailable("openai package is not installed") from exc

    client = OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_api_base_url,
        timeout=60.0,
    )

    kwargs: dict[str, Any] = {
        "model": settings.groq_model,
        "temperature": settings.temperature,
        "messages": call_messages,
        "response_format": {"type": "json_object"},
        "max_completion_tokens": max_completion,
    }
    if settings.groq_model == GPT_OSS_MODEL:
        kwargs["reasoning_effort"] = "low"

    try:
        completion = client.chat.completions.create(**kwargs)
    except (APITimeoutError, APIConnectionError) as exc:
        raise LLMUnavailable("model provider unavailable") from exc
    except APIStatusError as exc:
        raise LLMUnavailable("model provider unavailable") from exc
    except Exception as exc:  # noqa: BLE001
        raise LLMUnavailable("model provider unavailable") from exc

    if active is not None and reservation is not None:
        actual = None
        usage = getattr(completion, "usage", None)
        if usage is not None:
            total = getattr(usage, "total_tokens", None)
            if isinstance(total, int):
                actual = total
        active.settle(reservation, actual)

    content = completion.choices[0].message.content
    if not content:
        raise LLMSchemaError("model returned an empty message")
    return parse_model_payload(content).model_dump()


def default_provider_complete(
    messages: list[dict[str, str]],
    *,
    repair: bool = False,
    settings: Settings | None = None,
    limiter: UsageLimiter | None | object = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    if cfg.model_provider == "groq":
        return _call_groq(
            messages, settings=cfg, repair=repair, limiter=limiter
        )
    raise LLMUnavailable("unsupported model provider")


def complete(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    provider_complete: Completer | Callable[..., dict[str, Any]] | None = None,
    limiter: UsageLimiter | None | object = None,
) -> LLMResult:
    """Call the model, validate, repair once if needed, apply source=null guard."""
    cfg = settings or get_settings()

    def runner(msgs: list[dict[str, str]], *, repair: bool = False) -> dict[str, Any]:
        if provider_complete is None:
            return default_provider_complete(
                msgs, repair=repair, settings=cfg, limiter=limiter
            )
        try:
            return provider_complete(msgs, repair=repair)
        except TypeError:
            return provider_complete(msgs)  # type: ignore[call-arg]

    logger.info(
        "llm_complete provider=%s model=%s temperature=%s prompt_version=%s",
        cfg.model_provider,
        cfg.groq_model,
        cfg.temperature,
        cfg.prompt_version,
    )

    last_error: Exception | None = None
    for attempt, repair in enumerate((False, True)):
        try:
            raw = runner(messages, repair=repair)
            output = parse_model_payload(raw)
            answer, claims = apply_contract_guard(output)
            return LLMResult(
                answer=answer,
                claims=claims,
                model=cfg.groq_model,
                temperature=cfg.temperature,
                prompt_version=cfg.prompt_version,
            )
        except LLMUnavailable:
            raise
        except LLMSchemaError as exc:
            last_error = exc
            logger.warning("llm_schema_error attempt=%s error=%s", attempt + 1, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = LLMSchemaError(str(exc))
            logger.warning(
                "llm_unexpected_error attempt=%s error=%s", attempt + 1, exc
            )
            continue

    raise LLMSchemaError(
        "model returned unparseable structured output"
    ) from last_error
