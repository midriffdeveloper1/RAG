import { useEffect, useRef } from "react";
import { VOICE_CALL_STATE } from "../../hooks/useVoiceSession.js";
import ChatMessage from "./ChatMessage.jsx";
import { AlertCircle, Loader2, Mic, MicOff, PhoneOff, Volume2, VolumeX } from "../common/Icons.jsx";

const STATE_LABEL = {
  [VOICE_CALL_STATE.CONNECTING]: "Connecting…",
  [VOICE_CALL_STATE.CONNECTED]: "Connected",
  [VOICE_CALL_STATE.LISTENING]: "Listening…",
  [VOICE_CALL_STATE.PROCESSING]: "Thinking…",
  [VOICE_CALL_STATE.SPEAKING]: "Speaking…",
  [VOICE_CALL_STATE.INTERRUPTED]: "Go ahead…",
  [VOICE_CALL_STATE.ERROR]: "Connection issue",
};

/**
 * The entire live voice call — transcript, status, and controls — lives in
 * this dialog while a call is active. It's intentionally separate from the
 * text ChatWindow: voice conversations never appear in the default chat
 * pane, only here.
 */
export default function VoiceCallModal({
  messages,
  callState,
  error,
  micMuted,
  speakerMuted,
  onToggleMic,
  onToggleSpeaker,
  onEndCall,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Ending the call is the only way out — no backdrop-click / Escape
  // dismiss, so an active call is never hung up by accident.
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape") e.preventDefault();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const isListening = callState === VOICE_CALL_STATE.LISTENING || callState === VOICE_CALL_STATE.INTERRUPTED;
  const isSpeaking = callState === VOICE_CALL_STATE.SPEAKING;
  const isBusy = callState === VOICE_CALL_STATE.CONNECTING || callState === VOICE_CALL_STATE.PROCESSING;

  return (
    <div className="modal-overlay voice-modal-overlay" role="dialog" aria-modal="true" aria-label="Voice call">
      <div className="modal-card voice-modal-card">
        <div className="modal-card__header voice-modal__header">
          <h2>Voice Call</h2>
          <span className="voice-modal__status" role="status" aria-live="polite">
            {isBusy && <Loader2 size={14} className="voice-call__spin" />}
            {STATE_LABEL[callState] || "…"}
          </span>
        </div>

        <div className="voice-modal__transcript">
          {messages.length === 0 ? (
            <p className="voice-modal__transcript-empty">The conversation will appear here as you talk.</p>
          ) : (
            messages.map((message) => (
              <ChatMessage key={message.id ?? `${message.role}-${message.content}`} message={message} />
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {error && (
          <p className="voice-call__error">
            <AlertCircle size={14} />
            <span>{error}</span>
          </p>
        )}

        <div className="voice-modal__controls">
          <button
            type="button"
            className={`voice-modal__ctrl-btn ${micMuted ? "voice-modal__ctrl-btn--active" : ""}`}
            onClick={onToggleMic}
            aria-pressed={micMuted}
            aria-label={micMuted ? "Unmute microphone" : "Mute microphone"}
          >
            {micMuted ? <MicOff size={18} /> : <Mic size={18} />}
            <span>{micMuted ? "Unmute" : "Mute"}</span>
          </button>

          <button
            type="button"
            className="voice-modal__end-btn"
            onClick={onEndCall}
            aria-label="End call"
          >
            <PhoneOff size={20} />
          </button>

          <button
            type="button"
            className={`voice-modal__ctrl-btn ${speakerMuted ? "voice-modal__ctrl-btn--active" : ""}`}
            onClick={onToggleSpeaker}
            aria-pressed={speakerMuted}
            aria-label={speakerMuted ? "Turn speaker on" : "Turn speaker off"}
          >
            {speakerMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
            <span>Speaker</span>
          </button>
        </div>

        <div
          className={`voice-modal__indicator ${isListening ? "voice-call__indicator--listening" : ""} ${
            isSpeaking ? "voice-call__indicator--speaking" : ""
          }`}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}