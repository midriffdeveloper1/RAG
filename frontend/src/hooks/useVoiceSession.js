import { useCallback, useRef, useState } from "react";
import { startVoiceSession } from "../services/api.js";
import { connectSTT, connectTTS, startMicCapture, waitForSocketOpen } from "../realtime/deepgramClient.js";
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
};

const SENTENCE_END = /[.!?]\s*$/;
const MIN_BARGE_IN_CHARS = 2;

function toWsUrl(relativePath) {
  const apiBase = new URL(import.meta.env.VITE_API_BASE_URL || "/api/v1", window.location.origin);
  const wsProtocol = apiBase.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${apiBase.host}${relativePath}`;
}


export function useVoiceSession({ sessionId, customerEmail, chat, onSessionCreated, bargeInEnabled = true }) {
  const [callState, setCallStateRaw] = useState(VOICE_CALL_STATE.IDLE);
  const [error, setError] = useState(null);
  const [micMuted, setMicMutedRaw] = useState(false);
  const [speakerMuted, setSpeakerMutedRaw] = useState(false);
  const callStateRef = useRef(VOICE_CALL_STATE.IDLE);
  const micMutedRef = useRef(false);

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
  const pendingBargeInRef = useRef(false);
  const pendingSpeechRef = useRef([]);
  const finalizedTranscriptRef = useRef("");

  const cleanup = useCallback(async () => {
    if (stopMicRef.current) {
      await stopMicRef.current().catch(() => {});
      stopMicRef.current = null;
    }
    sttSocketRef.current?.closeForCleanup?.();
    sttSocketRef.current = null;
    if (ttsRef.current) {
      await ttsRef.current.playback.close().catch(() => {});
      ttsRef.current.socket.closeForCleanup?.();
      ttsRef.current = null;
    }
    controlSocketRef.current?.close(1000, "Client cleanup");
    controlSocketRef.current = null;

    userMessageIdRef.current = null;
    assistantMessageIdRef.current = null;
    assistantBufferRef.current = "";
    ttsSentenceBufferRef.current = "";
    pendingBargeInRef.current = false;
    finalizedTranscriptRef.current = "";
    pendingSpeechRef.current = [];
    micMutedRef.current = false;
    setMicMutedRaw(false);
    setSpeakerMutedRaw(false);
  }, []);

  /** Mic mute — the mic keeps capturing (avoids re-negotiating the device),
   * we just stop forwarding frames to STT while muted. */
  const toggleMic = useCallback(() => {
    micMutedRef.current = !micMutedRef.current;
    setMicMutedRaw(micMutedRef.current);
  }, []);

  /** Loudspeaker mute — silences assistant audio without pausing the call. */
  const toggleSpeaker = useCallback(() => {
    setSpeakerMutedRaw((prev) => {
      const next = !prev;
      ttsRef.current?.playback?.setMuted(next);
      return next;
    });
  }, []);

  const speakSentence = useCallback((sentence) => {
    const text = sentence.trim();
    if (!text) return;
    const socket = ttsRef.current?.socket;
    if (socket?.readyState !== WebSocket.OPEN) {
      // TTS isn't connected yet (e.g. the call-start greeting arrives
      // before setup finishes) — queue it, flushed once the socket opens.
      pendingSpeechRef.current.push(text);
      return;
    }
    socket.send(JSON.stringify({ type: "Speak", text }));
    socket.send(JSON.stringify({ type: "Flush" }));
  }, []);

  const handleControlEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "session.created":
        case "call.started":
          setCallState(VOICE_CALL_STATE.CONNECTED);
          break;

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

        default:
          break;
      }
    },
    [chat, speakSentence, setCallState]
  );

  const startCall = useCallback(async () => {
    if (callStateRef.current !== VOICE_CALL_STATE.IDLE) return;

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
            ? "Voice calling isn't configured yet — ask an admin to set the Deepgram key."
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
      controlSocket.onmessage = (event) => {
        try {
          handleControlEvent(JSON.parse(event.data));
        } catch {
          /* ignore malformed event */
        }
      };
      await waitForSocketOpen(controlSocket, "Call connection");

      // Mic capture can start before the STT socket finishes connecting —
      // frames are queued and flushed the moment it opens, so no audio at
      // the very start of the call is lost.
      let sttSocket = null;
      const pcmQueue = [];
      stopMicRef.current = await startMicCapture(
        (pcm) => {
          if (micMutedRef.current) return;
          if (sttSocket?.readyState === WebSocket.OPEN) {
            sttSocket.send(pcm);
          } else if (pcmQueue.length < 100) {
            pcmQueue.push(pcm);
          }
        },
        {
          onRecovering: () => setError("Microphone interrupted — reconnecting…"),
          onRecovered: () => setError(null),
          onFatalError: () => {
            setError("Microphone connection was lost and couldn't be restored. Please try again.");
            setCallState(VOICE_CALL_STATE.ERROR);
          },
        }
      );

      const displayTranscript = (partial = "") => {
        const combined = [finalizedTranscriptRef.current, partial].filter(Boolean).join(" ").trim();
        if (!combined) return;
        if (!userMessageIdRef.current) {
          userMessageIdRef.current = chat.appendMessage("user", combined, { channel: "voice" });
        } else {
          chat.updateMessage(userMessageIdRef.current, combined);
        }
      };

      const sendFinalTranscript = () => {
        const text = finalizedTranscriptRef.current.trim();
        if (!text || controlSocket.readyState !== WebSocket.OPEN) {
          finalizedTranscriptRef.current = "";
          userMessageIdRef.current = null;
          return;
        }
        if (!bargeInEnabled && callStateRef.current === VOICE_CALL_STATE.SPEAKING) {
          return;
        }
        finalizedTranscriptRef.current = "";
        pendingBargeInRef.current = false;
        setCallState(VOICE_CALL_STATE.PROCESSING);
        controlSocket.send(
          JSON.stringify({
            type: "user.transcript.final",
            data: { text, customer_email: customerEmail || null },
          })
        );
        userMessageIdRef.current = null;
      };

      sttSocket = connectSTT(session.stt, session.deepgram_token, {
        onPartial: (text) => {
          displayTranscript(text);
          // Confirmed real speech (not just a VAD blip) — now it's safe to
          // actually cut the assistant off, if barge-in is allowed.
          if (pendingBargeInRef.current && bargeInEnabled && text.trim().length >= MIN_BARGE_IN_CHARS) {
            pendingBargeInRef.current = false;
            ttsRef.current?.playback?.interrupt();
            setCallState(VOICE_CALL_STATE.INTERRUPTED);
          }
        },
        onFinal: (text, speechFinal) => {
          // Accumulate — a single utterance often arrives as several
          // `is_final` chunks, and only the last carries `speech_final`.
          if (text.trim()) {
            finalizedTranscriptRef.current = [finalizedTranscriptRef.current, text.trim()]
              .filter(Boolean)
              .join(" ");
          }
          displayTranscript();
          if (speechFinal) sendFinalTranscript();
        },
        onUtteranceEnd: () => {
          // Fallback: word-timing gap detected with no `speech_final` —
          // still finalize whatever we've accumulated so the call never
          // gets stuck waiting and the customer never has to repeat
          // themselves for no visible reason.
          if (finalizedTranscriptRef.current.trim()) sendFinalTranscript();
        },
        onSpeechStarted: () => {
          // VAD fired — this alone might just be background noise, so we
          // only flag it as a *possible* barge-in and wait for onPartial to
          // confirm there's real transcribed content before interrupting.
          if (callStateRef.current === VOICE_CALL_STATE.SPEAKING) {
            pendingBargeInRef.current = true;
          } else if (callStateRef.current !== VOICE_CALL_STATE.PROCESSING) {
            setCallState(VOICE_CALL_STATE.LISTENING);
          }
        },
        onError: (event, wasOpened) => {
          if (!wasOpened) {
            setError("Couldn't connect to speech recognition.");
            setCallState(VOICE_CALL_STATE.ERROR);
            return;
          }
          setError("Speech recognition connection dropped. Reconnecting…");
        },
      });
      sttSocketRef.current = sttSocket;
      await waitForSocketOpen(sttSocket, "Speech recognition");

      // Flush anything captured while the STT socket was still connecting.
      if (sttSocket.readyState === WebSocket.OPEN) {
        for (const pcm of pcmQueue) sttSocket.send(pcm);
        pcmQueue.length = 0;
      }

      ttsRef.current = connectTTS(session.tts, session.deepgram_token, {
        onAudioStarted: () => setCallState(VOICE_CALL_STATE.SPEAKING),
        onAudioCompleted: () => {
          if (callStateRef.current !== VOICE_CALL_STATE.ERROR) setCallState(VOICE_CALL_STATE.LISTENING);
          // Barge-in was off and the customer talked while we were still
          // speaking — now that we're done, process what they said.
          if (finalizedTranscriptRef.current.trim()) sendFinalTranscript();
        },
        onError: () => setError("Voice playback dropped, but text responses are still available."),
      });
      await waitForSocketOpen(ttsRef.current.socket, "Text-to-speech");

      // Flush any speech (e.g. the call-start greeting) that arrived
      // before this socket was ready to accept it.
      if (pendingSpeechRef.current.length) {
        const queued = pendingSpeechRef.current;
        pendingSpeechRef.current = [];
        for (const text of queued) speakSentence(text);
      }

      setCallState(VOICE_CALL_STATE.LISTENING);
    } catch (err) {
      setError(
        err?.name === "NotAllowedError"
          ? "Microphone access was denied. Please allow it to start a voice call."
          : err?.message || "Couldn't connect the call. Please try again."
      );
      setCallState(VOICE_CALL_STATE.ERROR);
      await cleanup();
    }
  }, [sessionId, customerEmail, chat, onSessionCreated, bargeInEnabled, handleControlEvent, cleanup, setCallState]);

  const endCall = useCallback(async () => {
    if (controlSocketRef.current?.readyState === WebSocket.OPEN) {
      try {
        controlSocketRef.current.send(JSON.stringify({ type: "call.end" }));
      } catch {
        /* socket already going away */
      }
    }
    await cleanup();
    setCallState(VOICE_CALL_STATE.IDLE);
  }, [cleanup, setCallState]);

  return { callState, error, startCall, endCall, micMuted, speakerMuted, toggleMic, toggleSpeaker };
}