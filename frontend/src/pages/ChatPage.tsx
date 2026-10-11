import { useEffect, useState } from "react";
import { ChatWindow } from "../components/ChatWindow";
import {
  checkHealth,
  createReading,
  restartConversation,
  sendConversationMessage,
  startConversation,
} from "../services/api";
import type { ChatMessage, ConnectionStatus, ConversationResponse, Reading } from "../types/chat";

function createId(): string {
  return crypto.randomUUID();
}

function repliesToMessages(replies: string[]): ChatMessage[] {
  return replies.map((text) => ({ id: createId(), role: "assistant", text }));
}

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [inputError, setInputError] = useState("");
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [statusDetail, setStatusDetail] = useState("Checking the local API...");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phase, setPhase] = useState("collect_birth_date");
  const [userId, setUserId] = useState<number | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [sending, setSending] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  async function connect() {
    setStatus("checking");
    setStatusDetail("Checking the local API...");

    try {
      const health = await checkHealth();
      setStatus("connected");
      setStatusDetail(`API connected: ${health.service}`);
      const conversation = await startConversation();
      applyConversation(conversation, true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "The API check failed.";
      setStatus("unreachable");
      setStatusDetail(message);
    }
  }

  function applyConversation(conversation: ConversationResponse, replace: boolean) {
    setSessionId(conversation.session_id);
    setPhase(conversation.state);
    setUserId(conversation.user_id);
    if (replace) {
      setReading(null);
      setAnalyzing(false);
    }
    const incoming = repliesToMessages(conversation.replies);
    setMessages((current) => (replace ? incoming : [...current, ...incoming]));
  }

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        const health = await checkHealth();
        if (cancelled) {
          return;
        }
        setStatus("connected");
        setStatusDetail(`API connected: ${health.service}`);
        const conversation = await startConversation();
        if (cancelled) {
          return;
        }
        setSessionId(conversation.session_id);
        setPhase(conversation.state);
        setUserId(conversation.user_id);
        setReading(null);
        setMessages(repliesToMessages(conversation.replies));
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : "The API check failed.";
        setStatus("unreachable");
        setStatusDetail(message);
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  async function sendMessage() {
    const text = draft.trim();
    if (!text) {
      setInputError("Type a message before sending.");
      return;
    }
    if (!sessionId) {
      setInputError("The conversation has not started yet.");
      return;
    }
    if (sending) {
      return;
    }

    setSending(true);
    setInputError("");
    try {
      const conversation = await sendConversationMessage(sessionId, text);
      const userMessage: ChatMessage = { id: createId(), role: "user", text };
      setMessages((current) => [
        ...current,
        userMessage,
        ...repliesToMessages(conversation.replies),
      ]);
      setSessionId(conversation.session_id);
      setPhase(conversation.state);
      setUserId(conversation.user_id);
      setDraft("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "The message could not be sent.";
      setInputError(message);
    } finally {
      setSending(false);
    }
  }

  async function analyze() {
    if (userId === null || analyzing || sending) {
      return;
    }
    setAnalyzing(true);
    setInputError("");
    try {
      const result = await createReading(userId);
      setReading(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Analysis failed.";
      setInputError(message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function restart() {
    if (sending) {
      return;
    }
    setSending(true);
    setInputError("");
    setDraft("");
    try {
      const conversation = await restartConversation(sessionId);
      applyConversation(conversation, true);
      setStatus("connected");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Restart failed.";
      setInputError(message);
    } finally {
      setSending(false);
    }
  }

  return (
    <ChatWindow
      messages={messages}
      draft={draft}
      inputError={inputError}
      status={status}
      statusDetail={statusDetail}
      sending={sending || analyzing}
      canAnalyze={phase === "confirmed" && userId !== null && reading === null && !analyzing}
      analyzing={analyzing}
      reading={reading}
      onDraftChange={(value) => {
        setDraft(value);
        if (inputError) {
          setInputError("");
        }
      }}
      onSend={() => {
        void sendMessage();
      }}
      onRetry={() => {
        void connect();
      }}
      onRestart={() => {
        void restart();
      }}
      onAnalyze={() => {
        void analyze();
      }}
    />
  );
}
