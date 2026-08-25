import { useCallback, useState } from "react";
import ChatSidebar from "../components/Chat/ChatSidebar.jsx";
import ChatWidget from "../components/Chat/ChatWidget.jsx";
import EmailGateModal from "../components/Chat/EmailGateModal.jsx";
import WelcomeToast from "../components/Chat/WelcomeToast.jsx";
import { useCustomer } from "../context/CustomerContext.jsx";
import { useChatSessions } from "../hooks/useChatSessions.js";

export default function Home() {
  const { customer, isIdentified, lastGreeting, clearGreeting, switchAccount } = useCustomer();
  const [activeSessionId, setActiveSessionId] = useState(null);
  const { sessions, isLoading, refresh, remove } = useChatSessions(customer?.email);

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

  const handleSwitchAccount = useCallback(() => {
    setActiveSessionId(null);
    switchAccount();
  }, [switchAccount]);

  if (!isIdentified) {
    return <EmailGateModal />;
  }

  return (
    <div className="home-page home-page--with-sidebar">
      {lastGreeting && (
        <WelcomeToast
          isReturning={lastGreeting.isReturning}
          name={customer?.name}
          onDismiss={clearGreeting}
        />
      )}

      <ChatSidebar
        sessions={sessions}
        isLoading={isLoading}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNew={handleNew}
        onDelete={handleDelete}
        onSwitchAccount={handleSwitchAccount}
      />

      <div className="home-page__chat-area">
        <ChatWidget
          key={activeSessionId || "new"}
          sessionId={activeSessionId}
          customerEmail={customer?.email}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  );
}