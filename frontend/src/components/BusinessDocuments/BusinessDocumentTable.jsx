import { useCallback, useEffect, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import {
  deleteBusinessDocument,
  getBusinessDocumentFieldSchemas,
  listBusinessDocuments,
} from "../../services/adminApi.js";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import { Eye, FileText, Trash2 } from "../common/Icons.jsx";
import { formatDateTime, formatFileSize } from "../../utils/businessDocuments.js";
import BusinessDocumentStatusBadge from "./BusinessDocumentStatusBadge.jsx";
import ConfidenceMeter from "./ConfidenceMeter.jsx";
import BusinessDocumentDetailModal from "./BusinessDocumentDetailModal.jsx";

const PAGE_SIZE = 10;
const MAX_PRIMARY_FIELDS = 2;
const POLL_INTERVAL_MS = 4000;
const ACTIVE_STATUSES = new Set(["pending", "processing"]);

// Pick the 1-2 fields that best identify a document at a glance (e.g.
// merchant + receipt number for a receipt, vendor + invoice number for an
// invoice) — required fields first, so the most useful info wins.
function buildPrimaryFields(schemaFields) {
  if (!schemaFields) return [];
  const scalarFields = schemaFields.filter((f) => f.type !== "object_list");
  const ordered = [...scalarFields].sort((a, b) => Number(b.required) - Number(a.required));
  return ordered.slice(0, MAX_PRIMARY_FIELDS);
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return value.toLocaleString();
  return String(value);
}

export default function BusinessDocumentTable({ documentType, reloadSignal = 0, emptyDescription }) {
  const [busyId, setBusyId] = useState(null);
  const [activeDocId, setActiveDocId] = useState(null);
  const [schemaFields, setSchemaFields] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getBusinessDocumentFieldSchemas().then((all) => {
      if (!cancelled) setSchemaFields(all[documentType] || []);
    });
    return () => {
      cancelled = true;
    };
  }, [documentType]);

  const fetcher = useCallback(
    (page, pageSize) => listBusinessDocuments({ page, pageSize, documentType }),
    [documentType]
  );

  const {
    page,
    setPage,
    items: documents,
    setItems: setDocuments,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE, deps: [documentType, reloadSignal] });

  // Uploads process in the background now (Celery) — while any visible row
  // is still pending/processing, poll so the table catches up without a
  // manual refresh.
  useEffect(() => {
    const hasActive = documents.some((d) => ACTIVE_STATUSES.has(d.status));
    if (!hasActive) return undefined;
    const interval = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [documents, reload]);

  async function handleDelete(id) {
    if (!window.confirm("Delete this document and its extracted data?")) return;
    setBusyId(id);
    try {
      await deleteBusinessDocument(id);
      reload();
    } finally {
      setBusyId(null);
    }
  }

  function handleChanged(updated) {
    setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  function handleDeleted(id) {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    reload();
  }

  if (isLoading && documents.length === 0) return <LoadingState label="Loading documents…" />;
  if (error) return <p className="admin-dashboard__error">{error}</p>;

  if (total === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No documents here yet"
        description={emptyDescription || "Upload files from the Upload Documents page to see them here."}
      />
    );
  }

  const primaryFields = buildPrimaryFields(schemaFields);
  const activeDoc = documents.find((d) => d.id === activeDocId) || null;

  return (
    <>
      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Uploaded</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => {
              const isActive = ACTIVE_STATUSES.has(doc.status);

              // e.g. "Grand Nails Salon · 00004" — the doc's own identifying
              // values, not just its filename/size.
              const primarySummary = !isActive
                ? primaryFields
                    .map((f) => formatCellValue(doc.extracted_data?.[f.name]))
                    .filter(Boolean)
                    .join(" · ")
                : "";

              return (
                <tr key={doc.id}>
                  <td className="data-table__file-col">
                    <span className="data-table__primary">
                      <FileText size={14} className="data-table__file-icon" />
                      {doc.original_filename}
                    </span>
                    {isActive ? (
                      <span className="data-table__processing-note">
                        <Spinner size={12} />
                        {doc.status === "pending" ? "Queued for processing…" : "Extracting data…"}
                      </span>
                    ) : (
                      <span className="data-table__secondary">
                        {primarySummary || formatFileSize(doc.file_size_bytes)}
                      </span>
                    )}
                  </td>

                  <td>
                    <BusinessDocumentStatusBadge status={doc.status} />
                    {doc.status === "failed" && doc.error_message && (
                      <span className="data-table__error" title={doc.error_message}>
                        {doc.error_message}
                      </span>
                    )}
                  </td>
                  <td>
                    <ConfidenceMeter value={doc.confidence_score} size="sm" />
                  </td>
                  <td>{formatDateTime(doc.uploaded_at)}</td>
                  <td className="data-table__actions">
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => setActiveDocId(doc.id)}
                      aria-label="View document"
                      title="View full record"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      type="button"
                      className="icon-button icon-button--danger"
                      onClick={() => handleDelete(doc.id)}
                      disabled={busyId === doc.id}
                      aria-label="Delete document"
                      title="Delete document"
                    >
                      {busyId === doc.id ? <Spinner size={14} /> : <Trash2 size={14} />}
                    </button>
                  </td>
                </tr>
              );
            })}
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
        itemLabel="documents"
      />

      {activeDoc && (
        <BusinessDocumentDetailModal
          document={activeDoc}
          onClose={() => setActiveDocId(null)}
          onChanged={handleChanged}
          onDeleted={handleDeleted}
        />
      )}
    </>
  );
}