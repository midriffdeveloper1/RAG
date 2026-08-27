import { useMemo, useState } from "react";
import { createAppointment, updateAppointment } from "../../services/adminApi.js";
import { AlertCircle } from "../common/Icons.jsx";
import Modal from "../common/Modal.jsx";
import { Spinner } from "../common/Spinner.jsx";

const STATUS_OPTIONS = ["booked", "cancelled", "completed"];

function toFormState(appointment) {
  return {
    service_id: appointment?.service_id || "",
    staff_id: appointment?.staff_id || "",
    customer_name: appointment?.customer_name || "",
    customer_email: appointment?.customer_email || "",
    customer_phone: appointment?.customer_phone || "",
    appointment_date: appointment?.appointment_date || "",
    start_time: appointment?.start_time?.slice(0, 5) || "",
    status: appointment?.status || "booked",
    notes: appointment?.notes || "",
  };
}

/**
 * appointment: null (add mode) | appointment object (edit mode)
 * services: full list of { id, name } for the dropdown
 * staff: full list of { id, name, services: [{id, name}] } for the dropdown
 */
export default function AppointmentModal({ appointment, services, staff, onClose, onSaved }) {
  const isEditMode = Boolean(appointment);
  const [form, setForm] = useState(() => toFormState(appointment));
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  // Only show staff who actually provide the selected service — avoids the
  // exact "wrong staff for the treatment" mismatch bug from the chatbot side.
  const eligibleStaff = useMemo(() => {
    if (!form.service_id) return staff;
    return staff.filter((s) => s.services.some((svc) => svc.id === form.service_id));
  }, [staff, form.service_id]);

  function handleServiceChange(service_id) {
    const stillEligible = staff
      .filter((s) => s.services.some((svc) => svc.id === service_id))
      .some((s) => s.id === form.staff_id);
    setForm({ ...form, service_id, staff_id: stillEligible ? form.staff_id : "" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setIsSaving(true);
    try {
      if (isEditMode) {
        const saved = await updateAppointment(appointment.id, form);
        onSaved(saved);
      } else {
        const saved = await createAppointment(form);
        onSaved(saved);
      }
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save this appointment.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal title={isEditMode ? "Edit appointment" : "Add appointment"} onClose={onClose} width={560}>
      <form className="staff-modal-form" onSubmit={handleSubmit}>
        <div className="settings-form__grid">
          <label className="settings-form__field">
            Service
            <select
              value={form.service_id}
              onChange={(e) => handleServiceChange(e.target.value)}
              required
            >
              <option value="" disabled>
                Select a service…
              </option>
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>

          <label className="settings-form__field">
            Staff
            <select
              value={form.staff_id}
              onChange={(e) => setForm({ ...form, staff_id: e.target.value })}
              required
              disabled={!form.service_id}
            >
              <option value="" disabled>
                {form.service_id ? "Select staff…" : "Choose a service first"}
              </option>
              {eligibleStaff.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>

          <label className="settings-form__field">
            Date
            <input
              type="date"
              value={form.appointment_date}
              onChange={(e) => setForm({ ...form, appointment_date: e.target.value })}
              required
            />
          </label>

          <label className="settings-form__field">
            Start time
            <input
              type="time"
              value={form.start_time}
              onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              required
            />
          </label>

          <label className="settings-form__field">
            Customer name
            <input
              value={form.customer_name}
              onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
              required
            />
          </label>

          <label className="settings-form__field">
            Customer email
            <input
              type="email"
              value={form.customer_email}
              onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
              required
            />
          </label>

          <label className="settings-form__field">
            Customer phone
            <input
              value={form.customer_phone}
              onChange={(e) => setForm({ ...form, customer_phone: e.target.value })}
              required
            />
          </label>

          {isEditMode && (
            <label className="settings-form__field">
              Status
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="settings-form__field settings-form__field--wide">
            Notes
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </label>
        </div>

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
            {isSaving ? "Saving…" : isEditMode ? "Save changes" : "Add appointment"}
          </button>
        </div>
      </form>
    </Modal>
  );
}