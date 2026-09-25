import { SUGGESTION_CHIPS } from "./EmptyState";

type Props = {
  value: string;
  disabled: boolean;
  error: string | null;
  showSuggestions: boolean;
  sourcesOpen: boolean;
  onToggleSources: () => void;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onPickSuggestion: (message: string) => void;
};

export function MessageInput({
  value,
  disabled,
  error,
  showSuggestions,
  sourcesOpen,
  onToggleSources,
  onChange,
  onSubmit,
  onPickSuggestion,
}: Props) {
  const charCount = value.length;

  return (
    <div className="composer-dock">
      {error ? (
        <div className="error-banner" role="alert">
          <div className="error-banner-left">
            <span className="material-symbols-outlined">cloud_off</span>
            <p>{error}</p>
          </div>
          <span className="error-code">Request failed</span>
        </div>
      ) : null}

      {showSuggestions ? (
        <div className="suggestion-row">
          {SUGGESTION_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              className="suggestion-chip"
              disabled={disabled}
              onClick={() => onPickSuggestion(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      ) : null}

      <form
        className="composer-box"
        onSubmit={(event) => {
          event.preventDefault();
          if (!disabled && value.trim()) onSubmit();
        }}
      >
        <label className="sr-only" htmlFor="chat-input">
          Message
        </label>
        <textarea
          id="chat-input"
          rows={3}
          value={value}
          disabled={disabled}
          placeholder="Ask about nutrients, chemical stability, food safety, or cooking mechanisms…"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!disabled && value.trim()) onSubmit();
            }
          }}
        />
        <div className="composer-toolbar">
          <div className="composer-tools">
            <button
              type="button"
              className="icon-btn"
              disabled
              title="Attachments arrive in a later milestone"
            >
              <span className="material-symbols-outlined">attach_file</span>
            </button>
            <button
              type="button"
              className="icon-btn"
              disabled
              title="Filters arrive in a later milestone"
            >
              <span className="material-symbols-outlined">tune</span>
            </button>
            <span className="composer-hint">
              Shift+Enter for newline • Enter to submit
            </span>
          </div>
          <div className="composer-send-group">
            <span className="token-count">{charCount} / 2,048</span>
            <button
              type="submit"
              className="send-btn"
              disabled={disabled || !value.trim()}
              aria-label={disabled ? "Sending" : "Send message"}
            >
              <span className="material-symbols-outlined">
                {disabled ? "hourglass_empty" : "arrow_upward"}
              </span>
            </button>
          </div>
        </div>
      </form>

      <button
        type="button"
        className="mobile-sources-toggle"
        onClick={onToggleSources}
      >
        <span className="material-symbols-outlined">menu_book</span>
        {sourcesOpen ? "Hide sources" : "Show sources"}
      </button>
    </div>
  );
}
