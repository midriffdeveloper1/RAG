import { useEffect, useState } from "react";
import { getBusiness, updateBusiness } from "../../services/adminApi.js";
import { AlertCircle, CheckCircle2 } from "../common/Icons.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function buildHoursForm(openingHours) {
  const byDay = Object.fromEntries((openingHours || []).map((oh) => [oh.day_of_week, oh]));
  return DAYS.map((day) => ({
    day_of_week: day,
    open_time: byDay[day]?.open_time || "10:00",
    close_time: byDay[day]?.close_time || "19:00",
    is_closed: byDay[day]?.is_closed || false,
  }));
}

export default function BusinessForm() {
  const [form, setForm] = useState(null);
  const [hours, setHours] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getBusiness()
      .then((business) => {
        setForm({
          name: business.name || "",
          description: business.description || "",
          address: business.address || "",
          phone: business.phone || "",
          email: business.email || "",
        });
        setHours(buildHoursForm(business.opening_hours));
      })
      .catch(() => setError("Couldn't load business details."))
      .finally(() => setIsLoading(false));
  }, []);

  function updateHourField(day, field, value) {
    setHours((prev) => prev.map((h) => (h.day_of_week === day ? { ...h, [field]: value } : h)));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setIsSaving(true);
    try {
      await updateBusiness({ ...form, opening_hours: hours });
      setSaved(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save business details.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return <LoadingState label="Loading business details…" />;
  if (!form) return <p className="admin-dashboard__error">{error}</p>;

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <div className="settings-form__section">
        <h2>Business information</h2>
        <div className="settings-form__grid">
          <label className="settings-form__field">
            Business name
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </label>
          <label className="settings-form__field">
            Contact email
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
          <label className="settings-form__field settings-form__field--wide">
            Address
            <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </label>
          <label className="settings-form__field settings-form__field--wide">
            Description
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What your business does — used by the chatbot to describe you to customers."
            />
          </label>
        </div>
      </div>

      <div className="settings-form__section">
        <h2>Opening hours</h2>
        <div className="hours-grid">
          {hours.map((h) => (
            <div key={h.day_of_week} className="hours-grid__row">
              <span className="hours-grid__day">{h.day_of_week}</span>
              <label className="hours-grid__closed">
                <input
                  type="checkbox"
                  checked={h.is_closed}
                  onChange={(e) => updateHourField(h.day_of_week, "is_closed", e.target.checked)}
                />
                Closed
              </label>
              <input
                type="time"
                value={h.open_time || ""}
                disabled={h.is_closed}
                onChange={(e) => updateHourField(h.day_of_week, "open_time", e.target.value)}
              />
              <span className="hours-grid__sep">to</span>
              <input
                type="time"
                value={h.close_time || ""}
                disabled={h.is_closed}
                onChange={(e) => updateHourField(h.day_of_week, "close_time", e.target.value)}
              />
            </div>
          ))}
        </div>
      </div>

      {error && (
        <p className="admin-dashboard__error">
          <AlertCircle size={14} />
          {error}
        </p>
      )}
      {saved && (
        <p className="settings-form__success">
          <CheckCircle2 size={14} />
          Business details saved.
        </p>
      )}

      <button type="submit" className="settings-form__submit" disabled={isSaving}>
        {isSaving && <Spinner size={14} className="spinner--on-dark" />}
        {isSaving ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}
