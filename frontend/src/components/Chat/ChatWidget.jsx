import { useEffect, useState } from "react";
import { useChat } from "../../hooks/useChat.js";
import { useVoiceSession, VOICE_CALL_STATE } from "../../hooks/useVoiceSession.js";
import { getPublicChatbotConfig } from "../../services/api.js";
import ChatWindow from "./ChatWindow.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";
import VoiceCallWidget from "./VoiceCallWidget.jsx";
import { MessageSquare, Mic, PhoneCall } from "../common/Icons.jsx";

/**
 * Chat and Voice are two independent conversations (separate session ids),
 * each with its own useChat instance. Switching tabs never ends a call or
 * discards either transcript — a call only ends when the person explicitly
 * clicks "End Call", and the voice session id is kept afterwards so
 * re-opening the Voice tab resumes the same conversation rather than
 * starting over. Both reset on page refresh, or when the sidebar's "New
 * chat" clears them.
 */
export default function ChatWidget({ sessionId = null, customerEmail, onSessionCreated }) {
  const [activeMode, setActiveMode] = useState("chat");
  const [voiceSessionId, setVoiceSessionId] = useState(null);

  const textChat = useChat(sessionId, customerEmail, { onSessionCreated });
  const voiceChat = useChat(voiceSessionId, customerEmail, { onSessionCreated: setVoiceSessionId });

  const [voiceEnabled, setVoiceEnabled] = useState(false);
  useEffect(() => {
    getPublicChatbotConfig()
      .then((config) => setVoiceEnabled(Boolean(config.voice_enabled)))
      .catch(() => setVoiceEnabled(false));
  }, []);

  const voice = useVoiceSession({
    sessionId: voiceSessionId,
    customerEmail,
    chat: voiceChat,
    onSessionCreated: setVoiceSessionId,
  });
  const inCall = voice.callState !== VOICE_CALL_STATE.IDLE;
  const hasVoiceHistory = voiceChat.messages.some((m) => m.role === "user");

  const activeChat = activeMode === "voice" ? voiceChat : textChat;
  const hasUserMessaged = activeChat.messages.some((m) => m.role === "user");

  return (
    <section className="chat-widget" aria-label="Support chat">
      {voiceEnabled && (
        <div className="chat-mode-toggle" role="tablist" aria-label="Chat or voice call">
          <button
            type="button"
            role="tab"
            aria-selected={activeMode === "chat"}
            className={`chat-mode-toggle__btn ${activeMode === "chat" ? "chat-mode-toggle__btn--active" : ""}`}
            onClick={() => setActiveMode("chat")}
          >
            <MessageSquare size={15} />
            <span>Chat</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeMode === "voice"}
            className={`chat-mode-toggle__btn ${activeMode === "voice" ? "chat-mode-toggle__btn--active" : ""}`}
            onClick={() => setActiveMode("voice")}
          >
            <Mic size={15} />
            <span>Voice Call{inCall ? " •" : ""}</span>
          </button>
        </div>
      )}

      {activeChat.isLoadingHistory ? (
        <div className="chat-window chat-window--loading">Loading conversation…</div>
      ) : (
        <ChatWindow messages={activeChat.messages} isLoading={activeChat.isLoading} />
      )}

      {activeMode === "voice" ? (
        inCall ? (
          <VoiceCallWidget callState={voice.callState} error={voice.error} onEndCall={voice.endCall} />
        ) : (
          <div className="voice-call voice-call--idle">
            {voice.error && <p className="voice-call__error">{voice.error}</p>}
            <button type="button" className="voice-call__start-btn" onClick={voice.startCall}>
              <PhoneCall size={16} />
              <span>{hasVoiceHistory ? "Resume Voice Call" : "Start Voice Call"}</span>
            </button>
          </div>
        )
      ) : (
        <>
          {!hasUserMessaged && !activeChat.isLoadingHistory && (
            <SuggestedQuestions onSelect={textChat.sendMessage} disabled={textChat.isLoading} />
          )}

          {textChat.error && <p className="chat-widget__error">{textChat.error}</p>}

          <ChatInput onSend={textChat.sendMessage} disabled={textChat.isLoading || textChat.isLoadingHistory} />
        </>
      )}
    </section>
  );
}