import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Briefcase,
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  MessageCircle,
  Users,
  XCircle,
} from "../../components/common/Icons.jsx";
import { LoadingState } from "../../components/common/Spinner.jsx";
import { getAnalyticsOverview } from "../../services/adminApi.js";

export default function AdminOverview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAnalyticsOverview()
      .then(setData)
      .catch(() => setError("Couldn't load analytics."));
  }, []);

  if (error) return <p className="admin-dashboard__error">{error}</p>;
  if (!data) return <LoadingState label="Loading analytics…" />;

  const primaryStats = [
    { label: "Documents", value: data.total_documents, icon: FileText, hint: `${data.documents_failed} failed` },
    { label: "Services", value: data.total_services, icon: Briefcase },
    { label: "Staff", value: data.total_staff, icon: Users, hint: `${data.active_staff} active` },
    { label: "Customers", value: data.total_customers, icon: Users },
  ];

  const appointmentStats = [
    { label: "Booked", value: data.appointments_by_status.booked, icon: Clock, tone: "booked" },
    { label: "Completed", value: data.appointments_by_status.completed, icon: CheckCircle2, tone: "completed" },
    { label: "Cancelled", value: data.appointments_by_status.cancelled, icon: XCircle, tone: "cancelled" },
  ];

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Analytics overview</h1>
          <p>A snapshot of your business at a glance.</p>
        </div>
      </div>

      <div className="admin-stats">
        {primaryStats.map((stat) => (
          <div key={stat.label} className="admin-stats__card">
            <span className="admin-stats__icon">
              <stat.icon size={18} />
            </span>
            <div>
              <p className="admin-stats__value">{stat.value}</p>
              <p className="admin-stats__label">
                {stat.label}
                {stat.hint && <span className="admin-stats__hint"> · {stat.hint}</span>}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="admin-panel">
        <div className="admin-panel__header">
          <Calendar size={18} />
          <h2>Appointments</h2>
          <span className="admin-panel__badge">{data.total_appointments} total</span>
        </div>
        <div className="admin-mini-stats">
          {appointmentStats.map((stat) => (
            <div key={stat.label} className={`admin-mini-stats__card admin-mini-stats__card--${stat.tone}`}>
              <stat.icon size={16} />
              <span className="admin-mini-stats__value">{stat.value}</span>
              <span className="admin-mini-stats__label">{stat.label}</span>
            </div>
          ))}
        </div>
        <p className="admin-panel__footnote">
          {data.appointments_last_7_days} new appointment{data.appointments_last_7_days === 1 ? "" : "s"} in the
          last 7 days
        </p>
      </div>

      <div className="admin-panel">
        <div className="admin-panel__header">
          <MessageCircle size={18} />
          <h2>Chat activity</h2>
          <span className="admin-panel__badge">{data.total_chat_sessions} total sessions</span>
        </div>
        <p className="admin-panel__footnote">
          {data.chat_sessions_last_7_days} new session{data.chat_sessions_last_7_days === 1 ? "" : "s"} in the
          last 7 days
        </p>
        {data.escalated_chat_sessions > 0 && (
          <p className="admin-panel__footnote" style={{ color: "var(--danger, #d64545)" }}>
            <Link to="/admin/conversations?needsHuman=1" style={{ color: "inherit" }}>
              {data.escalated_chat_sessions} conversation{data.escalated_chat_sessions === 1 ? "" : "s"} handed off
              to a human by the Support Agent — review in Conversations
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}