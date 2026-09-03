import { useCallback, useRef, useState } from "react";
import { startVoiceSession } from "../services/api.js";
import { connectSTT, connectTTS, startMicCapture } from "../realtime/deepgramClient.js";
import { getBrowserId } from "../utils/browserId.js";

export const VOICE_CALL_STATE = {
  IDLE: "idle",
  CONNECTING: "connecting",
  CONNECTED: "connected",
  LISTENING: "listening",
  PROCESSING: "processing",
  SPEAKING: "speaking",
  INTERRUPTED: "interrupted",
  ERROR: "error",
  ENDED: "ended",
};

const SENTENCE_END = /[.!?]\s*$/;

function toWsUrl(relativePath) {
  const apiBase = new URL(
    import.meta.env.VITE_API_BASE_URL || "/api/v1",
    window.location.origin
  );
  const wsProtocol = apiBase.protocol === "https:" ? "wss:" : "ws:";
  // relativePath already includes the /api/v1 prefix from the backend, so
  // resolve it against the API host, not against the full base (which would
  // double up the prefix).
  return `${wsProtocol}//${apiBase.host}${relativePath}`;
}


export function useVoiceSession({ sessionId, customerEmail, chat, onSessionCreated }) {
  const [callState, setCallStateRaw] = useState(VOICE_CALL_STATE.IDLE);
  const [error, setError] = useState(null);
  const callStateRef = useRef(VOICE_CALL_STATE.IDLE);

  const setCallState = useCallback((next) => {
    callStateRef.current = next;
    setCallStateRaw(next);
  }, []);

  const controlSocketRef = useRef(null);
  const sttSocketRef = useRef(null);
  const ttsRef = useRef(null); // { socket, playback }
  const stopMicRef = useRef(null);
  const userMessageIdRef = useRef(null);
  const assistantMessageIdRef = useRef(null);
  const assistantBufferRef = useRef("");
  const ttsSentenceBufferRef = useRef("");

  const cleanup = useCallback(() => {
    stopMicRef.current?.();
    stopMicRef.current = null;
    sttSocketRef.current?.close();
    sttSocketRef.current = null;
    ttsRef.current?.playback.close();
    ttsRef.current?.socket.close();
    ttsRef.current = null;
    controlSocketRef.current?.close();
    controlSocketRef.current = null;
    userMessageIdRef.current = null;
    assistantMessageIdRef.current = null;
    assistantBufferRef.current = "";
    ttsSentenceBufferRef.current = "";
  }, []);

  const speakSentence = useCallback((sentence) => {
    const trimmed = sentence.trim();
    if (!trimmed || !ttsRef.current) return;
    ttsRef.current.socket.send(JSON.stringify({ type: "Speak", text: trimmed }));
    ttsRef.current.socket.send(JSON.stringify({ type: "Flush" }));
  }, []);

  const handleControlEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "assistant.response.started":
          setCallState(VOICE_CALL_STATE.PROCESSING);
          assistantBufferRef.current = "";
          ttsSentenceBufferRef.current = "";
          assistantMessageIdRef.current = chat.appendMessage("assistant", "", { channel: "voice" });
          break;

        case "assistant.text.delta": {
          const delta = event.data?.delta || "";
          assistantBufferRef.current += delta;
          ttsSentenceBufferRef.current += delta;
          if (assistantMessageIdRef.current) {
            chat.updateMessage(assistantMessageIdRef.current, assistantBufferRef.current);
          }
          if (SENTENCE_END.test(ttsSentenceBufferRef.current)) {
            speakSentence(ttsSentenceBufferRef.current);
            ttsSentenceBufferRef.current = "";
          }
          break;
        }

        case "assistant.text.completed": {
          const finalText = event.data?.text || assistantBufferRef.current;
          if (assistantMessageIdRef.current) {
            chat.updateMessage(assistantMessageIdRef.current, finalText);
          }
          if (ttsSentenceBufferRef.current.trim()) {
            speakSentence(ttsSentenceBufferRef.current);
            ttsSentenceBufferRef.current = "";
          }
          assistantMessageIdRef.current = null;
          break;
        }

        case "tool.call.started":
          setCallState(VOICE_CALL_STATE.PROCESSING);
          break;

        case "error":
          setError(event.data?.message || "Something went wrong during the call.");
          if (!event.data?.recoverable) setCallState(VOICE_CALL_STATE.ERROR);
          break;

        case "call.ended":
          setCallState(VOICE_CALL_STATE.ENDED);
          break;

        default:
          break;
      }
    },
    [chat, speakSentence]
  );

  const startCall = useCallback(async () => {
    setError(null);
    setCallState(VOICE_CALL_STATE.CONNECTING);

    let session;
    try {
      session = await startVoiceSession({ sessionId, customerEmail });
    } catch (err) {
      const message =
        err.response?.status === 403
          ? "Voice calling isn't enabled for this business yet."
          : err.response?.status === 503
            ? "Voice calling isn't configured yet — ask an admin to set the Deepgram keys."
            : "Couldn't start the call. Please try again.";
      setError(message);
      setCallState(VOICE_CALL_STATE.ERROR);
      return;
    }

    if (!sessionId && session.conversation_id) {
      onSessionCreated?.(session.conversation_id);
    }

    try {
      const controlUrl = new URL(toWsUrl(session.ws_url));
      controlUrl.searchParams.set("voice_session_id", session.voice_session_id);
      controlUrl.searchParams.set("browser_id", getBrowserId());
      const controlSocket = new WebSocket(controlUrl.toString());
      controlSocketRef.current = controlSocket;

      controlSocket.onmessage = (evt) => handleControlEvent(JSON.parse(evt.data));
      controlSocket.onerror = () => {
        setError("The call connection dropped. Please try again.");
        setCallState(VOICE_CALL_STATE.ERROR);
      };

      await new Promise((resolve, reject) => {
        controlSocket.onopen = resolve;
        controlSocket.addEventListener("error", reject, { once: true });
      });

      const sttSocket = connectSTT(session.stt, session.deepgram_token, {
        onPartial: (text) => {
          if (!userMessageIdRef.current) {
            userMessageIdRef.current = chat.appendMessage("user", text, { channel: "voice" });
          } else {
            chat.updateMessage(userMessageIdRef.current, text);
          }
        },
        onFinal: (text, speechFinal) => {
          if (!userMessageIdRef.current) {
            userMessageIdRef.current = chat.appendMessage("user", text, { channel: "voice" });
          } else {
            chat.updateMessage(userMessageIdRef.current, text);
          }
          if (speechFinal && text.trim()) {
            setCallState(VOICE_CALL_STATE.PROCESSING);
            controlSocket.send(
              JSON.stringify({
                type: "user.transcript.final",
                data: { text: text.trim(), customer_email: customerEmail || null },
              })
            );
            userMessageIdRef.current = null;
          }
        },
        onSpeechStarted: () => {
          // Barge-in: a new user turn always wins over stale assistant audio.
          if (ttsRef.current?.playback) {
            ttsRef.current.playback.interrupt();
          }
          if (callStateRef.current === VOICE_CALL_STATE.SPEAKING) {
            setCallState(VOICE_CALL_STATE.INTERRUPTED);
          } else {
            setCallState(VOICE_CALL_STATE.LISTENING);
          }
        },
        onError: () => setError("Speech recognition hiccuped — please keep talking."),
      });
      sttSocketRef.current = sttSocket;

      ttsRef.current = connectTTS(session.tts, session.deepgram_token, {
        onAudioStarted: () => setCallState(VOICE_CALL_STATE.SPEAKING),
        onAudioCompleted: () => setCallState(VOICE_CALL_STATE.LISTENING),
        onError: () => setError("Voice playback hiccuped."),
      });

      stopMicRef.current = await startMicCapture((pcmFrame) => {
        if (sttSocket.readyState === WebSocket.OPEN) sttSocket.send(pcmFrame);
      });

      setCallState(VOICE_CALL_STATE.LISTENING);
    } catch (err) {
      const message =
        err?.name === "NotAllowedError"
          ? "Microphone access was denied. Please allow it to start a voice call."
          : "Couldn't connect the call. Please try again.";
      setError(message);
      setCallState(VOICE_CALL_STATE.ERROR);
      cleanup();
    }
  }, [sessionId, customerEmail, chat, onSessionCreated, handleControlEvent, cleanup]);

  const endCall = useCallback(() => {
    try {
      controlSocketRef.current?.send(JSON.stringify({ type: "call.end" }));
    } catch {
      // socket may already be closed
    }
    cleanup();
    setCallState(VOICE_CALL_STATE.IDLE);
    chat.refresh();
  }, [cleanup, chat]);

  return { callState, error, startCall, endCall };
}
