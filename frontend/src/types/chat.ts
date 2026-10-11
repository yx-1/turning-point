export type MessageRole = "assistant" | "user";

export type ConnectionStatus = "checking" | "connected" | "unreachable";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface ConversationResponse {
  session_id: string;
  state: string;
  replies: string[];
  user_id: number | null;
}

export interface Reading {
  user_id: number;
  natal_summary: string;
  time_note: string;
  past_pattern: string;
  future_window: string;
  themes: string[];
  why: string;
  similarities: string;
  preparation: string;
  disclaimer: string;
}
