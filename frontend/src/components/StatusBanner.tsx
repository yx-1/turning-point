import type { ConnectionStatus } from "../types/chat";

interface StatusBannerProps {
  status: ConnectionStatus;
  detail: string;
  onRetry: () => void;
}

export function StatusBanner({ status, detail, onRetry }: StatusBannerProps) {
  return (
    <div className={`status-banner status-${status}`} role="status">
      <p>{detail}</p>
      {status === "unreachable" ? (
        <button type="button" className="text-button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
