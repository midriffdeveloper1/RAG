import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteAppointment, listAppointments, updateAppointment } from "../../services/adminApi.js";
import { Calendar, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import StatusBadge from "./StatusBadge.jsx";

const STATUS_OPTIONS = ["booked", "cancelled", "completed"];
const PAGE_SIZE = 8;

export default function AppointmentList() {
  const [statusFilter, setStatusFilter] = useState("");
  const [busyId, setBusyId] = useState(null);

  const fetcher = useCallback(
    (page, pageSize) =>
      listAppointments({ page, pageSize, filters: statusFilter ? { status: statusFilter } : {} }),
    [statusFilter]
  );

  const {
    page,
    setPage,
    items: appointments,
    setItems: setAppointments,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE, deps: [statusFilter] });

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
    if (!window.confirm("Permanently delete this appointment record?")) return;
    setBusyId(id);
    try {
      await deleteAppointment(id);
      reload();
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

      {isLoading && <LoadingState label="Loading appointments…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && total === 0 && (
        <EmptyState
          icon={Calendar}
          title="No appointments found"
          description="Bookings made through the chat assistant will show up here."
        />
      )}

      {!isLoading && !error && total > 0 && (
        <>
          <div className="data-table-wrapper">
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
                      <span className="data-table__primary">{appt.customer_name}</span>
                      <span className="data-table__secondary">{appt.customer_email}</span>
                      <span className="data-table__secondary">{appt.customer_phone}</span>
                    </td>
                    <td>{appt.service_name}</td>
                    <td>{appt.staff_name}</td>
                    <td>
                      {appt.appointment_date} · {appt.start_time}–{appt.end_time}
                    </td>
                    <td>
                      <StatusBadge status={appt.status} />
                    </td>
                    <td className="data-table__actions">
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
                        className="icon-button icon-button--danger"
                        disabled={busyId === appt.id}
                        onClick={() => handleDelete(appt.id)}
                        aria-label="Delete appointment"
                        title="Delete appointment"
                      >
                        {busyId === appt.id ? <Spinner size={14} /> : <Trash2 size={14} />}
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
            itemLabel="appointments"
          />
        </>
      )}
    </div>
  );
}
