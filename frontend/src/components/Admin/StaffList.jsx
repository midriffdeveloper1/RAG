import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { createStaff, deleteStaff, listStaff, updateStaff } from "../../services/adminApi.js";
import { AlertCircle, Plus, Trash2, Users } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";

const EMPTY_FORM = { name: "", email: "", phone: "", service_ids: [] };
const PAGE_SIZE = 8;

export default function StaffList({ services = [] }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  const fetcher = useCallback((page, pageSize) => listStaff({ page, pageSize }), []);

  const {
    page,
    setPage,
    items: staff,
    setItems: setStaff,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error: loadError,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE });

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
      await createStaff(form);
      setForm(EMPTY_FORM);
      reload();
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
      setStaff((prev) => prev.map((s) => (s.id === member.id ? updated : s)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this staff member? Their past appointments stay on record.")) return;
    setBusyId(id);
    try {
      await deleteStaff(id);
      reload();
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

      {isLoading && <LoadingState label="Loading staff…" />}
      {loadError && <p className="admin-dashboard__error">{loadError}</p>}

      {!isLoading && !loadError && total === 0 && (
        <EmptyState
          icon={Users}
          title="No staff added yet"
          description="Add a staff member using the form above."
        />
      )}

      {!isLoading && !loadError && total > 0 && (
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
                {staff.map((member) => (
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
            totalItems={total}
            startIndex={startIndex}
            endIndex={endIndex}
            itemLabel="staff members"
          />
        </>
      )}
    </div>
  );
}
