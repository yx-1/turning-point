import type { ConversationResponse, HealthResponse, Reading } from "../types/chat";

function localApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "");
  // Local development talks to the API on this computer. A production build
  // is served by that same API, so requests stay on the page's own address.
  if (!configured) {
    return import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
  }
  let url: URL;
  try {
    url = new URL(configured);
  } catch {
    throw new Error("The API address is not a valid local URL.");
  }
  const localHost =
    url.hostname === "127.0.0.1" || url.hostname === "localhost" || url.hostname === "::1";
  if ((url.protocol !== "http:" && url.protocol !== "https:") || !localHost) {
    throw new Error(
      "The API address must stay on this computer. Birth details are not sent to an outside server.",
    );
  }
  return configured;
}

/**
 * Ask the FastAPI process whether it is running.
 * The browser calls GET /health directly. No chat text is sent.
 */
export async function checkHealth(): Promise<HealthResponse> {
  const data = await requestJson(`${localApiBaseUrl()}/health`);
  if (!isHealthResponse(data)) {
    throw new Error("The API returned an unexpected health response.");
  }
  return data;
}

/** Create a new in-memory conversation and return the first questions. */
export async function startConversation(): Promise<ConversationResponse> {
  const data = await requestJson(`${localApiBaseUrl()}/conversation/start`, {
    method: "POST",
  });
  return parseConversation(data);
}

/** Send one user answer. The backend decides the next question. */
export async function sendConversationMessage(
  sessionId: string,
  text: string,
): Promise<ConversationResponse> {
  const data = await requestJson(`${localApiBaseUrl()}/conversation/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  return parseConversation(data);
}

/** Calculate one local reading from a saved profile. */
export async function createReading(userId: number): Promise<Reading> {
  const data = await requestJson(`${localApiBaseUrl()}/users/${userId}/reading`, {
    method: "POST",
  });
  if (!isReading(data)) {
    throw new Error("The API returned an unexpected reading.");
  }
  return data;
}

/** Drop the current session and start the questions again. */
export async function restartConversation(
  sessionId: string | null,
): Promise<ConversationResponse> {
  const data = await requestJson(`${localApiBaseUrl()}/conversation/restart`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  return parseConversation(data);
}

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new Error(
      localApiBaseUrl()
        ? `Cannot reach the API at ${localApiBaseUrl()}. Start the backend, then try again.`
        : "Cannot reach the API. Start the backend, then try again.",
    );
  }

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  try {
    return await response.json();
  } catch {
    throw new Error("The API returned a response this page could not read.");
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
    }
  } catch {
    // The body was not JSON. Fall through to the status code.
  }
  return `The API returned an error (status ${response.status}).`;
}

function parseConversation(value: unknown): ConversationResponse {
  if (!isConversationResponse(value)) {
    throw new Error("The API returned an unexpected conversation response.");
  }
  return {
    session_id: value.session_id,
    state: value.state,
    replies: value.replies,
    user_id: typeof value.user_id === "number" ? value.user_id : null,
  };
}

function isReading(value: unknown): value is Reading {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.user_id === "number" &&
    typeof record.natal_summary === "string" &&
    typeof record.past_pattern === "string" &&
    typeof record.future_window === "string" &&
    Array.isArray(record.themes) &&
    record.themes.every((theme) => typeof theme === "string") &&
    typeof record.why === "string" &&
    typeof record.similarities === "string" &&
    typeof record.preparation === "string" &&
    typeof record.disclaimer === "string"
  );
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return record.status === "ok" && typeof record.service === "string";
}

function isConversationResponse(value: unknown): value is ConversationResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  const userIdOk =
    record.user_id === undefined || record.user_id === null || typeof record.user_id === "number";
  return (
    typeof record.session_id === "string" &&
    typeof record.state === "string" &&
    Array.isArray(record.replies) &&
    record.replies.every((reply) => typeof reply === "string") &&
    userIdOk
  );
}
