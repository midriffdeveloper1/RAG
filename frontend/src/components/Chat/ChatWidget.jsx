import { useEffect, useState } from "react";
import { useChat } from "../../hooks/useChat.js";
import {
  useVoiceSession,
  VOICE_CALL_STATE,
} from "../../hooks/useVoiceSession.js";
import {
  deleteChatSession,
  getPublicChatbotConfig,
} from "../../services/api.js";
import ChatModal from "./ChatModal.jsx";
import ModeChoice from "./ModeChoice.jsx";
import VoiceCallModal from "./VoiceCallModal.jsx";

export default function ChatWidget({
  sessionId = null,
  customerEmail,
  onSessionCreated,
}) {
  const [voiceSessionId, setVoiceSessionId] = useState(null);

  const textChat = useChat(sessionId, customerEmail, {
    onSessionCreated,
  });

  const voiceChat = useChat(voiceSessionId, customerEmail, {
    onSessionCreated: setVoiceSessionId,
    initialMessages: [],
  });

  const [configLoaded, setConfigLoaded] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [bargeInEnabled, setBargeInEnabled] = useState(true);
  const [widgetTitle, setWidgetTitle] = useState("");

  useEffect(() => {
    getPublicChatbotConfig()
      .then((config) => {
        setVoiceEnabled(Boolean(config.voice_enabled));
        setBargeInEnabled(config.barge_in_enabled !== false);
        setWidgetTitle(config.widget_title || "");
      })
      .catch(() => setVoiceEnabled(false))
      .finally(() => setConfigLoaded(true));
  }, []);

  const voice = useVoiceSession({
    sessionId: voiceSessionId,
    customerEmail,
    chat: voiceChat,
    onSessionCreated: setVoiceSessionId,
    bargeInEnabled,
  });

  const inCall = voice.callState !== VOICE_CALL_STATE.IDLE;

  /**
   * Automatically close the voice modal when the voice connection
   * is terminated by the AI/backend/browser.
   *
   * This handles cases where the user does NOT click "End Call".
   */
  useEffect(() => {
    if (mode !== "voice") {
      return;
    }

    if (voice.callState === VOICE_CALL_STATE.IDLE) {
      setVoiceSessionId(null);
      setMode(null);
    }
  }, [voice.callState]);

  const [mode, setMode] = useState(sessionId ? "chat" : null);

  useEffect(() => {
    if (!configLoaded || sessionId || voiceEnabled) {
      return;
    }

    setMode("chat");
  }, [configLoaded, voiceEnabled, sessionId]);

  const handleCloseChat = () => {
    setMode(null);
  };

  const handleEndCall = async () => {
    const endedSessionId = voiceSessionId;

    await voice.endCall();

    setVoiceSessionId(null);

    if (endedSessionId && customerEmail) {
      deleteChatSession(endedSessionId, customerEmail).catch(() => {});
    }

    setMode(null);
  };

  if (!configLoaded && mode === null) {
    return (
      <section
        className="chat-widget chat-widget--loading"
        aria-label="Support chat"
      />
    );
  }

  if (mode === "voice" || inCall) {
    return (
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
    );
  }

  if (mode === "chat") {
    return (
      <ChatModal
        chat={textChat}
        onClose={handleCloseChat}
      />
    );
  }

  return (
    <ModeChoice
      businessName={widgetTitle}
      onChat={() => setMode("chat")}
      onVoice={() => {
        setMode("voice");
        voice.startCall();
      }}
    />
  );
}

