"""Chat and conversation routes with scope gate (Phase 4)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.db.session import session_scope
from app.schemas.response import (
    ChatRequest,
    ChatResponse,
    CreateConversationResponse,
    Meta,
)
from app.services import conversation as conversation_service
from app.services.llm import LLMSchemaError, LLMUnavailable, complete
from app.services.prompt import build_messages
from app.services.scope_gate import (
    check_answer_leak,
    decline_response_fields,
    evaluate_scope,
)

router = APIRouter(prefix="/api")


def _declined_chat_response(
    *,
    conversation_id: UUID,
    message_id: UUID,
    answer: str,
    reason: str,
) -> ChatResponse:
    return ChatResponse(
        answer=answer,
        claims=[],
        meta=Meta(
            conversation_id=conversation_id,
            message_id=message_id,
            declined=True,
            decline_reason=reason,
        ),
    )


@router.post("/conversations", response_model=CreateConversationResponse)
def create_conversation() -> CreateConversationResponse:
    with session_scope() as session:
        conversation = conversation_service.create_conversation(session)
        return CreateConversationResponse(conversation_id=UUID(conversation.id))


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: UUID) -> dict:
    with session_scope() as session:
        payload = conversation_service.conversation_to_api(session, conversation_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="conversation not found")
        return payload


@router.post("/chat", response_model=ChatResponse)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    provider_complete = getattr(request.app.state, "llm_complete", None)

    with session_scope() as session:
        existing = conversation_service.get_conversation(session, body.conversation_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="conversation not found")

        history = conversation_service.history_for_llm(session, body.conversation_id)
        decision = evaluate_scope(body.message, history=history)

        if decision.blocked:
            answer, reason = decline_response_fields(decision)
            conversation_service.add_user_message(
                session, body.conversation_id, body.message
            )
            message_id = str(uuid4())
            conversation_service.add_assistant_message(
                session,
                body.conversation_id,
                content=answer,
                claims=[],
                declined=True,
                model=None,
                prompt_version=get_settings().prompt_version,
                message_id=message_id,
            )
            return _declined_chat_response(
                conversation_id=body.conversation_id,
                message_id=UUID(message_id),
                answer=answer,
                reason=reason,
            )

        messages = build_messages(body.message, history=history)

        try:
            result = complete(messages, provider_complete=provider_complete)
        except LLMUnavailable:
            raise HTTPException(
                status_code=503,
                detail="model provider unavailable",
            ) from None
        except LLMSchemaError:
            raise HTTPException(
                status_code=502,
                detail="model returned an unparseable response",
            ) from None

        leak = check_answer_leak(result.answer)
        conversation_service.add_user_message(
            session, body.conversation_id, body.message
        )
        message_id = str(uuid4())

        if leak.blocked:
            answer, reason = decline_response_fields(leak)
            conversation_service.add_assistant_message(
                session,
                body.conversation_id,
                content=answer,
                claims=[],
                declined=True,
                model=result.model,
                prompt_version=result.prompt_version,
                message_id=message_id,
            )
            return _declined_chat_response(
                conversation_id=body.conversation_id,
                message_id=UUID(message_id),
                answer=answer,
                reason=reason,
            )

        conversation_service.add_assistant_message(
            session,
            body.conversation_id,
            content=result.answer,
            claims=result.claims,
            declined=False,
            model=result.model,
            prompt_version=result.prompt_version,
            message_id=message_id,
        )

        return ChatResponse(
            answer=result.answer,
            claims=result.claims,
            meta=Meta(
                conversation_id=body.conversation_id,
                message_id=UUID(message_id),
                declined=False,
                decline_reason=None,
            ),
        )


def empty_message_http_exception(exc: RequestValidationError) -> HTTPException | None:
    """Map empty/whitespace/too-long message validation to HTTP 400.

    Missing ``message`` stays 422 (edge-case.md).
    """
    for err in exc.errors():
        loc = err.get("loc", ())
        if "message" not in loc:
            continue
        if err.get("type") == "missing":
            continue
        return HTTPException(status_code=400, detail=err.get("msg", "invalid message"))
    return None
