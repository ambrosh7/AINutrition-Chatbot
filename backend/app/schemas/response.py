"""Shared request/response contract for /api/chat.

Milestone 1: every claim ``source`` is JSON null. Phase 2 adds a contract
guard that normalizes non-null model output to null before respond + persist.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Soft cap for a single user message (edge-case.md Phase 1).
MAX_MESSAGE_LENGTH = 8000


class Claim(BaseModel):
    """Atomic factual claim. ``source`` is always null in Milestone 1."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1)
    # Literal null only. Non-null provider values are normalized in Phase 2.
    source: Literal[None] = None


class Meta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conversation_id: UUID
    message_id: UUID
    declined: bool = False
    decline_reason: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answer: str = Field(min_length=1)
    claims: list[Claim]
    meta: Meta


class ChatRequest(BaseModel):
    """Body for POST /api/chat. Prefer an explicit conversation create first."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    message: str

    @field_validator("message")
    @classmethod
    def message_must_be_non_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message must not be empty")
        if len(trimmed) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"message must be at most {MAX_MESSAGE_LENGTH} characters"
            )
        return trimmed


class CreateConversationResponse(BaseModel):
    conversation_id: UUID
