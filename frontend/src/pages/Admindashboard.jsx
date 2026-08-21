import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppointmentList from "../components/admin/AppointmentList.jsx";
import DocumentList from "../components/admin/DocumentList.jsx";
import DocumentUpload from "../components/admin/DocumentUpload.jsx";
import ServiceList from "../components/admin/ServiceList.jsx";
import StaffList from "../components/admin/StaffList.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { listDocuments, listServices, listStaff } from "../services/adminApi.js";

const TABS = [
  { id: "knowledge-base", label: "Knowledge base" },
  { id: "catalog", label: "Services & staff" },
  { id: "appointments", label: "Appointments" },
];

export default function AdminDashboard() {
  const { admin, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(TABS[0].id);

  const [documents, setDocuments] = useState([]);
  const [services, setServices] = useState([]);
  const [staff, setStaff] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([listDocuments(), listServices(), listStaff()])
      .then(([docsData, servicesData, staffData]) => {
        setDocuments(docsData.documents);
        setServices(servicesData);
        setStaff(staffData);
      })
      .catch(() => setError("Couldn't load dashboard data."))
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
          <h1>Admin dashboard</h1>
          <p>Signed in as {admin?.email}</p>
        </div>
        <button type="button" className="admin-dashboard__logout" onClick={handleLogout}>
          Log out
        </button>
      </div>

      <nav className="admin-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`admin-tabs__tab ${activeTab === tab.id ? "admin-tabs__tab--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {isLoading && <p>Loading…</p>}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && activeTab === "knowledge-base" && (
        <>
          <DocumentUpload onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />
          <DocumentList documents={documents} onChange={setDocuments} />
        </>
      )}

      {!isLoading && !error && activeTab === "catalog" && (
        <>
          <h2 className="admin-dashboard__section-title">Services</h2>
          <ServiceList services={services} onChange={setServices} />
          <h2 className="admin-dashboard__section-title">Staff</h2>
          <StaffList staff={staff} services={services} onChange={setStaff} />
        </>
      )}

      {!isLoading && !error && activeTab === "appointments" && <AppointmentList />}
    </div>
  );
}
