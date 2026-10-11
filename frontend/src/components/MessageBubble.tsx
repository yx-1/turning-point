import type { ChatMessage } from "../types/chat";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const label = message.role === "assistant" ? "Turning Point" : "You";

  return (
    <article className={`bubble bubble-${message.role}`}>
      <p className="bubble-label">{label}</p>
      <p className="bubble-text">{message.text}</p>
    </article>
  );
}
