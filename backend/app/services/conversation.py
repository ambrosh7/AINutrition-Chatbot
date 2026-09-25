"""Conversation persistence and history for the chat path."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Conversation, Message
from app.schemas.response import Claim


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_conversation(session: Session) -> Conversation:
    conversation = Conversation()
    session.add(conversation)
    session.flush()
    return conversation


def get_conversation(session: Session, conversation_id: UUID | str) -> Conversation | None:
    return session.get(Conversation, str(conversation_id))


def list_messages(session: Session, conversation_id: UUID | str) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == str(conversation_id))
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(session.scalars(stmt))


def history_for_llm(
    session: Session,
    conversation_id: UUID | str,
    *,
    limit: int | None = None,
) -> list[dict[str, str]]:
    """Prior user/assistant turns for the model (no system rows)."""
    max_messages = limit if limit is not None else get_settings().history_message_limit
    messages = list_messages(session, conversation_id)
    turns: list[dict[str, str]] = []
    for message in messages:
        if message.role not in {"user", "assistant"}:
            continue
        turns.append({"role": message.role, "content": message.content})
    if max_messages > 0 and len(turns) > max_messages:
        turns = turns[-max_messages:]
    return turns


def add_user_message(
    session: Session, conversation_id: UUID | str, content: str
) -> Message:
    conversation = get_conversation(session, conversation_id)
    if conversation is None:
        raise ValueError("conversation not found")
    message = Message(
        conversation_id=str(conversation_id),
        role="user",
        content=content,
        claims_json=None,
        declined=False,
        model=None,
        prompt_version=None,
    )
    conversation.updated_at = _utcnow()
    session.add(message)
    session.flush()
    return message


def add_assistant_message(
    session: Session,
    conversation_id: UUID | str,
    *,
    content: str,
    claims: list[Claim],
    declined: bool = False,
    model: str | None = None,
    prompt_version: str | None = None,
    message_id: str | None = None,
) -> Message:
    conversation = get_conversation(session, conversation_id)
    if conversation is None:
        raise ValueError("conversation not found")
    claims_payload = [{"text": claim.text, "source": None} for claim in claims]
    message = Message(
        conversation_id=str(conversation_id),
        role="assistant",
        content=content,
        claims_json=claims_payload,
        declined=declined,
        model=model,
        prompt_version=prompt_version,
    )
    if message_id:
        message.id = message_id
    conversation.updated_at = _utcnow()
    session.add(message)
    session.flush()
    return message


def conversation_to_api(session: Session, conversation_id: UUID | str) -> dict | None:
    conversation = get_conversation(session, conversation_id)
    if conversation is None:
        return None
    messages = list_messages(session, conversation_id)
    return {
        "conversation_id": conversation.id,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "claims": message.claims_json,
                "declined": message.declined,
                "model": message.model,
                "prompt_version": message.prompt_version,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ],
    }
