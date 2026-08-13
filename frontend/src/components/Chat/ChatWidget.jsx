import { useChat } from "../../hooks/useChat.js";
import ChatWindow from "./ChatWindow.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";

export default function ChatWidget() {
  const { messages, isLoading, error, sendMessage } = useChat();
  const hasUserMessaged = messages.some((m) => m.role === "user");

  return (
    <section className="chat-widget" aria-label="Support chat">
      <ChatWindow messages={messages} isLoading={isLoading} />

      {!hasUserMessaged && (
        <SuggestedQuestions onSelect={sendMessage} disabled={isLoading} />
      )}

      {error && <p className="chat-widget__error">{error}</p>}

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </section>
  );
}
