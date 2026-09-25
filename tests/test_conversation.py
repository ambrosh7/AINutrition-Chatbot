"""Persistence helpers for conversations."""

from __future__ import annotations

from app.db.session import session_scope
from app.schemas.response import Claim
from app.services import conversation as conversation_service


def test_history_survives_new_session(app) -> None:
    with session_scope() as session:
        conversation = conversation_service.create_conversation(session)
        cid = conversation.id
        conversation_service.add_user_message(session, cid, "First question")
        conversation_service.add_assistant_message(
            session,
            cid,
            content="First answer",
            claims=[Claim(text="First claim", source=None)],
            model="openai/gpt-oss-120b",
            prompt_version="m1-v1",
        )

    with session_scope() as session:
        history = conversation_service.history_for_llm(session, cid)
        assert history == [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ]
        payload = conversation_service.conversation_to_api(session, cid)
        assert payload is not None
        assert payload["messages"][1]["claims"][0]["source"] is None
