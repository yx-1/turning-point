import { useEffect, useRef, type ReactNode } from "react";
import type { ChatMessage } from "../types/chat";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
  footer?: ReactNode;
  scrollKey?: string;
}

export function MessageList({ messages, footer, scrollKey }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, scrollKey]);

  return (
    <div className="message-list" role="log" aria-live="polite" aria-relevant="additions">
      {messages.length === 0 ? (
        <p className="empty-chat">Starting the conversation...</p>
      ) : (
        messages.map((message) => <MessageBubble key={message.id} message={message} />)
      )}
      {footer}
      <div ref={endRef} />
    </div>
  );
}
