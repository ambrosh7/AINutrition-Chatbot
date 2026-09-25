"""Unit tests for the Phase 1 response contract."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.response import (
    MAX_MESSAGE_LENGTH,
    ChatRequest,
    ChatResponse,
    Claim,
    Meta,
)


def test_claim_requires_non_empty_text() -> None:
    with pytest.raises(ValidationError):
        Claim(text="", source=None)


def test_claim_source_must_be_null() -> None:
    claim = Claim(text="Protein is a macronutrient.", source=None)
    assert claim.source is None


def test_non_null_source_rejected_until_phase_2_normalization() -> None:
    """Document Phase 2: non-null model sources will be normalized to null.

    Milestone 1 schema only accepts literal null. Phase 2 adds a contract
    guard that forces source=null even when the provider emits a string/URL.
    """
    with pytest.raises(ValidationError):
        Claim.model_validate(
            {"text": "WHO recommends X.", "source": "WHO"}
        )


def test_chat_response_accepts_valid_payload() -> None:
    payload = ChatResponse(
        answer="Cooked rice keeps about 3–4 days in the fridge.",
        claims=[
            Claim(
                text="Cooked rice is often kept 3–4 days refrigerated.",
                source=None,
            )
        ],
        meta=Meta(
            conversation_id=uuid4(),
            message_id=uuid4(),
            declined=False,
            decline_reason=None,
        ),
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["claims"][0]["source"] is None
    assert dumped["meta"]["declined"] is False


def test_chat_response_rejects_missing_claims() -> None:
    with pytest.raises(ValidationError):
        ChatResponse.model_validate(
            {
                "answer": "Some answer",
                "meta": {
                    "conversation_id": str(uuid4()),
                    "message_id": str(uuid4()),
                    "declined": False,
                    "decline_reason": None,
                },
            }
        )


def test_chat_response_rejects_null_claims() -> None:
    with pytest.raises(ValidationError):
        ChatResponse.model_validate(
            {
                "answer": "Some answer",
                "claims": None,
                "meta": {
                    "conversation_id": str(uuid4()),
                    "message_id": str(uuid4()),
                    "declined": False,
                    "decline_reason": None,
                },
            }
        )


def test_chat_response_rejects_empty_answer() -> None:
    with pytest.raises(ValidationError):
        ChatResponse(
            answer="",
            claims=[],
            meta=Meta(
                conversation_id=uuid4(),
                message_id=uuid4(),
                declined=False,
                decline_reason=None,
            ),
        )


def test_chat_response_allows_empty_claims_list() -> None:
    payload = ChatResponse(
        answer="I cannot provide a personal calorie target.",
        claims=[],
        meta=Meta(
            conversation_id=uuid4(),
            message_id=uuid4(),
            declined=True,
            decline_reason="calorie_target",
        ),
    )
    assert payload.claims == []
    assert payload.meta.declined is True


def test_chat_request_rejects_empty_and_whitespace_message() -> None:
    conversation_id = uuid4()
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id=conversation_id, message="")
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id=conversation_id, message="   ")


def test_chat_request_rejects_overlong_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            conversation_id=uuid4(),
            message="x" * (MAX_MESSAGE_LENGTH + 1),
        )


def test_chat_request_trims_message() -> None:
    req = ChatRequest(conversation_id=uuid4(), message="  hello  ")
    assert req.message == "hello"
