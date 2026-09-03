import { useEffect, useState } from "react";
import { useChat } from "../../hooks/useChat.js";
import { useVoiceSession, VOICE_CALL_STATE } from "../../hooks/useVoiceSession.js";
import { getPublicChatbotConfig } from "../../services/api.js";
import ChatWindow from "./ChatWindow.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";
import VoiceCallWidget from "./VoiceCallWidget.jsx";
import { MessageSquare, Mic } from "../common/Icons.jsx";

export default function ChatWidget({ sessionId = null, customerEmail, onSessionCreated }) {
  const chat = useChat(sessionId, customerEmail, { onSessionCreated });
  const { messages, isLoading, isLoadingHistory, error, sendMessage } = chat;
  const hasUserMessaged = messages.some((m) => m.role === "user");

  const [voiceEnabled, setVoiceEnabled] = useState(false);
  useEffect(() => {
    getPublicChatbotConfig()
      .then((config) => setVoiceEnabled(Boolean(config.voice_enabled)))
      .catch(() => setVoiceEnabled(false));
  }, []);

  const voice = useVoiceSession({ sessionId, customerEmail, chat, onSessionCreated });
  const inCall = voice.callState !== VOICE_CALL_STATE.IDLE;

  function switchToChat() {
    if (inCall) voice.endCall();
  }

  function switchToVoice() {
    if (!inCall) voice.startCall();
  }

  return (
    <section className="chat-widget" aria-label="Support chat">
      {voiceEnabled && (
        <div className="chat-mode-toggle" role="tablist" aria-label="Chat or voice call">
          <button
            type="button"
            role="tab"
            aria-selected={!inCall}
            className={`chat-mode-toggle__btn ${!inCall ? "chat-mode-toggle__btn--active" : ""}`}
            onClick={switchToChat}
          >
            <MessageSquare size={15} />
            <span>Chat</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={inCall}
            className={`chat-mode-toggle__btn ${inCall ? "chat-mode-toggle__btn--active" : ""}`}
            onClick={switchToVoice}
          >
            <Mic size={15} />
            <span>Voice Call</span>
          </button>
        </div>
      )}

      {isLoadingHistory ? (
        <div className="chat-window chat-window--loading">Loading conversation…</div>
      ) : (
        <ChatWindow messages={messages} isLoading={isLoading} />
      )}

      {inCall ? (
        <VoiceCallWidget callState={voice.callState} error={voice.error} onEndCall={switchToChat} />
      ) : (
        <>
          {!hasUserMessaged && !isLoadingHistory && (
            <SuggestedQuestions onSelect={sendMessage} disabled={isLoading} />
          )}

          {error && <p className="chat-widget__error">{error}</p>}

          <ChatInput onSend={sendMessage} disabled={isLoading || isLoadingHistory} />
        </>
      )}
    </section>
  );
}
