import { useEffect, useState } from "react";
import { useChat } from "../../hooks/useChat.js";
import { useVoiceSession, VOICE_CALL_STATE } from "../../hooks/useVoiceSession.js";
import { deleteChatSession, getPublicChatbotConfig } from "../../services/api.js";
import ChatWindow from "./ChatWindow.jsx";
import ChatInput from "./ChatInput.jsx";
import SuggestedQuestions from "./SuggestedQuestions.jsx";
import VoiceCallModal from "./VoiceCallModal.jsx";
import { MessageSquare, Mic } from "../common/Icons.jsx";

export default function ChatWidget({ sessionId = null, customerEmail, onSessionCreated }) {
  const [voiceSessionId, setVoiceSessionId] = useState(null);

  const textChat = useChat(sessionId, customerEmail, { onSessionCreated });
  const voiceChat = useChat(voiceSessionId, customerEmail, { onSessionCreated: setVoiceSessionId });

  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [bargeInEnabled, setBargeInEnabled] = useState(true);
  useEffect(() => {
    getPublicChatbotConfig()
      .then((config) => {
        setVoiceEnabled(Boolean(config.voice_enabled));
        setBargeInEnabled(config.barge_in_enabled !== false);
      })
      .catch(() => setVoiceEnabled(false));
  }, []);

  const voice = useVoiceSession({
    sessionId: voiceSessionId,
    customerEmail,
    chat: voiceChat,
    onSessionCreated: setVoiceSessionId,
    bargeInEnabled,
  });
  const inCall = voice.callState !== VOICE_CALL_STATE.IDLE;
  const hasUserMessaged = textChat.messages.some((m) => m.role === "user");

  // Every call starts fresh — no "resume" option. When a call ends, its
  // backend session is deleted and the local id cleared, so the next
  // "Start Voice Call" always creates a brand-new conversation.
  const handleEndCall = async () => {
    const endedSessionId = voiceSessionId;
    await voice.endCall();
    setVoiceSessionId(null);
    if (endedSessionId && customerEmail) {
      deleteChatSession(endedSessionId, customerEmail).catch(() => {});
    }
  };

  return (
    <section className="chat-widget" aria-label="Support chat">
      {voiceEnabled && (
        <div className="chat-mode-toggle" role="tablist" aria-label="Chat or voice call">
          <button
            type="button"
            role="tab"
            aria-selected="true"
            className="chat-mode-toggle__btn chat-mode-toggle__btn--active"
            disabled
          >
            <MessageSquare size={15} />
            <span>Chat</span>
          </button>
          <button
            type="button"
            className="chat-mode-toggle__btn"
            onClick={voice.startCall}
            disabled={inCall}
          >
            <Mic size={15} />
            <span>{inCall ? "Call in progress…" : "Start Voice Call"}</span>
          </button>
        </div>
      )}

      {textChat.isLoadingHistory ? (
        <div className="chat-window chat-window--loading">Loading conversation…</div>
      ) : (
        <ChatWindow messages={textChat.messages} isLoading={textChat.isLoading} />
      )}

      {!hasUserMessaged && !textChat.isLoadingHistory && (
        <SuggestedQuestions onSelect={textChat.sendMessage} disabled={textChat.isLoading} />
      )}

      {textChat.error && <p className="chat-widget__error">{textChat.error}</p>}

      <ChatInput onSend={textChat.sendMessage} disabled={textChat.isLoading || textChat.isLoadingHistory} />

      {inCall && (
        <VoiceCallModal
          messages={voiceChat.messages}
          callState={voice.callState}
          error={voice.error}
          micMuted={voice.micMuted}
          speakerMuted={voice.speakerMuted}
          onToggleMic={voice.toggleMic}
          onToggleSpeaker={voice.toggleSpeaker}
          onEndCall={handleEndCall}
        />
      )}
    </section>
  );
}