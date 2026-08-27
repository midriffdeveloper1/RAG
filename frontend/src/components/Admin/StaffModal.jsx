import { useState } from "react";
import { createStaff, updateStaff } from "../../services/adminApi.js";
import { AlertCircle } from "../common/Icons.jsx";
import Modal from "../common/Modal.jsx";
import MultiSelectDropdown from "../common/MultiSelectDropdown.jsx";
import { Spinner } from "../common/Spinner.jsx";

function toFormState(staff) {
  return {
    name: staff?.name || "",
    email: staff?.email || "",
    phone: staff?.phone || "",
    is_active: staff?.is_active ?? true,
    service_ids: staff?.services?.map((s) => s.id) || [],
  };
}

export default function StaffModal({ staff, services, onClose, onSaved }) {
  const isEditMode = Boolean(staff);
  const [form, setForm] = useState(() => toFormState(staff));
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const serviceOptions = services.map((s) => ({ value: s.id, label: s.name }));

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setError(null);
    setIsSaving(true);
    try {
      const saved = isEditMode ? await updateStaff(staff.id, form) : await createStaff(form);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save this staff member.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal title={isEditMode ? "Edit staff member" : "Add staff member"} onClose={onClose}>
      <form className="staff-modal-form" onSubmit={handleSubmit}>
        <label className="settings-form__field">
          Full name
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            autoFocus
            required
          />
        </label>

        <label className="settings-form__field">
          Email
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </label>

        <label className="settings-form__field">
          Phone
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </label>

        <label className="settings-form__field">
          Services
          <MultiSelectDropdown
            options={serviceOptions}
            selected={form.service_ids}
            onChange={(service_ids) => setForm({ ...form, service_ids })}
            placeholder="Select services this person provides…"
          />
        </label>

        {isEditMode && (
          <label className="settings-toggle">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            <span className="settings-toggle__track" aria-hidden="true" />
            Active (can be booked)
          </label>
        )}

        {error && (
          <p className="admin-dashboard__error">
            <AlertCircle size={14} />
            {error}
          </p>
        )}

        <div className="staff-modal-form__actions">
          <button type="button" className="staff-modal-form__cancel" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="settings-form__submit" disabled={isSaving}>
            {isSaving && <Spinner size={14} className="spinner--on-dark" />}
            {isSaving ? "Saving…" : isEditMode ? "Save changes" : "Add staff member"}
          </button>
        </div>
      </form>
    </Modal>
  );
}