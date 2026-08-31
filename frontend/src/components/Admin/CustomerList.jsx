import { useCallback, useState } from "react";
import { useServerPagination } from "../../hooks/useServerPagination.js";
import { deleteCustomer, listCustomers } from "../../services/adminApi.js";
import { Pencil, Plus, Trash2, Users } from "../common/Icons.jsx";
import EmptyState from "../common/EmptyState.jsx";
import Pagination from "../common/Pagination.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";
import CustomerModal from "./CustomerModal.jsx";

const PAGE_SIZE = 10;

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString();
}

export default function CustomerList() {
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [modalCustomer, setModalCustomer] = useState(undefined); // undefined = closed, null = add, object = edit

  const fetcher = useCallback((page, pageSize) => listCustomers({ page, pageSize, search }), [search]);

  const {
    page,
    setPage,
    items: customers,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  } = useServerPagination(fetcher, { pageSize: PAGE_SIZE, deps: [search] });

  async function handleDelete(id) {
    if (!window.confirm("Delete this customer profile? Their past appointments stay on record.")) return;
    setBusyId(id);
    try {
      await deleteCustomer(id);
      reload();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="catalog-section">
      <div className="catalog-section__toolbar catalog-section__toolbar--split">
        <input
          className="customer-search-input"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" className="catalog-section__add-btn" onClick={() => setModalCustomer(null)}>
          <Plus size={15} />
          Add customer
        </button>
      </div>

      {isLoading && <LoadingState label="Loading customers…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && total === 0 && (
        <EmptyState
          icon={Users}
          title="No customers found"
          description={search ? "Try a different search term." : "Customers appear here once they chat with your assistant, or add one manually."}
        />
      )}

      {!isLoading && !error && total > 0 && (
        <>
          <div className="data-table-wrapper">
            <table className="data-table">
              <colgroup>
                <col style={{ width: "26%" }} />
                <col style={{ width: "26%" }} />
                <col style={{ width: "18%" }} />
                <col style={{ width: "15%" }} />
                <col style={{ width: "15%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Since</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr key={customer.id}>
                    <td className="data-table__primary">{customer.name || "—"}</td>
                    <td>{customer.email}</td>
                    <td>{customer.phone || "—"}</td>
                    <td>{formatDate(customer.created_at)}</td>
                    <td className="data-table__actions">
                      <button
                        type="button"
                        className="icon-button"
                        disabled={busyId === customer.id}
                        onClick={() => setModalCustomer(customer)}
                        aria-label="Edit customer"
                        title="Edit"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        className="icon-button icon-button--danger"
                        disabled={busyId === customer.id}
                        onClick={() => handleDelete(customer.id)}
                        aria-label="Delete customer"
                        title="Delete customer"
                      >
                        {busyId === customer.id ? <Spinner size={14} /> : <Trash2 size={14} />}
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
            itemLabel="customers"
          />
        </>
      )}

      {modalCustomer !== undefined && (
        <CustomerModal
          customer={modalCustomer}
          onClose={() => setModalCustomer(undefined)}
          onSaved={reload}
        />
      )}
    </div>
  );
}