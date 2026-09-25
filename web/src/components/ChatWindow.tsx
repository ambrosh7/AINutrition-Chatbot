import { useEffect, useMemo, useState } from "react";
import { createConversation, sendChat } from "../api/client";
import type { ChatTurn } from "../types/chat";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import { SourcesPanel } from "./SourcesPanel";

export function ChatWindow() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [inFlight, setInFlight] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    createConversation()
      .then((id) => {
        if (!cancelled) setConversationId(id);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setBootError(
            error instanceof Error ? error.message : "Could not start a chat."
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedClaims = useMemo(() => {
    const selected = turns.find((turn) => turn.id === selectedId);
    return selected?.role === "assistant" ? selected.claims : undefined;
  }, [selectedId, turns]);

  async function sendMessage(raw: string) {
    const message = raw.trim();
    if (!message || !conversationId || inFlight) return;

    setChatError(null);
    setDraft("");
    const userTurn: ChatTurn = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };
    setTurns((prev) => [...prev, userTurn]);
    setInFlight(true);

    try {
      const response = await sendChat(conversationId, message);
      const assistantTurn: ChatTurn = {
        id: response.meta.message_id,
        role: "assistant",
        content: response.answer,
        declined: response.meta.declined,
        claims: response.claims,
      };
      setTurns((prev) => [...prev, assistantTurn]);
      setSelectedId(assistantTurn.id);
    } catch (error: unknown) {
      setChatError(
        error instanceof Error ? error.message : "Something went wrong."
      );
    } finally {
      setInFlight(false);
    }
  }

  function handleClearSession() {
    if (inFlight) return;
    setTurns([]);
    setSelectedId(null);
    setChatError(null);
    setDraft("");
    setBootError(null);
    setConversationId(null);
    createConversation()
      .then((id) => setConversationId(id))
      .catch((error: unknown) => {
        setBootError(
          error instanceof Error ? error.message : "Could not start a chat."
        );
      });
  }

  const inputDisabled = inFlight || !conversationId || Boolean(bootError);

  return (
    <div className="chat-shell">
      <section className="chat-column">
        <div className="chat-subheader">
          <div className="chat-subheader-left">
            <div className="chat-subheader-icon" aria-hidden>
              <span className="material-symbols-outlined">science</span>
            </div>
            <div className="chat-subheader-copy">
              <div className="chat-subheader-title-row">
                <span className="chat-subheader-title">Nutrition Assistant</span>
                <span className="model-chip">
                  <span className="status-dot" aria-hidden />
                  Model • Verified Data
                </span>
              </div>
              <span className="brand-sub">
                Food science, nutrient profiles & clinical food safety
              </span>
            </div>
          </div>
          <div className="chat-subheader-actions">
            <button
              type="button"
              className="icon-btn"
              title="Clear session"
              disabled={inFlight}
              onClick={handleClearSession}
            >
              <span className="material-symbols-outlined">restart_alt</span>
            </button>
            <button
              type="button"
              className="icon-btn"
              title="Export not available yet"
              disabled
            >
              <span className="material-symbols-outlined">download</span>
            </button>
          </div>
        </div>

        {bootError ? (
          <div className="composer-dock" style={{ paddingBottom: 0 }}>
            <div className="error-banner" role="alert">
              <div className="error-banner-left">
                <span className="material-symbols-outlined">cloud_off</span>
                <p>{bootError}</p>
              </div>
              <span className="error-code">Boot failed</span>
            </div>
          </div>
        ) : null}

        <MessageList
          turns={turns}
          selectedId={selectedId}
          inFlight={inFlight}
          promptsDisabled={inputDisabled}
          onSelect={setSelectedId}
          onPickPrompt={(message) => {
            void sendMessage(message);
          }}
        />

        <MessageInput
          value={draft}
          disabled={inputDisabled}
          error={chatError}
          showSuggestions={turns.length > 0}
          sourcesOpen={sourcesOpen}
          onToggleSources={() => setSourcesOpen((open) => !open)}
          onChange={setDraft}
          onSubmit={() => {
            void sendMessage(draft);
          }}
          onPickSuggestion={(message) => {
            void sendMessage(message);
          }}
        />
      </section>

      <SourcesPanel claims={selectedClaims} mobileOpen={sourcesOpen} />
    </div>
  );
}
