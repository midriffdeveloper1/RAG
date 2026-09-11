import { useEffect } from "react";
import ChatWindow from "./ChatWindow.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";
import { X } from "../common/Icons.jsx";

/**
 * The entire text conversation lives in this dialog once "Chat" is picked —
 * mirrors VoiceCallModal's role for voice. Unlike the voice call, closing
 * this doesn't destroy anything (the conversation is saved and reachable
 * again from the sidebar), so a normal close-X / Escape / backdrop click
 * all work here.
 */
export default function ChatModal({ chat, onClose }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const hasUserMessaged = chat.messages.some((m) => m.role === "user");

  return (
    <div className="modal-overlay chat-modal-overlay" role="dialog" aria-modal="true" aria-label="Chat" onClick={onClose}>
      <div
        className="modal-card wide-modal-card chat-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-card__header chat-modal__header">
          <h2>Chat</h2>
          <button type="button" className="modal-card__close" onClick={onClose} aria-label="Close chat">
            <X size={18} />
          </button>
        </div>

        {chat.isLoadingHistory ? (
          <div className="chat-window chat-window--loading">Loading conversation…</div>
        ) : (
          <ChatWindow messages={chat.messages} isLoading={chat.isLoading} />
        )}

        {!hasUserMessaged && !chat.isLoadingHistory && (
          <SuggestedQuestions onSelect={chat.sendMessage} disabled={chat.isLoading} />
        )}

        {chat.error && <p className="chat-widget__error">{chat.error}</p>}

        <ChatInput onSend={chat.sendMessage} disabled={chat.isLoading || chat.isLoadingHistory} />
      </div>
    </div>
  );
}