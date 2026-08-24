import { useCallback, useState } from "react";
import ChatSidebar from "../components/Chat/ChatSidebar.jsx";
import ChatWidget from "../components/Chat/ChatWidget.jsx";
import { useChatSessions } from "../hooks/useChatSessions.js";

export default function Home() {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const { sessions, isLoading, refresh, remove } = useChatSessions();

  const handleSessionCreated = useCallback(
    (sessionId) => {
      setActiveSessionId(sessionId);
      refresh();
    },
    [refresh]
  );

  const handleNew = useCallback(() => setActiveSessionId(null), []);

  const handleDelete = useCallback(
    async (sessionId) => {
      await remove(sessionId);
      setActiveSessionId((current) => (current === sessionId ? null : current));
    },
    [remove]
  );

  return (
    <div className="home-page home-page--with-sidebar">
      <ChatSidebar
        sessions={sessions}
        isLoading={isLoading}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNew={handleNew}
        onDelete={handleDelete}
      />

      <div className="home-page__chat-area">
        <ChatWidget
          key={activeSessionId || "new"}
          sessionId={activeSessionId}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  );
}