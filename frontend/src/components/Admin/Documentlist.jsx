// import { useState } from "react";
// import { deleteDocument, reindexDocument } from "../../services/adminApi.js";
// import StatusBadge from "./StatusBadge.jsx";

// function formatSize(bytes) {
//   if (bytes < 1024) return `${bytes} B`;
//   if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
//   return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
// }

// function formatDate(isoString) {
//   return new Date(isoString).toLocaleString();
// }

// export default function DocumentList({ documents, onChange }) {
//   const [busyId, setBusyId] = useState(null);

//   async function handleReindex(id) {
//     setBusyId(id);
//     try {
//       const updated = await reindexDocument(id);
//       onChange((prev) => prev.map((d) => (d.id === id ? updated : d)));
//     } finally {
//       setBusyId(null);
//     }
//   }

//   async function handleDelete(id) {
//     if (!confirm("Delete this document and all its embedded chunks?")) return;
//     setBusyId(id);
//     try {
//       await deleteDocument(id);
//       onChange((prev) => prev.filter((d) => d.id !== id));
//     } finally {
//       setBusyId(null);
//     }
//   }

//   if (documents.length === 0) {
//     return <p className="document-list__empty">No documents uploaded yet.</p>;
//   }

//   return (
//     <table className="document-list">
//       <thead>
//         <tr>
//           <th>File</th>
//           <th>Status</th>
//           <th>Chunks</th>
//           <th>Version</th>
//           <th>Size</th>
//           <th>Uploaded</th>
//           <th aria-label="Actions" />
//         </tr>
//       </thead>
//       <tbody>
//         {documents.map((doc) => (
//           <tr key={doc.id}>
//             <td>
//               <span className="document-list__filename">{doc.original_filename}</span>
//               {doc.status === "failed" && doc.error_message && (
//                 <span className="document-list__error" title={doc.error_message}>
//                   {doc.error_message}
//                 </span>
//               )}
//             </td>
//             <td>
//               <StatusBadge status={doc.status} />
//             </td>
//             <td>{doc.chunk_count}</td>
//             <td>v{doc.version}</td>
//             <td>{formatSize(doc.file_size_bytes)}</td>
//             <td>{formatDate(doc.uploaded_at)}</td>
//             <td className="document-list__actions">
//               <button
//                 type="button"
//                 onClick={() => handleReindex(doc.id)}
//                 disabled={busyId === doc.id}
//                 title="Delete existing vectors and re-process this file"
//               >
//                 Reindex
//               </button>
//               <button
//                 type="button"
//                 className="document-list__delete"
//                 onClick={() => handleDelete(doc.id)}
//                 disabled={busyId === doc.id}
//               >
//                 Delete
//               </button>
//             </td>
//           </tr>
//         ))}
//       </tbody>
//     </table>
//   );
// }

import { useState } from "react";
import { usePagination } from "../../hooks/usePagination.js";
import { deleteDocument, reindexDocument } from "../../services/adminApi.js";
import { FileText, RefreshCw, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { Spinner } from "../common/Spinner.jsx";
import StatusBadge from "./Statusbadge.jsx";

const PAGE_SIZE = 8;

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
  const { page, setPage, totalPages, totalItems, startIndex, endIndex, paginated } = usePagination(
    documents,
    PAGE_SIZE
  );

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
    if (!window.confirm("Delete this document and all its embedded chunks?")) return;
    setBusyId(id);
    try {
      await deleteDocument(id);
      onChange((prev) => prev.filter((d) => d.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  if (documents.length === 0) {
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
            {paginated.map((doc) => (
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
        totalItems={totalItems}
        startIndex={startIndex}
        endIndex={endIndex}
        itemLabel="documents"
      />
    </>
  );
}