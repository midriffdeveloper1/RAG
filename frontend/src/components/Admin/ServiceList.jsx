import { useState } from "react";
import { createService, deleteService, updateService } from "../../services/adminApi.js";

const EMPTY_FORM = { name: "", description: "", price: "", duration_minutes: "" };

export default function ServiceList({ services, onChange }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  async function handleCreate(e) {
    e.preventDefault();
    setError(null);
    try {
      const created = await createService({
        name: form.name,
        description: form.description || null,
        price: Number(form.price),
        duration_minutes: Number(form.duration_minutes),
      });
      onChange((prev) => [...prev, created]);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't create the service.");
    }
  }

  async function handleFieldUpdate(service, field, value) {
    setBusyId(service.id);
    try {
      const updated = await updateService(service.id, { [field]: value });
      onChange((prev) => prev.map((s) => (s.id === service.id ? updated : s)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this service? Staff assignments will be removed.")) return;
    setBusyId(id);
    try {
      await deleteService(id);
      onChange((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="catalog-section">
      <form className="catalog-form" onSubmit={handleCreate}>
        <input
          placeholder="Service name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <input
          type="number"
          min="0"
          placeholder="Price (₹)"
          value={form.price}
          onChange={(e) => setForm({ ...form, price: e.target.value })}
          required
        />
        <input
          type="number"
          min="1"
          placeholder="Duration (min)"
          value={form.duration_minutes}
          onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
          required
        />
        <button type="submit">Add service</button>
      </form>

      {error && <p className="admin-dashboard__error">{error}</p>}

      {services.length === 0 ? (
        <p className="document-list__empty">No services yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Price</th>
              <th>Duration</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id}>
                <td>{service.name}</td>
                <td>{service.description || "—"}</td>
                <td>
                  <input
                    type="number"
                    className="catalog-inline-input"
                    defaultValue={service.price}
                    disabled={busyId === service.id}
                    onBlur={(e) => {
                      const value = Number(e.target.value);
                      if (value !== service.price) handleFieldUpdate(service, "price", value);
                    }}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    className="catalog-inline-input"
                    defaultValue={service.duration_minutes}
                    disabled={busyId === service.id}
                    onBlur={(e) => {
                      const value = Number(e.target.value);
                      if (value !== service.duration_minutes) {
                        handleFieldUpdate(service, "duration_minutes", value);
                      }
                    }}
                  />{" "}
                  min
                </td>
                <td>
                  <button
                    type="button"
                    className="document-list__delete"
                    disabled={busyId === service.id}
                    onClick={() => handleDelete(service.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
