import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteDocument, listDocuments, reindexDocument } from "../../services/adminApi.js";
import { FileText, RefreshCw, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import StatusBadge from "./StatusBadge.jsx";

const PAGE_SIZE = 8;

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString();
}

export default function DocumentList({ reloadSignal = 0 }) {
  const [busyId, setBusyId] = useState(null);

  const fetcher = useCallback(
    (page, pageSize) => listDocuments({ page, pageSize }),
    []
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
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE, deps: [reloadSignal] });

  async function handleReindex(id) {
    setBusyId(id);
    try {
      const updated = await reindexDocument(id);
      setDocuments((prev) => prev.map((d) => (d.id === id ? updated : d)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this document and all its embedded chunks?")) return;
    setBusyId(id);
    try {
      await deleteDocument(id);
      reload();
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading) return <LoadingState label="Loading documents…" />;
  if (error) return <p className="admin-dashboard__error">{error}</p>;

  if (total === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No documents uploaded yet"
        description="Upload a PDF or Word document above to build the knowledge base."
      />
    );
  }

  return (
    <>
      <div className="data-table-wrapper">
        <table className="data-table">
          <colgroup>
            <col style={{ width: "28%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "10%" }} />
            <col style={{ width: "10%" }} />
            <col style={{ width: "11%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "10%" }} />
          </colgroup>
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Chunks</th>
              <th>Version</th>
              <th>Size</th>
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
                  {doc.status === "failed" && doc.error_message && (
                    <span className="data-table__error" title={doc.error_message}>
                      {doc.error_message}
                    </span>
                  )}
                  {doc.status === "completed" && doc.extraction_summary && (
                    <span className="data-table__extraction-note" title={doc.extraction_summary}>
                      {doc.extraction_summary}
                    </span>
                  )}
                </td>
                <td>
                  <StatusBadge status={doc.status} />
                </td>
                <td>{doc.chunk_count}</td>
                <td>v{doc.version}</td>
                <td>{formatSize(doc.file_size_bytes)}</td>
                <td>{formatDate(doc.uploaded_at)}</td>
                <td className="data-table__actions">
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => handleReindex(doc.id)}
                    disabled={busyId === doc.id}
                    title="Delete existing vectors and re-process this file"
                    aria-label="Reindex document"
                  >
                    {busyId === doc.id ? <Spinner size={14} /> : <RefreshCw size={14} />}
                  </button>
                  <button
                    type="button"
                    className="icon-button icon-button--danger"
                    onClick={() => handleDelete(doc.id)}
                    disabled={busyId === doc.id}
                    aria-label="Delete document"
                    title="Delete document"
                  >
                    <Trash2 size={14} />
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
    </>
  );
}