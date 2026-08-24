import { useCallback, useEffect, useState } from "react";
import { getChatSession, sendChatMessage } from "../services/api.js";
import { MESSAGE_ROLE } from "../utils/constants.js";

const WELCOME_MESSAGE = {
  id: "welcome",
  role: MESSAGE_ROLE.ASSISTANT,
  content: "Hi! Ask me anything about our services, hours, pricing, or policies.",
};

/**
 * Manages messages for a single chat session. Conversation memory is now
 * server-side (the backend loads and trims history from the database), so
 * this hook just displays whatever session is active and appends to it.
 *
 * @param {string | null} sessionId - existing session to load, or null for a fresh chat
 * @param {{ onSessionCreated?: (id: string) => void }} [options]
 */
export function useChat(sessionId, { onSessionCreated } = {}) {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sessionId) {
      setMessages([WELCOME_MESSAGE]);
      return;
    }
    setIsLoadingHistory(true);
    setError(null);
    getChatSession(sessionId)
      .then((session) => {
        setMessages(
          session.messages.map((m, i) => ({ id: `${sessionId}-${i}`, role: m.role, content: m.content }))
        );
      })
      .catch(() => setError("Couldn't load that conversation."))
      .finally(() => setIsLoadingHistory(false));
  }, [sessionId]);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim()) return;

      const userMessage = { id: crypto.randomUUID(), role: MESSAGE_ROLE.USER, content: text };
      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);
      setError(null);

      try {
        const response = await sendChatMessage({ question: text, sessionId });

        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: MESSAGE_ROLE.ASSISTANT, content: response.answer },
        ]);

        if (!sessionId && response.session_id) {
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
    [sessionId, onSessionCreated]
  );

  return { messages, isLoading: isSending, isLoadingHistory, error, sendMessage };
}