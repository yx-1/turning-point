import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { ChatPage } from "./pages/ChatPage";

export default function App() {
  return (
    <AppErrorBoundary>
      <ChatPage />
    </AppErrorBoundary>
  );
}
