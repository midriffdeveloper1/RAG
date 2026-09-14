import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteBusinessDocument, listBusinessDocuments } from "../../services/adminApi.js";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import { Eye, FileText, Trash2 } from "../common/Icons.jsx";
import { formatDateTime, formatFileSize, getHeadline } from "../../utils/businessDocuments.js";
import BusinessDocumentStatusBadge from "./BusinessDocumentStatusBadge.jsx";
import ConfidenceMeter from "./ConfidenceMeter.jsx";
import BusinessDocumentDetailModal from "./BusinessDocumentDetailModal.jsx";

const PAGE_SIZE = 10;

export default function BusinessDocumentTable({ documentType, reloadSignal = 0, emptyDescription }) {
  const [busyId, setBusyId] = useState(null);
  const [activeDocId, setActiveDocId] = useState(null);

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

  if (isLoading) return <LoadingState label="Loading documents…" />;
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

  const activeDoc = documents.find((d) => d.id === activeDocId) || null;

  return (
    <>
      <div className="data-table-wrapper">
        <table className="data-table">
          <colgroup>
            <col style={{ width: "24%" }} />
            <col style={{ width: "24%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "16%" }} />
            <col style={{ width: "10%" }} />
          </colgroup>
          <thead>
            <tr>
              <th>File</th>
              <th>Key details</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Uploaded</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <span className="data-table__primary">
                    <FileText size={14} className="data-table__file-icon" />
                    {doc.original_filename}
                  </span>
                  <span className="data-table__secondary">{formatFileSize(doc.file_size_bytes)}</span>
                </td>
                <td>
                  {getHeadline(doc.document_type, doc.extracted_data) || (
                    <span className="field-value__empty">—</span>
                  )}
                  {doc.missing_fields?.length > 0 && doc.status === "needs_review" && (
                    <span className="data-table__error" title={doc.missing_fields.join(", ")}>
                      Missing {doc.missing_fields.length} field
                      {doc.missing_fields.length === 1 ? "" : "s"}
                    </span>
                  )}
                  {doc.status === "failed" && doc.error_message && (
                    <span className="data-table__error" title={doc.error_message}>
                      {doc.error_message}
                    </span>
                  )}
                </td>
                <td>
                  <BusinessDocumentStatusBadge status={doc.status} />
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
                    title="View extracted data"
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