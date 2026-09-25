type Props = {
  visible: boolean;
};

export function TypingIndicator({ visible }: Props) {
  if (!visible) return null;

  return (
    <div className="typing-row" aria-live="polite" aria-label="Assistant is thinking">
      <div className="typing-dots" aria-hidden>
        <span />
        <span />
        <span />
      </div>
      <span className="typing-label">Analyzing nutrient database…</span>
    </div>
  );
}
