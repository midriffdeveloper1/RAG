import { useCallback, useRef, useState } from "react";
import { sendChatMessage } from "../services/api.js";
import { MESSAGE_ROLE } from "../utils/constants.js";

/**
 * Encapsulates chat state (messages, loading, error) for the widget.
 * Fully wired to POST /chat (retrieval + Groq generation, with a polite
 * out-of-domain refusal baked into the backend response itself — no
 * special-casing needed here).
 */
export function useChat() {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: MESSAGE_ROLE.ASSISTANT,
      content: "Hi! Ask me anything about our services, hours, pricing, or policies.",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // One session id per widget mount. Not used by the backend yet (each
  // question is answered independently), but threaded through so
  // multi-turn memory can be added later without a frontend change.
  const sessionIdRef = useRef(crypto.randomUUID());

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return;

    const userMessage = { id: crypto.randomUUID(), role: MESSAGE_ROLE.USER, content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage({
        question: text,
        sessionId: sessionIdRef.current,
      });

      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: MESSAGE_ROLE.ASSISTANT, content: response.answer },
      ]);
    } catch (err) {
      const message =
        err.response?.status === 503
          ? "The assistant isn't configured yet — ask an admin to set GROQ_API_KEY."
          : err.message || "Something went wrong. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, isLoading, error, sendMessage };
}