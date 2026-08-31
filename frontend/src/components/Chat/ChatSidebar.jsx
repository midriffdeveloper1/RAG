import { MessageSquare, Plus, Trash2, UserCog } from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";
import TicketStatusPanel from "./TicketStatusPanel.jsx";

export default function ChatSidebar({
  sessions,
  isLoading,
  activeSessionId,
  onSelect,
  onNew,
  onDelete,
  onSwitchAccount,
}) {
  function handleDelete(e, sessionId) {
    e.stopPropagation();
    if (window.confirm("Delete this conversation?")) {
      onDelete(sessionId);
    }
  }

  return (
    <aside className="chat-sidebar" aria-label="Chat history">
      <button type="button" className="chat-sidebar__new" onClick={onNew}>
        <Plus size={15} />
        New chat
      </button>

      <div className="chat-sidebar__list">
        {isLoading && (
          <div className="chat-sidebar__loading">
            <Spinner size={14} />
            <span>Loading…</span>
          </div>
        )}

        {!isLoading && sessions.length === 0 && (
          <div className="chat-sidebar__empty">
            <MessageSquare size={20} className="chat-sidebar__empty-icon" />
            <p>No conversations yet.</p>
          </div>
        )}

        {sessions.map((session) => (
          <div
            key={session.id}
            className={`chat-sidebar__item ${
              session.id === activeSessionId ? "chat-sidebar__item--active" : ""
            }`}
          >
            <button
              type="button"
              className="chat-sidebar__item-title"
              onClick={() => onSelect(session.id)}
              title={session.title || "New conversation"}
            >
              {session.title || "New conversation"}
            </button>
            <button
              type="button"
              className="chat-sidebar__item-delete"
              aria-label="Delete conversation"
              onClick={(e) => handleDelete(e, session.id)}
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>

      {onSwitchAccount && (
        <button type="button" className="chat-sidebar__switch-account" onClick={onSwitchAccount}>
          <UserCog size={13} />
          Not you? Switch account
        </button>
      )}

      <TicketStatusPanel />
    </aside>
  );
}