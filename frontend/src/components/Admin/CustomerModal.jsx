import { useState } from "react";
import { createCustomer, updateCustomer } from "../../services/adminApi.js";
import { AlertCircle } from "../common/Icons.jsx";
import Modal from "../common/Modal.jsx";
import { Spinner } from "../common/Spinner.jsx";

function toFormState(customer) {
  return {
    email: customer?.email || "",
    name: customer?.name || "",
    phone: customer?.phone || "",
  };
}

/**
 * customer: null (add mode) | customer object (edit mode)
 */
export default function CustomerModal({ customer, onClose, onSaved }) {
  const isEditMode = Boolean(customer);
  const [form, setForm] = useState(() => toFormState(customer));
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.email.trim()) return;
    setError(null);
    setIsSaving(true);
    try {
      const payload = {
        email: form.email.trim(),
        name: form.name.trim() || null,
        phone: form.phone.trim() || null,
      };
      const saved = isEditMode
        ? await updateCustomer(customer.id, payload)
        : await createCustomer(payload);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save this customer.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal title={isEditMode ? "Edit customer" : "Add customer"} onClose={onClose}>
      <form className="staff-modal-form" onSubmit={handleSubmit}>
        <label className="settings-form__field">
          Email
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            autoFocus
            required
          />
        </label>

        <label className="settings-form__field">
          Full name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>

        <label className="settings-form__field">
          Phone
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </label>

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
            {isSaving ? "Saving…" : isEditMode ? "Save changes" : "Add customer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}