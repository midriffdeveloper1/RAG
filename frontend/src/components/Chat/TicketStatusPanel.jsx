import { useState } from "react";
import { getTicketStatus } from "../../services/api.js";
import { AlertCircle, ChevronDown } from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";

export default function TicketStatusPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [ticketNumber, setTicketNumber] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isChecking, setIsChecking] = useState(false);

  async function handleCheck(e) {
    e.preventDefault();
    const trimmed = ticketNumber.trim();
    if (!trimmed) return;

    setIsChecking(true);
    setError(null);
    setResult(null);
    try {
      const data = await getTicketStatus(trimmed);
      setResult(data);
    } catch (err) {
      setError(
        err?.response?.status === 404
          ? "No ticket found with that number."
          : "Couldn't check that ticket right now."
      );
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <div className="chat-sidebar__ticket-panel">
      <button
        type="button"
        className="chat-sidebar__ticket-toggle"
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
      >
        <AlertCircle size={13} />
        <span>Check ticket status</span>
        <ChevronDown
          size={13}
          className={`chat-sidebar__ticket-chevron ${isOpen ? "chat-sidebar__ticket-chevron--open" : ""}`}
        />
      </button>

      {isOpen && (
        <form className="chat-sidebar__ticket-form" onSubmit={handleCheck}>
          <input
            placeholder="e.g. TCK-7K4M9QRT"
            value={ticketNumber}
            onChange={(e) => setTicketNumber(e.target.value)}
          />
          <button type="submit" className="chat-sidebar__ticket-submit" disabled={isChecking}>
            {isChecking ? <Spinner size={12} /> : "Check"}
          </button>

          {error && <p className="chat-sidebar__ticket-error">{error}</p>}

          {result && (
            <div
              className={`chat-sidebar__ticket-result chat-sidebar__ticket-result--${result.status}`}
            >
              <strong>{result.ticket_number}</strong>
              <span>{result.status === "open" ? "Open \u2014 our team has this" : "Resolved"}</span>
            </div>
          )}
        </form>
      )}
    </div>
  );
}