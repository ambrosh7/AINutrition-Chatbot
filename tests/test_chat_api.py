"""API tests for Phase 2/3 structured LLM chat (mocked Groq provider)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from app.services.llm import (
    LLMOutput,
    LLMSchemaError,
    LLMUnavailable,
    apply_contract_guard,
    complete,
    parse_model_payload,
)


def _ok_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "answer": "Cooked rice is usually kept about 3–4 days in the fridge.",
        "claims": [
            {
                "text": "Cooked rice is often refrigerated for 3–4 days.",
                "source": None,
            }
        ],
    }
    payload.update(overrides)
    return payload


def _with_mock(client, provider):
    client.app.state.llm_complete = provider
    return client


def test_create_conversation_returns_id(client) -> None:
    first = client.post("/api/conversations")
    second = client.post("/api/conversations")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["conversation_id"] != second.json()["conversation_id"]


def test_chat_valid_structured_payload_returns_200(client) -> None:
    _with_mock(client, lambda messages, repair=False: _ok_payload())
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "message": "How long does cooked rice keep?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["meta"]["declined"] is False
    assert body["meta"]["conversation_id"] == conversation_id
    for claim in body["claims"]:
        assert claim["source"] is None
    assert "sk-" not in response.text.lower()
    assert "api_key" not in response.text.lower()


def test_chat_persists_history_and_passes_prior_turns(client) -> None:
    seen: list[list[dict[str, str]]] = []

    def provider(messages, repair=False):
        seen.append(messages)
        n = len([m for m in messages if m["role"] == "user"])
        return {
            "answer": f"Reply for user turn {n}.",
            "claims": [{"text": f"Turn {n} claim.", "source": None}],
        }

    _with_mock(client, provider)
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    first = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "Remember the word mango."},
    )
    second = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "message": "What word did I ask you to remember?",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    # Second call should include prior user + assistant content.
    second_messages = seen[1]
    roles = [m["role"] for m in second_messages]
    assert roles[0] == "system"
    assert any(m["role"] == "user" and "mango" in m["content"] for m in second_messages)
    assert any(m["role"] == "assistant" for m in second_messages)

    detail = client.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert len(messages) == 4  # user, assistant, user, assistant
    assistant_rows = [m for m in messages if m["role"] == "assistant"]
    assert all(
        claim["source"] is None
        for row in assistant_rows
        for claim in (row["claims"] or [])
    )
    assert assistant_rows[0]["model"] == "openai/gpt-oss-120b"
    assert assistant_rows[0]["prompt_version"]


def test_chat_non_null_source_normalized_to_null(client) -> None:
    def provider(messages, repair=False):
        return {
            "answer": "WHO guidance is often cited for sugar limits.",
            "claims": [
                {"text": "WHO publishes sugar guidance.", "source": "WHO"},
                {
                    "text": "Limits are commonly expressed as percent of energy.",
                    "source": {"url": "https://example.com"},
                },
            ],
        }

    _with_mock(client, provider)
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "Sugar limits?"},
    )
    assert response.status_code == 200
    for claim in response.json()["claims"]:
        assert claim["source"] is None

    detail = client.get(f"/api/conversations/{conversation_id}").json()
    stored = detail["messages"][-1]["claims"]
    assert all(claim["source"] is None for claim in stored)


def test_chat_garbage_then_repair_success(client) -> None:
    calls: list[bool] = []

    def provider(messages, repair=False):
        calls.append(repair)
        if not repair:
            return "not-json-at-all"
        return _ok_payload()

    _with_mock(client, provider)
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "Protein basics?"},
    )
    assert response.status_code == 200
    assert calls == [False, True]


def test_chat_garbage_after_repair_returns_502(client) -> None:
    _with_mock(client, lambda messages, repair=False: "still-not-json")
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "hello"},
    )
    assert response.status_code == 502


def test_chat_provider_unavailable_returns_503(client) -> None:
    def provider(messages, repair=False):
        raise LLMUnavailable("model provider unavailable")

    _with_mock(client, provider)
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "hello"},
    )
    assert response.status_code == 503


def test_chat_empty_message_returns_400(client) -> None:
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "   "},
    )
    assert response.status_code == 400


def test_chat_unknown_conversation_returns_404(client) -> None:
    _with_mock(client, lambda messages, repair=False: _ok_payload())
    response = client.post(
        "/api/chat",
        json={"conversation_id": str(uuid4()), "message": "hello"},
    )
    assert response.status_code == 404


def test_get_unknown_conversation_returns_404(client) -> None:
    response = client.get(f"/api/conversations/{uuid4()}")
    assert response.status_code == 404


def test_disallowed_groq_model_does_not_call_provider(monkeypatch) -> None:
    from app.config import Settings

    monkeypatch.setattr(
        "app.services.llm.get_settings",
        lambda: Settings(
            model_provider="groq",
            groq_api_key="fake-key",
            groq_model="gpt-4o-mini",
            groq_api_base_url="https://api.groq.com/openai/v1",
            temperature=0.2,
            database_url="sqlite:///:memory:",
            prompt_version="m1-v1",
            allowed_origins=("http://localhost:5173",),
            history_message_limit=20,
        ),
    )
    with pytest.raises(LLMUnavailable):
        complete([{"role": "user", "content": "hi"}])


def test_apply_contract_guard_nulls_sources() -> None:
    output = LLMOutput.model_validate(
        {
            "answer": "An apple has calories as a food composition fact.",
            "claims": [{"text": "Apples contain calories.", "source": "USDA"}],
        }
    )
    answer, claims = apply_contract_guard(output)
    assert answer
    assert claims[0].source is None


def test_complete_retries_once_then_raises_schema_error() -> None:
    calls: list[bool] = []

    def provider(messages, repair=False):
        calls.append(repair)
        return "nope"

    with pytest.raises(LLMSchemaError):
        complete([], provider_complete=provider)
    assert calls == [False, True]


def test_parse_model_payload_accepts_dict() -> None:
    parsed = parse_model_payload(_ok_payload())
    assert parsed.answer
    assert parsed.claims[0].source is None
