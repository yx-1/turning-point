import { Component, type ReactNode } from "react";

interface AppErrorBoundaryProps {
  children: ReactNode;
}

interface AppErrorBoundaryState {
  failed: boolean;
}

/** If a screen throws while rendering, show a recovery message instead of a blank page. */
export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) {
      return this.props.children;
    }

    return (
      <div className="app-shell">
        <header className="app-header">
          <p className="eyebrow">Local prototype</p>
          <h1>Turning Point</h1>
        </header>
        <p className="composer-error" role="alert">
          Something went wrong on this page. Saved profiles are still on this computer.
        </p>
        <button type="button" className="send-button" onClick={() => window.location.reload()}>
          Reload
        </button>
      </div>
    );
  }
}
