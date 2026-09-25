"""Phase 1-compatible chat contract checks with mocked Groq + SQLite."""

from __future__ import annotations

from uuid import uuid4


def _mock(client) -> None:
    client.app.state.llm_complete = lambda messages, repair=False: {
        "answer": "Stubbed answer via mocked Groq.",
        "claims": [
            {
                "text": "Phase 3 tests mock the provider; source stays null.",
                "source": None,
            }
        ],
    }


def test_create_conversation_returns_id(client) -> None:
    first = client.post("/api/conversations")
    second = client.post("/api/conversations")
    assert first.status_code == 200
    assert first.json()["conversation_id"] != second.json()["conversation_id"]


def test_chat_returns_valid_chat_response(client) -> None:
    _mock(client)
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "How long does rice keep?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["meta"]["declined"] is False
    for claim in body["claims"]:
        assert claim["source"] is None


def test_chat_empty_message_returns_400(client) -> None:
    conversation_id = client.post("/api/conversations").json()["conversation_id"]
    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "   "},
    )
    assert response.status_code == 400


def test_chat_unknown_conversation_returns_404(client) -> None:
    _mock(client)
    response = client.post(
        "/api/chat",
        json={"conversation_id": str(uuid4()), "message": "hello"},
    )
    assert response.status_code == 404
