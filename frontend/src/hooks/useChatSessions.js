import { useCallback, useEffect, useState } from "react";
import { deleteChatSession, listChatSessions } from "../services/api.js";

export function useChatSessions(customerEmail) {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(() => {
    if (!customerEmail) {
      setSessions([]);
      setIsLoading(false);
      return Promise.resolve();
    }
    setIsLoading(true);
    return listChatSessions(customerEmail)
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setIsLoading(false));
  }, [customerEmail]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(
    async (sessionId) => {
      await deleteChatSession(sessionId, customerEmail);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    },
    [customerEmail]
  );

  return { sessions, isLoading, refresh, remove };
}