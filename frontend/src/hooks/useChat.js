import { useCallback, useState } from "react";
import { sendChatMessage } from "../services/api.js";
import { MESSAGE_ROLE } from "../utils/constants.js";

/**
 * Encapsulates chat state (messages, loading, error) for the widget.
 * Message list and loading/error states are fully functional; the actual
 * network call is a TODO until the backend /chat endpoint is implemented.
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

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return;

    const userMessage = { id: crypto.randomUUID(), role: MESSAGE_ROLE.USER, content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // TODO: replace with real call once backend /chat is implemented.
      const response = await sendChatMessage({ question: text });

      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: MESSAGE_ROLE.ASSISTANT, content: response.answer },
      ]);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, isLoading, error, sendMessage };
}
