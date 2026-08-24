export default function ChatSidebar({ sessions, isLoading, activeSessionId, onSelect, onNew, onDelete }) {
  function handleDelete(e, sessionId) {
    e.stopPropagation();
    if (confirm("Delete this conversation?")) {
      onDelete(sessionId);
    }
  }

  return (
    <aside className="chat-sidebar" aria-label="Chat history">
      <button type="button" className="chat-sidebar__new" onClick={onNew}>
        + New chat
      </button>

      <div className="chat-sidebar__list">
        {isLoading && <p className="chat-sidebar__empty">Loading…</p>}

        {!isLoading && sessions.length === 0 && (
          <p className="chat-sidebar__empty">No conversations yet.</p>
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
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}