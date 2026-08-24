// import { useEffect, useState } from "react";
// import { deleteAppointment, listAppointments, updateAppointment } from "../../services/adminApi.js";
// import StatusBadge from "./StatusBadge.jsx";

// const STATUS_OPTIONS = ["booked", "cancelled", "completed"];

// export default function AppointmentList() {
//   const [appointments, setAppointments] = useState([]);
//   const [statusFilter, setStatusFilter] = useState("");
//   const [isLoading, setIsLoading] = useState(true);
//   const [error, setError] = useState(null);
//   const [busyId, setBusyId] = useState(null);

//   useEffect(() => {
//     setIsLoading(true);
//     listAppointments(statusFilter ? { status: statusFilter } : {})
//       .then((data) => setAppointments(data.appointments))
//       .catch(() => setError("Couldn't load appointments."))
//       .finally(() => setIsLoading(false));
//   }, [statusFilter]);

//   async function handleStatusChange(appointment, status) {
//     setBusyId(appointment.id);
//     try {
//       const updated = await updateAppointment(appointment.id, { status });
//       setAppointments((prev) => prev.map((a) => (a.id === appointment.id ? updated : a)));
//     } finally {
//       setBusyId(null);
//     }
//   }

//   async function handleDelete(id) {
//     if (!confirm("Permanently delete this appointment record?")) return;
//     setBusyId(id);
//     try {
//       await deleteAppointment(id);
//       setAppointments((prev) => prev.filter((a) => a.id !== id));
//     } finally {
//       setBusyId(null);
//     }
//   }

//   return (
//     <div className="catalog-section">
//       <div className="appointment-filters">
//         <label>
//           Status
//           <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
//             <option value="">All</option>
//             {STATUS_OPTIONS.map((status) => (
//               <option key={status} value={status}>
//                 {status}
//               </option>
//             ))}
//           </select>
//         </label>
//       </div>

//       {isLoading && <p>Loading appointments…</p>}
//       {error && <p className="admin-dashboard__error">{error}</p>}

//       {!isLoading && !error && appointments.length === 0 && (
//         <p className="document-list__empty">No appointments found.</p>
//       )}

//       {!isLoading && !error && appointments.length > 0 && (
//         <table className="data-table">
//           <thead>
//             <tr>
//               <th>Customer</th>
//               <th>Service</th>
//               <th>Staff</th>
//               <th>When</th>
//               <th>Status</th>
//               <th aria-label="Actions" />
//             </tr>
//           </thead>
//           <tbody>
//             {appointments.map((appt) => (
//               <tr key={appt.id}>
//                 <td>
//                   <span className="document-list__filename">{appt.customer_name}</span>
//                   <br />
//                   {appt.customer_email}
//                   <br />
//                   {appt.customer_phone}
//                 </td>
//                 <td>{appt.service_name}</td>
//                 <td>{appt.staff_name}</td>
//                 <td>
//                   {appt.appointment_date} · {appt.start_time}–{appt.end_time}
//                 </td>
//                 <td>
//                   <StatusBadge status={appt.status} />
//                 </td>
//                 <td className="document-list__actions">
//                   <select
//                     value={appt.status}
//                     disabled={busyId === appt.id}
//                     onChange={(e) => handleStatusChange(appt, e.target.value)}
//                   >
//                     {STATUS_OPTIONS.map((status) => (
//                       <option key={status} value={status}>
//                         {status}
//                       </option>
//                     ))}
//                   </select>
//                   <button
//                     type="button"
//                     className="document-list__delete"
//                     disabled={busyId === appt.id}
//                     onClick={() => handleDelete(appt.id)}
//                   >
//                     Delete
//                   </button>
//                 </td>
//               </tr>
//             ))}
//           </tbody>
//         </table>
//       )}
//     </div>
//   );
// }


import { useEffect, useState } from "react";
import { usePagination } from "../../hooks/usePagination.js";
import { deleteAppointment, listAppointments, updateAppointment } from "../../services/adminApi.js";
import { Calendar, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import StatusBadge from "./Statusbadge.jsx";

const STATUS_OPTIONS = ["booked", "cancelled", "completed"];
const PAGE_SIZE = 8;

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

  const { page, setPage, totalPages, totalItems, startIndex, endIndex, paginated } = usePagination(
    appointments,
    PAGE_SIZE
  );

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

      {isLoading && <LoadingState label="Loading appointments…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && appointments.length === 0 && (
        <EmptyState
          icon={Calendar}
          title="No appointments found"
          description="Bookings made through the chat assistant will show up here."
        />
      )}

      {!isLoading && !error && appointments.length > 0 && (
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
                {paginated.map((appt) => (
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
            totalItems={totalItems}
            startIndex={startIndex}
            endIndex={endIndex}
            itemLabel="appointments"
          />
        </>
      )}
    </div>
  );
}