import { useState } from "react";
import DocumentList from "../../components/Admin/DocumentList.jsx";
import DocumentUpload from "../../components/Admin/DocumentUpload.jsx";

export default function AdminKnowledgeBasePage() {
  const [reloadSignal, setReloadSignal] = useState(0);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Knowledge base</h1>
          <p>Upload documents (PDF/Word) the chatbot's RAG pipeline retrieves answers from.</p>
        </div>
      </div>

      <DocumentUpload onUploaded={() => setReloadSignal((n) => n + 1)} />
      <DocumentList reloadSignal={reloadSignal} />
    </div>
  );
}
