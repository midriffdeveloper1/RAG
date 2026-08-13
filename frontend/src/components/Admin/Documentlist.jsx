import { useState } from "react";
import { deleteDocument, reindexDocument } from "../../services/adminApi.js";
import StatusBadge from "./StatusBadge.jsx";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString();
}

export default function DocumentList({ documents, onChange }) {
  const [busyId, setBusyId] = useState(null);

  async function handleReindex(id) {
    setBusyId(id);
    try {
      const updated = await reindexDocument(id);
      onChange((prev) => prev.map((d) => (d.id === id ? updated : d)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this document and all its embedded chunks?")) return;
    setBusyId(id);
    try {
      await deleteDocument(id);
      onChange((prev) => prev.filter((d) => d.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  if (documents.length === 0) {
    return <p className="document-list__empty">No documents uploaded yet.</p>;
  }

  return (
    <table className="document-list">
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
              <span className="document-list__filename">{doc.original_filename}</span>
              {doc.status === "failed" && doc.error_message && (
                <span className="document-list__error" title={doc.error_message}>
                  {doc.error_message}
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
            <td className="document-list__actions">
              <button
                type="button"
                onClick={() => handleReindex(doc.id)}
                disabled={busyId === doc.id}
                title="Delete existing vectors and re-process this file"
              >
                Reindex
              </button>
              <button
                type="button"
                className="document-list__delete"
                onClick={() => handleDelete(doc.id)}
                disabled={busyId === doc.id}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}