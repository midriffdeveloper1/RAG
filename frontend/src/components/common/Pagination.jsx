import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "./Icons.jsx";

export default function Pagination({
  page,
  totalPages,
  onPageChange,
  totalItems,
  startIndex,
  endIndex,
  itemLabel = "items",
}) {
  if (totalItems === 0) return null;

  return (
    <div className="pagination">
      <p className="pagination__summary">
        Showing <strong>{startIndex}</strong>–<strong>{endIndex}</strong> of{" "}
        <strong>{totalItems}</strong> {itemLabel}
      </p>

      {totalPages > 1 && (
        <div className="pagination__controls">
          <button
            type="button"
            className="pagination__btn"
            onClick={() => onPageChange(1)}
            disabled={page === 1}
            aria-label="First page"
          >
            <ChevronsLeft size={14} />
          </button>
          <button
            type="button"
            className="pagination__btn"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            aria-label="Previous page"
          >
            <ChevronLeft size={14} />
          </button>

          <span className="pagination__page">
            Page {page} of {totalPages}
          </span>

          <button
            type="button"
            className="pagination__btn"
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages}
            aria-label="Next page"
          >
            <ChevronRight size={14} />
          </button>
          <button
            type="button"
            className="pagination__btn"
            onClick={() => onPageChange(totalPages)}
            disabled={page === totalPages}
            aria-label="Last page"
          >
            <ChevronsRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}