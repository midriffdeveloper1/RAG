import { useEffect, useState } from "react";
import { listHolidays } from "../../services/adminApi.js";
import { Calendar, Plus } from "../common/Icons.jsx";
import { LoadingState } from "../common/Spinner.jsx";
import HolidayModal from "./HolidayModal.jsx";

export default function HolidayManager() {
  const [holidays, setHolidays] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);

  function reload() {
    setIsLoading(true);
    listHolidays()
      .then((data) => {
        setHolidays(data);
        setError(null);
      })
      .catch(() => setError("Couldn't load holidays."))
      .finally(() => setIsLoading(false));
  }

  useEffect(reload, []);

  const activeCount = holidays.filter((h) => h.is_active).length;
  const inactiveCount = holidays.length - activeCount;

  return (
    <div className="settings-form__section">
      <div className="settings-form__section-header">
        <div>
          <h2>Holidays &amp; closures</h2>
          <p className="settings-form__hint">
            Dates or recurring days the business is closed, or partly closed. The booking
            assistant checks this automatically before offering any appointment slot.
          </p>
        </div>
        <button type="button" className="catalog-section__add-btn" onClick={() => setShowModal(true)}>
          {holidays.length > 0 ? <Calendar size={15} /> : <Plus size={15} />}
          {holidays.length > 0 ? "Manage holidays" : "Add a holiday"}
        </button>
      </div>

      {isLoading && <LoadingState label="Loading holidays…" />}
      {error && <p className="admin-dashboard__error">{error}</p>}

      {!isLoading && !error && (
        <p className="holiday-summary">
          {activeCount === 0
            ? "No active closures set."
            : `${activeCount} active closure${activeCount === 1 ? "" : "s"}${
                inactiveCount > 0 ? `, ${inactiveCount} disabled` : ""
              }.`}
        </p>
      )}

      {showModal && (
        <HolidayModal holidays={holidays} onClose={() => setShowModal(false)} onChanged={reload} />
      )}
    </div>
  );
}