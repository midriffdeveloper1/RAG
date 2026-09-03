import { Mic, PhoneOff, Loader2, AlertCircle } from "../common/Icons.jsx";
import { VOICE_CALL_STATE } from "../../hooks/useVoiceSession.js";

const STATE_LABEL = {
  [VOICE_CALL_STATE.IDLE]: "Ready to call",
  [VOICE_CALL_STATE.CONNECTING]: "Connecting…",
  [VOICE_CALL_STATE.CONNECTED]: "Connected",
  [VOICE_CALL_STATE.LISTENING]: "Listening…",
  [VOICE_CALL_STATE.PROCESSING]: "Thinking…",
  [VOICE_CALL_STATE.SPEAKING]: "Speaking…",
  [VOICE_CALL_STATE.INTERRUPTED]: "Go ahead…",
  [VOICE_CALL_STATE.ERROR]: "Connection issue",
  [VOICE_CALL_STATE.ENDED]: "Call ended",
};

export default function VoiceCallWidget({ callState, error, onEndCall }) {
  const isListening = callState === VOICE_CALL_STATE.LISTENING || callState === VOICE_CALL_STATE.INTERRUPTED;
  const isSpeaking = callState === VOICE_CALL_STATE.SPEAKING;
  const isBusy = callState === VOICE_CALL_STATE.CONNECTING || callState === VOICE_CALL_STATE.PROCESSING;
  const hasErrored = callState === VOICE_CALL_STATE.ERROR;

  return (
    <div className="voice-call" role="status" aria-live="polite">
      <div
        className={`voice-call__indicator ${isListening ? "voice-call__indicator--listening" : ""} ${
          isSpeaking ? "voice-call__indicator--speaking" : ""
        }`}
      >
        {isBusy ? <Loader2 size={28} className="voice-call__spin" /> : <Mic size={28} />}
      </div>

      <p className="voice-call__label">{STATE_LABEL[callState] || "…"}</p>

      {error && (
        <p className="voice-call__error">
          <AlertCircle size={14} />
          <span>{error}</span>
        </p>
      )}

      <button type="button" className="voice-call__end-btn" onClick={onEndCall} aria-label="End call">
        <PhoneOff size={16} />
        <span>{hasErrored ? "Back to Chat" : "End Call"}</span>
      </button>
    </div>
  );
}
