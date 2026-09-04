import { useCallback, useRef, useState } from "react";
import { startVoiceSession } from "../services/api.js";
import {
  connectSTT,
  connectTTS,
  startMicCapture,
  waitForSocketOpen,
} from "../realtime/deepgramClient.js";
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

function getWsOrigin() {
  const configured = import.meta.env.VITE_API_BASE_URL;

  let origin = window.location.origin;

  if (configured) {
    try {
      origin = new URL(configured, window.location.origin).origin;
    } catch {
      // Fall back to the page origin if VITE_API_BASE_URL is malformed.
    }
  }

  return origin.replace(/^http/, "ws");
}

export function useVoiceSession({
  sessionId,
  customerEmail,
  chat,
  onSessionCreated,
}) {
  const [callState, setCallStateRaw] = useState(
    VOICE_CALL_STATE.IDLE,
  );
  const [error, setError] = useState(null);

  const callStateRef = useRef(
    VOICE_CALL_STATE.IDLE,
  );

  const controlSocketRef = useRef(null);
  const sttSocketRef = useRef(null);
  const ttsRef = useRef(null);
  const stopMicRef = useRef(null);

  const userMessageIdRef = useRef(null);
  const assistantMessageIdRef = useRef(null);
  const assistantBufferRef = useRef("");
  const ttsSentenceBufferRef = useRef("");

  const setCallState = useCallback((next) => {
    callStateRef.current = next;
    setCallStateRaw(next);
  }, []);

  const cleanup = useCallback(async () => {
    if (stopMicRef.current) {
      try {
        await stopMicRef.current();
      } catch {}

      stopMicRef.current = null;
    }

    if (sttSocketRef.current) {
      try {
        sttSocketRef.current.closeForCleanup?.();
      } catch {}

      sttSocketRef.current = null;
    }

    if (ttsRef.current) {
      try {
        await ttsRef.current.playback.close();
      } catch {}

      try {
        ttsRef.current.socket.closeForCleanup?.();
      } catch {}

      ttsRef.current = null;
    }

    if (controlSocketRef.current) {
      try {
        controlSocketRef.current.close(
          1000,
          "Client cleanup",
        );
      } catch {}

      controlSocketRef.current = null;
    }

    userMessageIdRef.current = null;
    assistantMessageIdRef.current = null;
    assistantBufferRef.current = "";
    ttsSentenceBufferRef.current = "";
  }, []);

  const speakSentence = useCallback((sentence) => {
    const text = sentence.trim();
    const socket = ttsRef.current?.socket;

    if (
      !text ||
      !socket ||
      socket.readyState !== WebSocket.OPEN
    ) {
      return;
    }

    socket.send(
      JSON.stringify({
        type: "Speak",
        text,
      }),
    );

    socket.send(
      JSON.stringify({
        type: "Flush",
      }),
    );
  }, []);

  const handleControlEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "session.created":
        case "call.started":
          setCallState(
            VOICE_CALL_STATE.CONNECTED,
          );
          break;

        case "assistant.response.started":
          setCallState(
            VOICE_CALL_STATE.PROCESSING,
          );

          assistantBufferRef.current = "";
          ttsSentenceBufferRef.current = "";

          assistantMessageIdRef.current =
            chat.appendMessage(
              "assistant",
              "",
              { channel: "voice" },
            );
          break;

        case "assistant.text.delta": {
          const delta =
            event.data?.delta || "";

          assistantBufferRef.current += delta;
          ttsSentenceBufferRef.current +=
            delta;

          if (
            assistantMessageIdRef.current
          ) {
            chat.updateMessage(
              assistantMessageIdRef.current,
              assistantBufferRef.current,
            );
          }

          if (
            SENTENCE_END.test(
              ttsSentenceBufferRef.current,
            )
          ) {
            speakSentence(
              ttsSentenceBufferRef.current,
            );

            ttsSentenceBufferRef.current =
              "";
          }

          break;
        }

        case "assistant.text.completed": {
          const finalText =
            event.data?.text ||
            assistantBufferRef.current;

          if (
            assistantMessageIdRef.current
          ) {
            chat.updateMessage(
              assistantMessageIdRef.current,
              finalText,
            );
          }

          if (
            ttsSentenceBufferRef.current.trim()
          ) {
            speakSentence(
              ttsSentenceBufferRef.current,
            );

            ttsSentenceBufferRef.current =
              "";
          }

          assistantMessageIdRef.current =
            null;

          break;
        }

        case "tool.call.started":
          setCallState(
            VOICE_CALL_STATE.PROCESSING,
          );
          break;

        case "error":
          setError(
            event.data?.message ||
              "Something went wrong during the call.",
          );

          if (!event.data?.recoverable) {
            setCallState(
              VOICE_CALL_STATE.ERROR,
            );
          }

          break;

        default:
          break;
      }
    },
    [chat, speakSentence, setCallState],
  );

  const startCall = useCallback(async () => {
    if (
      callStateRef.current !==
      VOICE_CALL_STATE.IDLE
    ) {
      return;
    }

    setError(null);
    setCallState(
      VOICE_CALL_STATE.CONNECTING,
    );

    let session;

    try {
      session = await startVoiceSession({
        sessionId,
        customerEmail,
      });
    } catch (err) {
      const message =
        err.response?.status === 403
          ? "Voice calling isn't enabled for this business yet."
          : err.response?.status === 503
            ? "Voice calling isn't configured yet — ask an admin to set the Deepgram key."
            : "Couldn't start the call. Please try again.";

      setError(message);
      setCallState(
        VOICE_CALL_STATE.ERROR,
      );

      return;
    }

    if (
      !sessionId &&
      session.conversation_id
    ) {
      onSessionCreated?.(
        session.conversation_id,
      );
    }

    try {
      const controlUrl = new URL(
        session.ws_url.startsWith("ws")
          ? session.ws_url
          : `${getWsOrigin()}${session.ws_url}`,
      );

      controlUrl.searchParams.set(
        "voice_session_id",
        session.voice_session_id,
      );

      controlUrl.searchParams.set(
        "browser_id",
        getBrowserId(),
      );

      const controlSocket =
        new WebSocket(
          controlUrl.toString(),
        );

      controlSocketRef.current =
        controlSocket;

      controlSocket.onmessage = (event) => {
        try {
          handleControlEvent(
            JSON.parse(event.data),
          );
        } catch {}
      };

      await waitForSocketOpen(
        controlSocket,
        "Call connection",
      );

      console.info(
        "[Voice] Control socket READY",
      );

      let sttSocket = null;
      let pcmFrames = 0;
      let pcmBytes = 0;
      const pcmQueue = [];

      stopMicRef.current =
        await startMicCapture(
          (pcm) => {
            if (
              sttSocket?.readyState ===
              WebSocket.OPEN
            ) {
              sttSocket.send(pcm);
              pcmFrames++;
              pcmBytes += pcm.byteLength;

              if (
                pcmFrames === 1 ||
                pcmFrames % 25 === 0
              ) {
                console.info(
                  "[Voice STT] Audio sent",
                  {
                    frames: pcmFrames,
                    bytes: pcmBytes,
                  },
                );
              }
            } else if (
              pcmQueue.length < 100
            ) {
              pcmQueue.push(pcm);
            }
          },
          {
            // Mic track died mid-call (device sleep, Bluetooth
            // renegotiation, another app grabbing the device, etc).
            // We attempt to reacquire automatically — this is what
            // used to happen silently and starve Deepgram of audio
            // until it timed out with code 1011.
            onRecovering: () => {
              console.warn(
                "[Voice] Microphone interrupted — attempting to reconnect...",
              );
            },

            onRecovered: () => {
              console.info(
                "[Voice] Microphone reconnected, call continuing",
              );
            },

            onFatalError: (err) => {
              console.error(
                "[Voice] Microphone recovery failed",
                err,
              );

              setError(
                "Microphone connection was lost and couldn't be restored. Please check your device and try again.",
              );

              setCallState(
                VOICE_CALL_STATE.ERROR,
              );
            },
          },
        );

      console.info(
        "[Voice] Microphone READY",
      );

      sttSocket = connectSTT(
        session.stt,
        session.deepgram_token,
        {
          onPartial: (text) => {
            if (
              !userMessageIdRef.current
            ) {
              userMessageIdRef.current =
                chat.appendMessage(
                  "user",
                  text,
                  { channel: "voice" },
                );
            } else {
              chat.updateMessage(
                userMessageIdRef.current,
                text,
              );
            }
          },

          onFinal: (
            text,
            speechFinal,
          ) => {
            if (
              !userMessageIdRef.current
            ) {
              userMessageIdRef.current =
                chat.appendMessage(
                  "user",
                  text,
                  { channel: "voice" },
                );
            } else {
              chat.updateMessage(
                userMessageIdRef.current,
                text,
              );
            }

            if (
              speechFinal &&
              text.trim() &&
              controlSocket.readyState ===
                WebSocket.OPEN
            ) {
              setCallState(
                VOICE_CALL_STATE.PROCESSING,
              );

              controlSocket.send(
                JSON.stringify({
                  type:
                    "user.transcript.final",
                  data: {
                    text: text.trim(),
                    customer_email:
                      customerEmail ||
                      null,
                  },
                }),
              );

              userMessageIdRef.current =
                null;
            }
          },

          onSpeechStarted: () => {
            ttsRef.current?.playback?.interrupt();

            if (
              callStateRef.current ===
              VOICE_CALL_STATE.SPEAKING
            ) {
              setCallState(
                VOICE_CALL_STATE.INTERRUPTED,
              );
            } else {
              setCallState(
                VOICE_CALL_STATE.LISTENING,
              );
            }
          },

          onOpen: () => {
            console.info(
              "[Voice STT] Deepgram OPEN",
            );
          },

          onError: (
            event,
            wasOpened,
          ) => {
            console.error(
              "[Voice STT] Error",
              {
                code: event?.code,
                reason: event?.reason,
                wasOpened,
              },
            );

            // A no-audio timeout (1011) right after a mic recovery
            // attempt is expected transient noise, not a fatal call
            // error — the mic layer already handles reconnecting the
            // audio source. Only hard-fail the call if the socket
            // never opened at all (real connectivity/auth problem).
            if (!wasOpened) {
              setError(
                "Couldn't connect to speech recognition.",
              );

              setCallState(
                VOICE_CALL_STATE.ERROR,
              );

              return;
            }

            setError(
              "Speech recognition connection dropped. Reconnecting...",
            );
          },
        },
      );

      sttSocketRef.current =
        sttSocket;

      await waitForSocketOpen(
        sttSocket,
        "Deepgram STT connection",
      );

      console.info(
        "[Voice STT] Socket READY",
      );

      if (
        sttSocket.readyState ===
        WebSocket.OPEN
      ) {
        for (const pcm of pcmQueue) {
          sttSocket.send(pcm);
          pcmFrames++;
          pcmBytes += pcm.byteLength;
        }

        pcmQueue.length = 0;
      }

      console.info(
        "[Voice STT] Initial audio flushed",
        {
          frames: pcmFrames,
          bytes: pcmBytes,
        },
      );

      ttsRef.current = connectTTS(
        session.tts,
        session.deepgram_token,
        {
          onAudioStarted: () => {
            setCallState(
              VOICE_CALL_STATE.SPEAKING,
            );
          },

          onAudioCompleted: () => {
            if (
              callStateRef.current !==
              VOICE_CALL_STATE.ERROR
            ) {
              setCallState(
                VOICE_CALL_STATE.LISTENING,
              );
            }
          },

          onError: () => {
            setError(
              "Voice playback dropped, but text responses are still available.",
            );
          },
        },
      );

      await waitForSocketOpen(
        ttsRef.current.socket,
        "Deepgram TTS connection",
      );

      console.info(
        "[Voice TTS] Socket READY",
      );

      setCallState(
        VOICE_CALL_STATE.LISTENING,
      );

      console.info(
        "[Voice] CALL READY",
      );
    } catch (err) {
      console.error(
        "[Voice] Call setup failed",
        err,
      );

      setError(
        err?.name === "NotAllowedError"
          ? "Microphone access was denied. Please allow microphone access."
          : err?.message ||
              "Couldn't connect the call. Please try again.",
      );

      setCallState(
        VOICE_CALL_STATE.ERROR,
      );

      await cleanup();
    }
  }, [
    sessionId,
    customerEmail,
    chat,
    onSessionCreated,
    handleControlEvent,
    cleanup,
    setCallState,
  ]);

  const endCall = useCallback(async () => {
    try {
      const socket =
        controlSocketRef.current;

      if (
        socket?.readyState ===
        WebSocket.OPEN
      ) {
        socket.send(
          JSON.stringify({
            type: "call.end",
          }),
        );
      }
    } catch {}

    await cleanup();

    setCallState(
      VOICE_CALL_STATE.IDLE,
    );
  }, [cleanup, setCallState]);

  return {
    callState,
    error,
    startCall,
    endCall,
  };
}