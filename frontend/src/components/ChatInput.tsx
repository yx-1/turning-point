interface ChatInputProps {
  draft: string;
  error: string;
  sending: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void;
}

export function ChatInput({ draft, error, sending, onDraftChange, onSend }: ChatInputProps) {
  return (
    <form
      className="composer"
      onSubmit={(event) => {
        event.preventDefault();
        onSend();
      }}
    >
      <label className="composer-label" htmlFor="chat-draft">
        Message
      </label>
      <textarea
        id="chat-draft"
        className="composer-input"
        rows={2}
        value={draft}
        placeholder="Type a message"
        disabled={sending}
        onChange={(event) => onDraftChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSend();
          }
        }}
      />
      <button type="submit" className="send-button" disabled={sending}>
        {sending ? "Sending..." : "Send"}
      </button>
      {error ? (
        <p className="composer-error" role="alert">
          {error}
        </p>
      ) : (
        <p className="composer-hint">Enter sends. Shift+Enter adds a new line.</p>
      )}
    </form>
  );
}
