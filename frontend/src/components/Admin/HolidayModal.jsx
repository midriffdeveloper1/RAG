import { useState } from "react";
import {
  createHoliday,
  deleteHoliday,
  updateHoliday,
} from "../../services/adminApi.js";
import { AlertCircle, Plus, Trash2 } from "../common/Icons.jsx";
import Modal from "../common/Modal.jsx";
import { Spinner } from "../common/Spinner.jsx";

const WEEKDAYS = [
  "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
];

const EMPTY_FORM = {
  kind: "date", // "date" | "recurring"
  date: "",
  day_of_week: "Sunday",
  is_full_day: true,
  start_time: "13:00",
  end_time: "14:00",
  note: "",
};

function describe(holiday) {
  return holiday.date ? holiday.date : `Every ${holiday.day_of_week}`;
}

function scope(holiday) {
  return holiday.is_full_day
    ? "Closed all day"
    : `Closed ${holiday.start_time}\u2013${holiday.end_time}`;
}

export default function HolidayModal({ holidays, onClose, onChanged }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);

  async function handleAdd(e) {
    e.preventDefault();
    setFormError(null);

    if (form.kind === "date" && !form.date) {
      setFormError("Pick a date for a one-off closure.");
      return;
    }
    if (!form.is_full_day && (!form.start_time || !form.end_time)) {
      setFormError("Set both a start and end time for a partial closure.");
      return;
    }

    setIsSaving(true);
    try {
      await createHoliday({
        date: form.kind === "date" ? form.date : null,
        day_of_week: form.kind === "recurring" ? form.day_of_week : null,
        is_full_day: form.is_full_day,
        start_time: form.is_full_day ? null : form.start_time,
        end_time: form.is_full_day ? null : form.end_time,
        note: form.note || null,
      });
      setForm(EMPTY_FORM);
      onChanged();
    } catch (err) {
      setFormError(err?.response?.data?.detail?.[0]?.msg || "Couldn't save that closure.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleToggleActive(holiday) {
    setBusyId(holiday.id);
    try {
      await updateHoliday(holiday.id, { is_active: !holiday.is_active });
      onChanged();
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this holiday/closure?")) return;
    setBusyId(id);
    try {
      await deleteHoliday(id);
      onChanged();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Modal title="Holidays & closures" onClose={onClose} width={620}>
      {holidays.length > 0 ? (
        <ul className="holiday-list">
          {holidays.map((holiday) => (
            <li key={holiday.id} className={`holiday-item ${holiday.is_active ? "" : "holiday-item--inactive"}`}>
              <div className="holiday-item__info">
                <strong>{describe(holiday)}</strong>
                <span className="holiday-item__meta">
                  {scope(holiday)}
                  {holiday.note ? ` \u2014 ${holiday.note}` : ""}
                  {!holiday.is_active ? " (disabled)" : ""}
                </span>
              </div>
              <div className="holiday-item__actions">
                <button
                  type="button"
                  className="holiday-item__toggle"
                  disabled={busyId === holiday.id}
                  onClick={() => handleToggleActive(holiday)}
                >
                  {busyId === holiday.id ? <Spinner size={13} /> : holiday.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  className="staff-modal-form__cancel"
                  disabled={busyId === holiday.id}
                  onClick={() => handleDelete(holiday.id)}
                  aria-label="Delete holiday"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="holiday-summary" style={{ marginBottom: 18 }}>
          No holidays or closures set up yet.
        </p>
      )}

      <form className="staff-modal-form holiday-form" onSubmit={handleAdd}>
        <p className="holiday-form__title">Add a closure</p>

        <div className="holiday-form__radio-group">
          <label className="holiday-form__radio">
            <input
              type="radio"
              checked={form.kind === "date"}
              onChange={() => setForm({ ...form, kind: "date" })}
            />
            One-off date
          </label>
          <label className="holiday-form__radio">
            <input
              type="radio"
              checked={form.kind === "recurring"}
              onChange={() => setForm({ ...form, kind: "recurring" })}
            />
            Recurring weekday
          </label>
        </div>

        <div className="holiday-form__row">
          {form.kind === "date" ? (
            <label className="settings-form__field">
              Date
              <input
                type="date"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
              />
            </label>
          ) : (
            <label className="settings-form__field">
              Day of week
              <select
                value={form.day_of_week}
                onChange={(e) => setForm({ ...form, day_of_week: e.target.value })}
              >
                {WEEKDAYS.map((day) => (
                  <option key={day} value={day}>
                    {day}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="settings-form__field">
            Note (optional)
            <input
              placeholder="e.g. Republic Day, staff lunch break"
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
            />
          </label>
        </div>

        <label className="holiday-form__checkbox">
          <input
            type="checkbox"
            checked={form.is_full_day}
            onChange={(e) => setForm({ ...form, is_full_day: e.target.checked })}
          />
          Closed all day
        </label>

        {!form.is_full_day && (
          <div className="holiday-form__row">
            <label className="settings-form__field">
              Closed from
              <input
                type="time"
                value={form.start_time}
                onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              />
            </label>
            <label className="settings-form__field">
              Closed until
              <input
                type="time"
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              />
            </label>
          </div>
        )}

        {formError && (
          <p className="admin-dashboard__error">
            <AlertCircle size={14} />
            {formError}
          </p>
        )}

        <div className="staff-modal-form__actions">
          <button type="button" className="staff-modal-form__cancel" onClick={onClose}>
            Close
          </button>
          <button type="submit" className="settings-form__submit" disabled={isSaving}>
            {isSaving ? <Spinner size={14} className="spinner--on-dark" /> : <Plus size={14} />}
            {isSaving ? "Adding\u2026" : "Add closure"}
          </button>
        </div>
      </form>
    </Modal>
  );
}