import type { ReactNode } from "react";
import type { ChatMessage, ConnectionStatus, Reading } from "../types/chat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import { ReadingView } from "./ReadingView";
import { StatusBanner } from "./StatusBanner";

interface ChatWindowProps {
  messages: ChatMessage[];
  draft: string;
  inputError: string;
  status: ConnectionStatus;
  statusDetail: string;
  sending: boolean;
  canAnalyze: boolean;
  analyzing: boolean;
  reading: Reading | null;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onRetry: () => void;
  onRestart: () => void;
  onAnalyze: () => void;
}

export function ChatWindow({
  messages,
  draft,
  inputError,
  status,
  statusDetail,
  sending,
  canAnalyze,
  analyzing,
  reading,
  onDraftChange,
  onSend,
  onRetry,
  onRestart,
  onAnalyze,
}: ChatWindowProps) {
  let footer: ReactNode = null;
  let scrollKey = "chat";
  if (analyzing) {
    footer = <p className="analysis-loading">Calculating the local chart and comparing your three events...</p>;
    scrollKey = "analyzing";
  } else if (reading) {
    footer = <ReadingView reading={reading} onStartOver={onRestart} />;
    scrollKey = "reading";
  }
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="title-row">
          <div>
            <p className="eyebrow">Local prototype</p>
            <h1>Turning Point</h1>
          </div>
          <button
            type="button"
            className="restart-button"
            onClick={onRestart}
            disabled={sending}
          >
            Restart
          </button>
        </div>
        <p className="privacy-note">
          The active chat stays in memory on this computer. Confirming saves the profile and
          three events to a local SQLite file. Analysis runs locally after you click Analyze.
        </p>
      </header>
      <StatusBanner status={status} detail={statusDetail} onRetry={onRetry} />
      <main className="chat-panel">
        <MessageList messages={messages} footer={footer} scrollKey={scrollKey} />
        {canAnalyze ? (
          <div className="analyze-bar">
            <button type="button" className="send-button" onClick={onAnalyze} disabled={sending}>
              Analyze
            </button>
            {inputError ? (
              <p className="composer-error" role="alert">
                {inputError}
              </p>
            ) : null}
          </div>
        ) : reading || analyzing ? null : (
          <ChatInput
            draft={draft}
            error={inputError}
            sending={sending}
            onDraftChange={onDraftChange}
            onSend={onSend}
          />
        )}
      </main>
    </div>
  );
}
