import { useState } from "react";
import { createService, updateService } from "../../services/adminApi.js";
import { AlertCircle } from "../common/Icons.jsx";
import Modal from "../common/Modal.jsx";
import { Spinner } from "../common/Spinner.jsx";

function toFormState(service) {
  return {
    name: service?.name || "",
    description: service?.description || "",
    price: service?.price ?? "",
    duration_minutes: service?.duration_minutes ?? "",
  };
}


export default function ServiceModal({ service, onClose, onSaved }) {
  const isEditMode = Boolean(service);
  const [form, setForm] = useState(() => toFormState(service));
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setError(null);
    setIsSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        price: form.price === "" ? null : Number(form.price),
        duration_minutes: form.duration_minutes === "" ? null : Number(form.duration_minutes),
      };
      const saved = isEditMode ? await updateService(service.id, payload) : await createService(payload);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save this service.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal title={isEditMode ? "Edit service" : "Add service"} onClose={onClose}>
      <form className="staff-modal-form" onSubmit={handleSubmit}>
        <label className="settings-form__field">
          Service name
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            autoFocus
            required
          />
        </label>

        <label className="settings-form__field">
          Description
          <textarea
            rows={2}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </label>

        <label className="settings-form__field">
          Price (₹)
          <input
            type="number"
            min="0"
            placeholder="Not set"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
          />
        </label>

        <label className="settings-form__field">
          Duration (minutes)
          <input
            type="number"
            min="1"
            placeholder="Not set"
            value={form.duration_minutes}
            onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
          />
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
            {isSaving ? "Saving…" : isEditMode ? "Save changes" : "Add service"}
          </button>
        </div>
      </form>
    </Modal>
  );
}