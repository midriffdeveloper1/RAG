import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteStaff, listStaff, updateStaff } from "../../services/adminApi.js";
import { Pencil, Plus, Trash2, Users } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import StaffModal from "./StaffModal.jsx";

const PAGE_SIZE = 8;

export default function StaffList({ services = [] }) {
  const [busyId, setBusyId] = useState(null);
  const [modalStaff, setModalStaff] = useState(undefined); // undefined = closed, null = add mode, object = edit mode

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
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE });

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

  function handleSaved(saved) {
    if (modalStaff) {
      setStaff((prev) => prev.map((s) => (s.id === saved.id ? saved : s)));
    } else {
      reload();
    }
  }

  return (
    <div className="catalog-section">
      <div className="catalog-section__toolbar">
        <button type="button" className="catalog-section__add-btn" onClick={() => setModalStaff(null)}>
          <Plus size={15} />
          Add staff
        </button>
      </div>

      {isLoading && <LoadingState label="Loading staff…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && total === 0 && (
        <EmptyState
          icon={Users}
          title="No staff added yet"
          description="Click “Add staff” to add your first team member."
        />
      )}

      {!isLoading && !error && total > 0 && (
        <>
          <div className="data-table-wrapper">
            <table className="data-table">
              <colgroup>
                <col style={{ width: "16%" }} />
                <col style={{ width: "16%" }} />
                <col style={{ width: "38%" }} />
                <col style={{ width: "10%" }} />
                <col style={{ width: "20%" }} />
              </colgroup>
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
                        className="icon-button"
                        disabled={busyId === member.id}
                        onClick={() => setModalStaff(member)}
                        aria-label="Edit staff member"
                        title="Edit"
                      >
                        <Pencil size={14} />
                      </button>
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

      {modalStaff !== undefined && (
        <StaffModal
          staff={modalStaff}
          services={services}
          onClose={() => setModalStaff(undefined)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}