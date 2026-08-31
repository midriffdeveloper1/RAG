import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteService, listServices } from "../../services/adminApi.js";
import { Briefcase, Pencil, Plus, Trash2 } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import ServiceModal from "./ServiceModal.jsx";

const PAGE_SIZE = 10;

export default function ServiceList() {
  const [busyId, setBusyId] = useState(null);
  const [modalService, setModalService] = useState(undefined); 
  const fetcher = useCallback((page, pageSize) => listServices({ page, pageSize }), []);

  const {
    page,
    setPage,
    items: services,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE });

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
      <div className="catalog-section__toolbar">
        <button type="button" className="catalog-section__add-btn" onClick={() => setModalService(null)}>
          <Plus size={15} />
          Add service
        </button>
      </div>

      {isLoading && <LoadingState label="Loading services…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && total === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No services yet"
          description="Click “Add service” to add your first bookable service."
        />
      )}

      {!isLoading && !error && total > 0 && (
        <>
          <div className="data-table-wrapper">
            <table className="data-table">
              <colgroup>
                <col style={{ width: "20%" }} />
                <col style={{ width: "40%" }} />
                <col style={{ width: "13%" }} />
                <col style={{ width: "13%" }} />
                <col style={{ width: "14%" }} />
              </colgroup>
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
                    <td>{service.price != null ? `₹${service.price}` : "Not set"}</td>
                    <td>{service.duration_minutes != null ? `${service.duration_minutes} min` : "Not set"}</td>
                    <td className="data-table__actions">
                      <button
                        type="button"
                        className="icon-button"
                        disabled={busyId === service.id}
                        onClick={() => setModalService(service)}
                        aria-label="Edit service"
                        title="Edit"
                      >
                        <Pencil size={14} />
                      </button>
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

      {modalService !== undefined && (
        <ServiceModal
          service={modalService}
          onClose={() => setModalService(undefined)}
          onSaved={reload}
        />
      )}
    </div>
  );
}