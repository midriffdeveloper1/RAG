import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteAppointment, listAppointments } from "../../services/adminApi.js";
import { Calendar, Pencil, Plus, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import AppointmentModal from "./AppointmentModal.jsx";
import StatusBadge from "./StatusBadge.jsx";

const STATUS_OPTIONS = ["booked", "cancelled", "completed"];
const PAGE_SIZE = 10;

export default function AppointmentList({ services = [], staff = [] }) {
  const [statusFilter, setStatusFilter] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [modalAppointment, setModalAppointment] = useState(undefined); // undefined = closed, null = add, object = edit

  const fetcher = useCallback(
    (page, pageSize) =>
      listAppointments({ page, pageSize, filters: statusFilter ? { status: statusFilter } : {} }),
    [statusFilter]
  );

  const {
    page,
    setPage,
    items: appointments,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE, deps: [statusFilter] });

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
      <div className="catalog-section__toolbar catalog-section__toolbar--split">
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
        <button
          type="button"
          className="catalog-section__add-btn"
          onClick={() => setModalAppointment(null)}
        >
          <Plus size={15} />
          Add appointment
        </button>
      </div>

      {isLoading && <LoadingState label="Loading appointments…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && total === 0 && (
        <EmptyState
          icon={Calendar}
          title="No appointments found"
          description="Bookings made through the chat assistant show up here, or add one manually."
        />
      )}

      {!isLoading && !error && total > 0 && (
        <>
          <div className="data-table-wrapper">
            <table className="data-table">
              <colgroup>
                <col style={{ width: "22%" }} />
                <col style={{ width: "16%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "16%" }} />
                <col style={{ width: "10%" }} />
                <col style={{ width: "22%" }} />
              </colgroup>
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
                      <button
                        type="button"
                        className="icon-button"
                        disabled={busyId === appt.id}
                        onClick={() => setModalAppointment(appt)}
                        aria-label="Edit appointment"
                        title="Edit"
                      >
                        <Pencil size={14} />
                      </button>
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

      {modalAppointment !== undefined && (
        <AppointmentModal
          appointment={modalAppointment}
          services={services}
          staff={staff}
          onClose={() => setModalAppointment(undefined)}
          onSaved={reload}
        />
      )}
    </div>
  );
}