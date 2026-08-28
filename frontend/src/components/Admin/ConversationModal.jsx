import { useEffect, useState } from "react";
import { getConversation, resolveConversation } from "../../services/adminApi.js";
import { AlertCircle } from "../common/Icons.jsx";
import Modal from "../common/Modal.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";

const AGENT_LABELS = {
  knowledge: "Knowledge Agent",
  booking: "Booking Agent",
  support: "Support Agent",
};

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString();
}

export default function ConversationModal({ sessionId, onClose, onResolved }) {
  const [session, setSession] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isResolving, setIsResolving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getConversation(sessionId)
      .then((data) => {
        if (!cancelled) setSession(data);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load this conversation.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  async function handleResolve() {
    setIsResolving(true);
    try {
      const updated = await resolveConversation(sessionId);
      setSession((prev) => (prev ? { ...prev, needs_human: updated.needs_human } : prev));
      onResolved?.();
    } finally {
      setIsResolving(false);
    }
  }

  return (
    <Modal title="Conversation" onClose={onClose} width={620}>
      {isLoading && <LoadingState label="Loading conversation…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {session && !isLoading && !error && (
        <div className="conversation-modal">
          {session.needs_human && (
            <div className="conversation-modal__alert">
              <AlertCircle size={15} />
              <div>
                <strong>Needs a human</strong>
                <p>{session.escalation_reason || "Flagged by the Support Agent."}</p>
                {session.escalated_at && (
                  <p className="settings-form__hint" style={{ margin: 0 }}>
                    Flagged {formatDateTime(session.escalated_at)}
                  </p>
                )}
              </div>
              <button type="button" className="catalog-section__add-btn" onClick={handleResolve} disabled={isResolving}>
                {isResolving && <Spinner size={13} className="spinner--on-dark" />}
                {isResolving ? "Resolving…" : "Mark resolved"}
              </button>
            </div>
          )}

          {session.customer_email && (
            <p className="settings-form__hint">Customer: {session.customer_email}</p>
          )}

          <div className="conversation-modal__transcript">
            {session.messages.map((msg, idx) => (
              <div
                key={idx}
                className={`conversation-modal__message conversation-modal__message--${msg.role}`}
              >
                <div className="conversation-modal__message-meta">
                  <span>{msg.role === "user" ? "Customer" : AGENT_LABELS[msg.agent] || "Assistant"}</span>
                  <span>{formatDateTime(msg.created_at)}</span>
                </div>
                <p>{msg.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}