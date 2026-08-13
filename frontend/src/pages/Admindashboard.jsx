import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import DocumentList from "../components/admin/DocumentList.jsx";
import DocumentUpload from "../components/admin/DocumentUpload.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { listDocuments } from "../services/adminApi.js";

export default function AdminDashboard() {
  const { admin, logout } = useAuth();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    listDocuments()
      .then((data) => setDocuments(data.documents))
      .catch(() => setError("Couldn't load documents."))
      .finally(() => setIsLoading(false));
  }, []);

  function handleLogout() {
    logout();
    navigate("/admin/login", { replace: true });
  }

  return (
    <div className="admin-dashboard">
      <div className="admin-dashboard__header">
        <div>
          <h1>Knowledge base</h1>
          <p>Signed in as {admin?.email}</p>
        </div>
        <button type="button" className="admin-dashboard__logout" onClick={handleLogout}>
          Log out
        </button>
      </div>

      <DocumentUpload onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />

      {isLoading && <p>Loading documents…</p>}
      {error && <p className="admin-dashboard__error">{error}</p>}
      {!isLoading && !error && (
        <DocumentList documents={documents} onChange={setDocuments} />
      )}
    </div>
  );
}