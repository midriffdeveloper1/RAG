import { useEffect, useState } from "react";
import {
  deleteConversation,
  getConversation,
  reopenConversation,
  resolveConversation,
} from "../../services/adminApi.js";
import { AlertCircle, CheckCircle2, Trash2 } from "../common/Icons.jsx";
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

export default function ConversationModal({ sessionId, onClose, onResolved, onDeleted }) {
  const [session, setSession] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

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
    setIsUpdatingStatus(true);
    try {
      const updated = await resolveConversation(sessionId);
      setSession((prev) =>
        prev ? { ...prev, needs_human: updated.needs_human, resolved_at: updated.resolved_at } : prev
      );
      onResolved?.();
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function handleReopen() {
    setIsUpdatingStatus(true);
    try {
      const updated = await reopenConversation(sessionId);
      setSession((prev) =>
        prev ? { ...prev, needs_human: updated.needs_human, resolved_at: updated.resolved_at } : prev
      );
      onResolved?.();
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Permanently delete this conversation? This can't be undone.")) return;
    setIsDeleting(true);
    try {
      await deleteConversation(sessionId);
      onDeleted?.();
      onClose();
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <Modal title="Conversation" onClose={onClose} width={620}>
      {isLoading && <LoadingState label="Loading conversation…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {session && !isLoading && !error && (
        <div className="conversation-modal">
          {(session.customer_name || session.customer_phone || session.customer_email) && (
            <div className="conversation-modal__contact">
              {session.customer_name && <strong>{session.customer_name}</strong>}
              {session.customer_phone && (
                <a href={`tel:${session.customer_phone}`}>{session.customer_phone}</a>
              )}
              {session.customer_email && (
                <a href={`mailto:${session.customer_email}`}>{session.customer_email}</a>
              )}
            </div>
          )}

          {session.ticket_number && (
            <div className="conversation-modal__ticket-bar">
              <span>
                Ticket <strong>{session.ticket_number}</strong>
              </span>
              {session.needs_human ? (
                <button
                  type="button"
                  className="catalog-section__add-btn"
                  onClick={handleResolve}
                  disabled={isUpdatingStatus}
                >
                  {isUpdatingStatus ? <Spinner size={13} className="spinner--on-dark" /> : <CheckCircle2 size={14} />}
                  {isUpdatingStatus ? "Updating…" : "Mark resolved"}
                </button>
              ) : (
                <button
                  type="button"
                  className="chat-sidebar__ticket-submit"
                  onClick={handleReopen}
                  disabled={isUpdatingStatus}
                >
                  {isUpdatingStatus ? <Spinner size={13} className="spinner--on-dark" /> : null}
                  {isUpdatingStatus ? "Updating…" : "Reopen"}
                </button>
              )}
            </div>
          )}

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
            </div>
          )}

          {!session.needs_human && session.ticket_number && session.resolved_at && (
            <p className="settings-form__hint" style={{ margin: 0 }}>
              Resolved {formatDateTime(session.resolved_at)}
            </p>
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

          <div className="staff-modal-form__actions">
            <button
              type="button"
              className="staff-modal-form__cancel"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? <Spinner size={13} /> : <Trash2 size={13} />}
              {isDeleting ? "Deleting…" : "Delete conversation"}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}