import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppointmentList from "../components/Admin/AppointmentList.jsx";
import DocumentList from "../components/Admin/DocumentList.jsx";
import DocumentUpload from "../components/Admin/DocumentUpload.jsx";
import ServiceList from "../components/Admin/ServiceList.jsx";
import StaffList from "../components/Admin/StaffList.jsx";
import { Briefcase, FileText, LogOut, Users } from "../components/common/Icons.jsx";
import { LoadingState } from "../components/common/Spinner.jsx";
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

  const stats = [
    { label: "Documents", value: documents.length, icon: FileText },
    { label: "Services", value: services.length, icon: Briefcase },
    { label: "Staff members", value: staff.length, icon: Users },
  ];

  return (
    <div className="admin-dashboard">
      <div className="admin-dashboard__header">
        <div>
          <h1>Admin dashboard</h1>
          <p>Signed in as {admin?.email}</p>
        </div>
        <button type="button" className="admin-dashboard__logout" onClick={handleLogout}>
          <LogOut size={15} />
          Log out
        </button>
      </div>

      {!isLoading && !error && (
        <div className="admin-stats">
          {stats.map((stat) => (
            <div key={stat.label} className="admin-stats__card">
              <span className="admin-stats__icon">
                <stat.icon size={18} />
              </span>
              <div>
                <p className="admin-stats__value">{stat.value}</p>
                <p className="admin-stats__label">{stat.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

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

      {isLoading && <LoadingState label="Loading dashboard…" />}
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