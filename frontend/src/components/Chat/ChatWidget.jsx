import { useChat } from "../../hooks/useChat.js";
import ChatWindow from "./ChatWindow.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";

export default function ChatWidget({ sessionId = null, onSessionCreated }) {
  const { messages, isLoading, isLoadingHistory, error, sendMessage } = useChat(sessionId, {
    onSessionCreated,
  });
  const hasUserMessaged = messages.some((m) => m.role === "user");

  return (
    <section className="chat-widget" aria-label="Support chat">
      {isLoadingHistory ? (
        <div className="chat-window chat-window--loading">Loading conversation…</div>
      ) : (
        <ChatWindow messages={messages} isLoading={isLoading} />
      )}

      {!hasUserMessaged && !isLoadingHistory && (
        <SuggestedQuestions onSelect={sendMessage} disabled={isLoading} />
      )}

      {error && <p className="chat-widget__error">{error}</p>}

      <ChatInput onSend={sendMessage} disabled={isLoading || isLoadingHistory} />
    </section>
  );
}