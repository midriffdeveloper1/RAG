import { useCallback, useEffect, useRef, useState } from "react";
import { discardChatSessionOnUnload, getChatSession, sendChatMessage } from "../services/api.js";
import { MESSAGE_ROLE } from "../utils/constants.js";

const WELCOME_MESSAGE = {
  id: "welcome",
  role: MESSAGE_ROLE.ASSISTANT,
  content: "Hi! Ask me anything about our services, hours, pricing, or policies.",
};

export function useChat(sessionId, customerEmail, { onSessionCreated } = {}) {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const liveSessionIdRef = useRef(sessionId);

  useEffect(() => {
    liveSessionIdRef.current = sessionId;
  }, [sessionId]);

  const refresh = useCallback(() => {
    if (!sessionId || !customerEmail) {
      setMessages([WELCOME_MESSAGE]);
      return;
    }
    setIsLoadingHistory(true);
    setError(null);
    return getChatSession(sessionId, customerEmail)
      .then((session) => {
        setMessages(
          session.messages.map((m, i) => ({
            id: `${sessionId}-${i}`,
            role: m.role,
            content: m.content,
            channel: m.channel,
          }))
        );
      })
      .catch(() => setError("Couldn't load that conversation."))
      .finally(() => setIsLoadingHistory(false));
  }, [sessionId, customerEmail]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  
  useEffect(() => {
    function handleUnload() {
      discardChatSessionOnUnload(liveSessionIdRef.current);
    }
    window.addEventListener("pagehide", handleUnload);
    window.addEventListener("beforeunload", handleUnload);
    return () => {
      window.removeEventListener("pagehide", handleUnload);
      window.removeEventListener("beforeunload", handleUnload);
    };
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || !customerEmail) return;

      const userMessage = { id: crypto.randomUUID(), role: MESSAGE_ROLE.USER, content: text };
      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);
      setError(null);

      try {
        const response = await sendChatMessage({ question: text, sessionId, customerEmail });

        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: MESSAGE_ROLE.ASSISTANT, content: response.answer },
        ]);

        if (!sessionId && response.session_id) {
          liveSessionIdRef.current = response.session_id;
          onSessionCreated?.(response.session_id);
        }
      } catch (err) {
        const message =
          err.response?.status === 503
            ? "The assistant isn't configured yet — ask an admin to set GROQ_API_KEY."
            : err.response?.status === 502
              ? "The assistant is temporarily unavailable. Please try again shortly."
              : err.message || "Something went wrong. Please try again.";
        setError(message);
      } finally {
        setIsSending(false);
      }
    },
    [sessionId, customerEmail, onSessionCreated]
  );

  /** Appends a message immediately (used by the voice layer for live turns). */
  const appendMessage = useCallback((role, content, extra = {}) => {
    const id = crypto.randomUUID();
    setMessages((prev) => [...prev, { id, role, content, ...extra }]);
    return id;
  }, []);

  /** Updates an already-appended message's content in place, by id. */
  const updateMessage = useCallback((id, content) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, content } : m)));
  }, []);

  return {
    messages,
    isLoading: isSending,
    isLoadingHistory,
    error,
    sendMessage,
    refresh,
    appendMessage,
    updateMessage,
  };
}