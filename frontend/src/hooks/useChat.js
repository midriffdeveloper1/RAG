import { useCallback, useRef, useState } from "react";
import { sendChatMessage } from "../services/api.js";
import { MAX_HISTORY_MESSAGES, MESSAGE_ROLE } from "../utils/constants.js";

const WELCOME_MESSAGE_ID = "welcome";

export function useChat() {
  const [messages, setMessages] = useState([
    {
      id: WELCOME_MESSAGE_ID,
      role: MESSAGE_ROLE.ASSISTANT,
      content: "Hi! Ask me anything about our services, hours, pricing, or policies.",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const sessionIdRef = useRef(crypto.randomUUID());

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim()) return;

      const userMessage = { id: crypto.randomUUID(), role: MESSAGE_ROLE.USER, content: text };

     
      const history = messages
        .filter((m) => m.id !== WELCOME_MESSAGE_ID)
        .slice(-MAX_HISTORY_MESSAGES)
        .map((m) => ({ role: m.role, content: m.content }));

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        const response = await sendChatMessage({
          question: text,
          sessionId: sessionIdRef.current,
          history,
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
    },
    [messages]
  );

  return { messages, isLoading, error, sendMessage };
}