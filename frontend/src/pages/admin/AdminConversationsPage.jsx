import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { listConversations } from "../../services/adminApi.js";
import { AlertCircle, MessageCircle } from "../../components/common/Icons.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import Pagination from "../../components/common/Pagination.jsx";
import { LoadingState } from "../../components/common/Spinner.jsx";
import StatusBadge from "../../components/Admin/StatusBadge.jsx";
import ConversationModal from "../../components/Admin/ConversationModal.jsx";

const PAGE_SIZE = 10;

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString();
}

export default function AdminConversationsPage() {
  const [needsHumanOnly, setNeedsHumanOnly] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState(null);

  const fetcher = useCallback(
    (page, pageSize) => listConversations({ page, pageSize, needsHuman: needsHumanOnly }),
    [needsHumanOnly]
  );

  const {
    page,
    setPage,
    items: sessions,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE, deps: [needsHumanOnly] });

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Conversations</h1>
          <p>
            Every chat session, and which ones the Support Agent has handed off to your team.
            Escalated conversations stay listed until you mark them resolved.
          </p>
        </div>
      </div>

      <div className="catalog-section">
        <div className="catalog-section__toolbar catalog-section__toolbar--split">
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={needsHumanOnly}
              onChange={(e) => setNeedsHumanOnly(e.target.checked)}
            />
            Needs a human only
          </label>
        </div>

        {isLoading && <LoadingState label="Loading conversations…" />}
        {error && <p className="admin-dashboard__error">{error}</p>}

        {!isLoading && !error && total === 0 && (
          <EmptyState
            icon={needsHumanOnly ? AlertCircle : MessageCircle}
            title={needsHumanOnly ? "No conversations need a human right now" : "No conversations yet"}
            description={
              needsHumanOnly
                ? "Escalated conversations from the Support Agent will show up here."
                : "Conversations appear here once visitors chat with your assistant."
            }
          />
        )}

        {!isLoading && !error && total > 0 && (
          <>
            <div className="data-table-wrapper">
              <table className="data-table">
                <colgroup>
                  <col style={{ width: "22%" }} />
                  <col style={{ width: "20%" }} />
                  <col style={{ width: "14%" }} />
                  <col style={{ width: "14%" }} />
                  <col style={{ width: "15%" }} />
                  <col style={{ width: "15%" }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Conversation</th>
                    <th>Customer</th>
                    <th>Ticket</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Last activity</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr
                      key={session.id}
                      onClick={() => setActiveSessionId(session.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <td className="data-table__primary">{session.title || "(no message yet)"}</td>
                      <td>{session.customer_email || "—"}</td>
                      <td>{session.ticket_number || "—"}</td>
                      <td>
                        {session.needs_human ? (
                          <StatusBadge status="failed" />
                        ) : session.ticket_number ? (
                          <StatusBadge status="completed" />
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>{formatDateTime(session.created_at)}</td>
                      <td>{formatDateTime(session.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={setPage}
              totalItems={total}
              startIndex={startIndex}
              endIndex={endIndex}
              itemLabel="conversations"
            />
          </>
        )}
      </div>

      {activeSessionId && (
        <ConversationModal
          sessionId={activeSessionId}
          onClose={() => setActiveSessionId(null)}
          onResolved={reload}
          onDeleted={reload}
        />
      )}
    </div>
  );
}