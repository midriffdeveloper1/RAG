import { useEffect, useState } from "react";
import { deleteAppointment, listAppointments, updateAppointment } from "../../services/adminApi.js";
import StatusBadge from "./StatusBadge.jsx";

const STATUS_OPTIONS = ["booked", "cancelled", "completed"];

export default function AppointmentList() {
  const [appointments, setAppointments] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    setIsLoading(true);
    listAppointments(statusFilter ? { status: statusFilter } : {})
      .then((data) => setAppointments(data.appointments))
      .catch(() => setError("Couldn't load appointments."))
      .finally(() => setIsLoading(false));
  }, [statusFilter]);

  async function handleStatusChange(appointment, status) {
    setBusyId(appointment.id);
    try {
      const updated = await updateAppointment(appointment.id, { status });
      setAppointments((prev) => prev.map((a) => (a.id === appointment.id ? updated : a)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Permanently delete this appointment record?")) return;
    setBusyId(id);
    try {
      await deleteAppointment(id);
      setAppointments((prev) => prev.filter((a) => a.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="catalog-section">
      <div className="appointment-filters">
        <label>
          Status
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <p>Loading appointments…</p>}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && appointments.length === 0 && (
        <p className="document-list__empty">No appointments found.</p>
      )}

      {!isLoading && !error && appointments.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Service</th>
              <th>Staff</th>
              <th>When</th>
              <th>Status</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {appointments.map((appt) => (
              <tr key={appt.id}>
                <td>
                  <span className="document-list__filename">{appt.customer_name}</span>
                  <br />
                  {appt.customer_email}
                  <br />
                  {appt.customer_phone}
                </td>
                <td>{appt.service_name}</td>
                <td>{appt.staff_name}</td>
                <td>
                  {appt.appointment_date} · {appt.start_time}–{appt.end_time}
                </td>
                <td>
                  <StatusBadge status={appt.status} />
                </td>
                <td className="document-list__actions">
                  <select
                    value={appt.status}
                    disabled={busyId === appt.id}
                    onChange={(e) => handleStatusChange(appt, e.target.value)}
                  >
                    {STATUS_OPTIONS.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="document-list__delete"
                    disabled={busyId === appt.id}
                    onClick={() => handleDelete(appt.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
