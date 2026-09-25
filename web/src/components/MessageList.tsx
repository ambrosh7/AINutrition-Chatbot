import type { Claim, ChatTurn } from "../types/chat";
import { EmptyState } from "./EmptyState";
import { TypingIndicator } from "./TypingIndicator";

type Props = {
  turns: ChatTurn[];
  selectedId: string | null;
  inFlight: boolean;
  promptsDisabled: boolean;
  onSelect: (id: string) => void;
  onPickPrompt: (message: string) => void;
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function ClaimList({ claims }: { claims: Claim[] }) {
  if (claims.length === 0) return null;

  return (
    <div className="claims-block">
      <div className="claims-header">
        <div className="claims-header-left">
          <span className="material-symbols-outlined">verified</span>
          <span>Extracted Claims & Verification</span>
        </div>
        <span className="claims-count">
          {claims.length} item{claims.length === 1 ? "" : "s"} identified
        </span>
      </div>
      {claims.map((claim, index) => (
        <div key={`${claim.text}-${index}`} className="claim-row">
          <p className="claim-text">{claim.text}</p>
          <span className="claim-source">
            {claim.source == null ? "Source: —" : "Source: Linked"}
          </span>
        </div>
      ))}
    </div>
  );
}

export function MessageList({
  turns,
  selectedId,
  inFlight,
  promptsDisabled,
  onSelect,
  onPickPrompt,
}: Props) {
  if (turns.length === 0 && !inFlight) {
    return (
      <div className="message-scroll">
        <EmptyState disabled={promptsDisabled} onPick={onPickPrompt} />
      </div>
    );
  }

  return (
    <div className="message-scroll" role="log" aria-live="polite">
      {turns.map((turn) => {
        if (turn.role === "user") {
          return (
            <article key={turn.id} className="turn-user">
              <div className="turn-meta">
                <span className="turn-role">Researcher Query</span>
                <span className="turn-time">{formatTime(new Date())}</span>
              </div>
              <div className="bubble-user">
                <p>{turn.content}</p>
              </div>
            </article>
          );
        }

        if (turn.declined) {
          return (
            <article key={turn.id} className="turn-assistant">
              <button
                type="button"
                className={`refusal-card${selectedId === turn.id ? " selected" : ""}`}
                onClick={() => onSelect(turn.id)}
              >
                <div className="refusal-icon" aria-hidden>
                  <span className="material-symbols-outlined">shield</span>
                </div>
                <div className="refusal-body">
                  <div className="refusal-badges">
                    <span className="refusal-badge">Clinical Scope Notice</span>
                    <span className="refusal-protocol">Protocol §4.1</span>
                  </div>
                  <p className="refusal-text">{turn.content}</p>
                </div>
              </button>
            </article>
          );
        }

        return (
          <article key={turn.id} className="turn-assistant">
            <div className="turn-meta turn-meta-assistant">
              <div className="engine-mark" aria-hidden>
                <span className="material-symbols-outlined">nutrition</span>
              </div>
              <span className="turn-role engine">Clinical Engine</span>
              <span className="turn-time">{formatTime(new Date())}</span>
            </div>
            <button
              type="button"
              className={`bubble-assistant${selectedId === turn.id ? " selected" : ""}`}
              onClick={() => onSelect(turn.id)}
            >
              <p className="assistant-body">{turn.content}</p>
              <ClaimList claims={turn.claims ?? []} />
            </button>
          </article>
        );
      })}
      <TypingIndicator visible={inFlight} />
    </div>
  );
}
