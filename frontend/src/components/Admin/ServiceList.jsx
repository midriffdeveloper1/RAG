import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { createService, deleteService, listServices, updateService } from "../../services/adminApi.js";
import { AlertCircle, Briefcase, Plus, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";

const EMPTY_FORM = { name: "", description: "", price: "", duration_minutes: "" };
const PAGE_SIZE = 8;

export default function ServiceList() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  const fetcher = useCallback((page, pageSize) => listServices({ page, pageSize }), []);

  const {
    page,
    setPage,
    items: services,
    setItems: setServices,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error: loadError,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE });

  async function handleCreate(e) {
    e.preventDefault();
    setError(null);
    setIsCreating(true);
    try {
      await createService({
        name: form.name,
        description: form.description || null,
        price: Number(form.price),
        duration_minutes: Number(form.duration_minutes),
      });
      setForm(EMPTY_FORM);
      reload();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't create the service.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleFieldUpdate(service, field, value) {
    setBusyId(service.id);
    try {
      const updated = await updateService(service.id, { [field]: value });
      setServices((prev) => prev.map((s) => (s.id === service.id ? updated : s)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this service? Staff assignments will be removed.")) return;
    setBusyId(id);
    try {
      await deleteService(id);
      reload();
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
        <button type="submit" disabled={isCreating}>
          {isCreating ? <Spinner size={14} className="spinner--on-dark" /> : <Plus size={14} />}
          Add service
        </button>
      </form>

      {error && (
        <p className="admin-dashboard__error">
          <AlertCircle size={14} />
          {error}
        </p>
      )}

      {isLoading && <LoadingState label="Loading services…" />}
      {loadError && <p className="admin-dashboard__error">{loadError}</p>}

      {!isLoading && !loadError && total === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No services yet"
          description="Add your first service using the form above."
        />
      )}

      {!isLoading && !loadError && total > 0 && (
        <>
          <div className="data-table-wrapper">
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
                    <td className="data-table__primary">{service.name}</td>
                    <td>{service.description || "—"}</td>
                    <td>
                      <span className="catalog-inline-prefix">₹</span>
                      <input
                        type="number"
                        className="catalog-inline-input"
                        placeholder="Not set"
                        defaultValue={service.price ?? ""}
                        disabled={busyId === service.id}
                        onBlur={(e) => {
                          const value = e.target.value === "" ? null : Number(e.target.value);
                          if (value !== service.price) handleFieldUpdate(service, "price", value);
                        }}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        className="catalog-inline-input"
                        placeholder="Not set"
                        defaultValue={service.duration_minutes ?? ""}
                        disabled={busyId === service.id}
                        onBlur={(e) => {
                          const value = e.target.value === "" ? null : Number(e.target.value);
                          if (value !== service.duration_minutes) {
                            handleFieldUpdate(service, "duration_minutes", value);
                          }
                        }}
                      />{" "}
                      min
                    </td>
                    <td className="data-table__actions">
                      <button
                        type="button"
                        className="icon-button icon-button--danger"
                        disabled={busyId === service.id}
                        onClick={() => handleDelete(service.id)}
                        aria-label="Delete service"
                        title="Delete service"
                      >
                        {busyId === service.id ? <Spinner size={14} /> : <Trash2 size={14} />}
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
            itemLabel="services"
          />
        </>
      )}
    </div>
  );
}