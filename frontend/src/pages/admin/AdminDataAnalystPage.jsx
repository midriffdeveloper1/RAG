import { useCallback, useEffect, useRef, useState } from "react";
import AnalystMessage from "../../components/Analyst/AnalystMessage.jsx";
import { Database, Loader2, Plus, Send, Sparkles, Trash2 } from "../../components/common/Icons.jsx";
import {
  askAnalyst,
  deleteAnalystSession,
  getAnalystScope,
  getAnalystSession,
  listAnalystSessions,
} from "../../services/adminApi.js";

export default function AdminDataAnalystPage() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [scope, setScope] = useState(null);

  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listAnalystSessions({ page: 1, pageSize: 20 });
      setSessions(data.sessions ?? []);
    } catch {
      // The thread list is a convenience; failing to load it shouldn't block
      // the admin from asking a new question.
    }
  }, []);

  useEffect(() => {
    getAnalystScope().then(setScope).catch(() => setScope(null));
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    // Keep the newest turn in view as the conversation grows.
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, isSending]);

  async function handleSubmit(event) {
    event?.preventDefault();

    const trimmed = question.trim();
    if (!trimmed || isSending) return;

    setError(null);
    setQuestion("");
    setIsSending(true);

    // Show the admin's question immediately rather than waiting for the
    // round-trip — the agent can take several seconds to plan and run SQL.
    const optimistic = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((current) => [...current, optimistic]);

    try {
      const data = await askAnalyst({ question: trimmed, sessionId });

      setSessionId(data.session_id);
      setMessages((current) => [...current, data.message]);
      refreshSessions();
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        "Something went wrong reaching the analyst. Please try again.";

      setError(detail);
      // Roll the optimistic bubble back so the admin can edit and retry
      // rather than leaving an unanswered question in the thread.
      setMessages((current) => current.filter((m) => m.id !== optimistic.id));
      setQuestion(trimmed);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  function startNewThread() {
    setSessionId(null);
    setMessages([]);
    setError(null);
    inputRef.current?.focus();
  }

  async function openSession(id) {
    setError(null);

    try {
      const data = await getAnalystSession(id);
      setSessionId(data.id);
      setMessages(data.messages ?? []);
    } catch {
      setError("Couldn't open that conversation.");
    }
  }

  async function removeSession(event, id) {
    event.stopPropagation();

    try {
      await deleteAnalystSession(id);

      if (id === sessionId) startNewThread();
      refreshSessions();
    } catch {
      setError("Couldn't delete that conversation.");
    }
  }

  function askSuggestion(text) {
    setQuestion(text);
    inputRef.current?.focus();
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="analyst-page">
      <aside className="analyst-threads">
        <button type="button" className="analyst-threads__new" onClick={startNewThread}>
          <Plus size={15} />
          <span>New question</span>
        </button>

        <p className="analyst-threads__heading">Recent</p>

        {sessions.length === 0 && (
          <p className="analyst-threads__empty">No conversations yet.</p>
        )}

        <ul className="analyst-threads__list">
          {sessions.map((session) => (
            <li key={session.id}>
              <button
                type="button"
                className={`analyst-threads__item ${
                  session.id === sessionId ? "analyst-threads__item--active" : ""
                }`}
                onClick={() => openSession(session.id)}
              >
                <span className="analyst-threads__title">{session.title || "Untitled"}</span>
                <span
                  className="analyst-threads__delete"
                  role="button"
                  tabIndex={0}
                  aria-label="Delete conversation"
                  onClick={(event) => removeSession(event, session.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") removeSession(event, session.id);
                  }}
                >
                  <Trash2 size={13} />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="analyst-main">
        <header className="analyst-header">
          <div className="analyst-header__title">
            <Database size={18} />
            <div>
              <h1>Data analyst</h1>
              <p>Ask questions about your business documents in plain English.</p>
            </div>
          </div>
        </header>

        <div className="analyst-scroll" ref={scrollRef}>
          {isEmpty && (
            <div className="analyst-welcome">
              <div className="analyst-welcome__icon" aria-hidden="true">
                <Sparkles size={22} />
              </div>

              <h2>What would you like to know?</h2>
              <p>
                I can query your {scope?.document_types?.length ?? 7} document types and
                answer with a summary, a table, and a chart where it helps.
              </p>

              {scope?.document_types?.length > 0 && (
                <div className="analyst-welcome__scope">
                  {scope.document_types.map((type) => (
                    <span key={type} className="analyst-welcome__chip">
                      {type}
                    </span>
                  ))}
                </div>
              )}

              {scope?.suggestions?.length > 0 && (
                <div className="analyst-suggestions">
                  {scope.suggestions.map((suggestion) => (
                    <button
                      key={suggestion.question}
                      type="button"
                      className="analyst-suggestion"
                      onClick={() => askSuggestion(suggestion.question)}
                    >
                      <span className="analyst-suggestion__label">{suggestion.label}</span>
                      <span className="analyst-suggestion__question">{suggestion.question}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((message) => (
            <AnalystMessage key={message.id} message={message} />
          ))}

          {isSending && (
            <div className="analyst-msg analyst-msg--assistant">
              <div className="analyst-msg__avatar" aria-hidden="true">
                <Loader2 size={15} className="analyst-spin" />
              </div>
              <div className="analyst-msg__body">
                <p className="analyst-msg__thinking">
                  Inspecting the schema, writing a query, and checking it&rsquo;s safe to run&hellip;
                </p>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="analyst-error" role="alert">
            {error}
          </div>
        )}

        <form className="analyst-composer" onSubmit={handleSubmit}>
          <textarea
            ref={inputRef}
            className="analyst-composer__input"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              // Enter sends; Shift+Enter makes a newline, matching the chat
              // conventions admins already know from the rest of the app.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="e.g. Which vendor invoiced us the most last quarter?"
            rows={1}
            disabled={isSending}
          />

          <button
            type="submit"
            className="analyst-composer__send"
            disabled={isSending || !question.trim()}
            aria-label="Ask"
          >
            {isSending ? <Loader2 size={16} className="analyst-spin" /> : <Send size={16} />}
          </button>
        </form>

        <p className="analyst-disclaimer">
          Read-only — this assistant can only run SELECT queries and can never modify your data.
        </p>
      </section>
    </div>
  );
}
