// import { useState } from "react";
// import { createStaff, deleteStaff, updateStaff } from "../../services/adminApi.js";

// const EMPTY_FORM = { name: "", email: "", phone: "", service_ids: [] };

// export default function StaffList({ staff, services, onChange }) {
//   const [form, setForm] = useState(EMPTY_FORM);
//   const [error, setError] = useState(null);
//   const [busyId, setBusyId] = useState(null);

//   function toggleFormService(serviceId) {
//     setForm((prev) => ({
//       ...prev,
//       service_ids: prev.service_ids.includes(serviceId)
//         ? prev.service_ids.filter((id) => id !== serviceId)
//         : [...prev.service_ids, serviceId],
//     }));
//   }

//   async function handleCreate(e) {
//     e.preventDefault();
//     setError(null);
//     try {
//       const created = await createStaff(form);
//       onChange((prev) => [...prev, created]);
//       setForm(EMPTY_FORM);
//     } catch (err) {
//       setError(err.response?.data?.detail || "Couldn't add the staff member.");
//     }
//   }

//   async function toggleActive(member) {
//     setBusyId(member.id);
//     try {
//       const updated = await updateStaff(member.id, { is_active: !member.is_active });
//       onChange((prev) => prev.map((s) => (s.id === member.id ? updated : s)));
//     } finally {
//       setBusyId(null);
//     }
//   }

//   async function handleDelete(id) {
//     if (!confirm("Delete this staff member? Their past appointments stay on record.")) return;
//     setBusyId(id);
//     try {
//       await deleteStaff(id);
//       onChange((prev) => prev.filter((s) => s.id !== id));
//     } finally {
//       setBusyId(null);
//     }
//   }

//   return (
//     <div className="catalog-section">
//       <form className="catalog-form catalog-form--staff" onSubmit={handleCreate}>
//         <input
//           placeholder="Full name"
//           value={form.name}
//           onChange={(e) => setForm({ ...form, name: e.target.value })}
//           required
//         />
//         <input
//           type="email"
//           placeholder="Email"
//           value={form.email}
//           onChange={(e) => setForm({ ...form, email: e.target.value })}
//         />
//         <input
//           placeholder="Phone"
//           value={form.phone}
//           onChange={(e) => setForm({ ...form, phone: e.target.value })}
//         />
//         <div className="catalog-form__services">
//           {services.map((service) => (
//             <label key={service.id} className="catalog-form__service-chip">
//               <input
//                 type="checkbox"
//                 checked={form.service_ids.includes(service.id)}
//                 onChange={() => toggleFormService(service.id)}
//               />
//               {service.name}
//             </label>
//           ))}
//         </div>
//         <button type="submit">Add staff member</button>
//       </form>

//       {error && <p className="admin-dashboard__error">{error}</p>}

//       {staff.length === 0 ? (
//         <p className="document-list__empty">No staff added yet.</p>
//       ) : (
//         <table className="data-table">
//           <thead>
//             <tr>
//               <th>Name</th>
//               <th>Contact</th>
//               <th>Services</th>
//               <th>Status</th>
//               <th aria-label="Actions" />
//             </tr>
//           </thead>
//           <tbody>
//             {staff.map((member) => (
//               <tr key={member.id}>
//                 <td>{member.name}</td>
//                 <td>
//                   {member.email || "—"}
//                   <br />
//                   {member.phone || "—"}
//                 </td>
//                 <td>{member.services.map((s) => s.name).join(", ") || "—"}</td>
//                 <td>
//                   <span className={`status-badge status-badge--${member.is_active ? "completed" : "failed"}`}>
//                     {member.is_active ? "Active" : "Inactive"}
//                   </span>
//                 </td>
//                 <td className="document-list__actions">
//                   <button type="button" disabled={busyId === member.id} onClick={() => toggleActive(member)}>
//                     {member.is_active ? "Deactivate" : "Activate"}
//                   </button>
//                   <button
//                     type="button"
//                     className="document-list__delete"
//                     disabled={busyId === member.id}
//                     onClick={() => handleDelete(member.id)}
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


import { useState } from "react";
import { usePagination } from "../../hooks/usePagination.js";
import { createStaff, deleteStaff, updateStaff } from "../../services/adminApi.js";
import { AlertCircle, Plus, Trash2, Users } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { Spinner } from "../common/Spinner.jsx";

const EMPTY_FORM = { name: "", email: "", phone: "", service_ids: [] };
const PAGE_SIZE = 8;

export default function StaffList({ staff, services, onChange }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  const { page, setPage, totalPages, totalItems, startIndex, endIndex, paginated } = usePagination(
    staff,
    PAGE_SIZE
  );

  function toggleFormService(serviceId) {
    setForm((prev) => ({
      ...prev,
      service_ids: prev.service_ids.includes(serviceId)
        ? prev.service_ids.filter((id) => id !== serviceId)
        : [...prev.service_ids, serviceId],
    }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError(null);
    setIsCreating(true);
    try {
      const created = await createStaff(form);
      onChange((prev) => [...prev, created]);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't add the staff member.");
    } finally {
      setIsCreating(false);
    }
  }

  async function toggleActive(member) {
    setBusyId(member.id);
    try {
      const updated = await updateStaff(member.id, { is_active: !member.is_active });
      onChange((prev) => prev.map((s) => (s.id === member.id ? updated : s)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this staff member? Their past appointments stay on record.")) return;
    setBusyId(id);
    try {
      await deleteStaff(id);
      onChange((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="catalog-section">
      <form className="catalog-form catalog-form--staff" onSubmit={handleCreate}>
        <input
          placeholder="Full name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <input
          placeholder="Phone"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
        <div className="catalog-form__services">
          {services.map((service) => (
            <label key={service.id} className="catalog-form__service-chip">
              <input
                type="checkbox"
                checked={form.service_ids.includes(service.id)}
                onChange={() => toggleFormService(service.id)}
              />
              {service.name}
            </label>
          ))}
        </div>
        <button type="submit" disabled={isCreating}>
          {isCreating ? <Spinner size={14} className="spinner--on-dark" /> : <Plus size={14} />}
          Add staff member
        </button>
      </form>

      {error && (
        <p className="admin-dashboard__error">
          <AlertCircle size={14} />
          {error}
        </p>
      )}

      {staff.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No staff added yet"
          description="Add a staff member using the form above."
        />
      ) : (
        <>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Contact</th>
                  <th>Services</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {paginated.map((member) => (
                  <tr key={member.id}>
                    <td className="data-table__primary">{member.name}</td>
                    <td>
                      <span className="data-table__secondary">{member.email || "—"}</span>
                      <span className="data-table__secondary">{member.phone || "—"}</span>
                    </td>
                    <td>{member.services.map((s) => s.name).join(", ") || "—"}</td>
                    <td>
                      <span className={`status-badge status-badge--${member.is_active ? "completed" : "failed"}`}>
                        {member.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="data-table__actions">
                      <button
                        type="button"
                        className="pill-button"
                        disabled={busyId === member.id}
                        onClick={() => toggleActive(member)}
                      >
                        {busyId === member.id && <Spinner size={12} />}
                        {member.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button
                        type="button"
                        className="icon-button icon-button--danger"
                        disabled={busyId === member.id}
                        onClick={() => handleDelete(member.id)}
                        aria-label="Delete staff member"
                        title="Delete staff member"
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
            itemLabel="staff members"
          />
        </>
      )}
    </div>
  );
}