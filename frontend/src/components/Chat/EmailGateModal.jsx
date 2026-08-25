import { useState } from "react";
import { BUSINESS_NAME } from "../../utils/constants.js";
import { AlertCircle } from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";
import { useCustomer } from "../../context/CustomerContext.jsx";

export default function EmailGateModal() {
  const { identify } = useCustomer();
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await identify(email.trim());
    } catch (err) {
      setError(
        err.response?.data?.detail || "That email doesn't look right — could you double check it?"
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="email-gate" role="dialog" aria-modal="true" aria-labelledby="email-gate-title">
      <div className="email-gate__card">
        <p className="email-gate__eyebrow">{BUSINESS_NAME}</p>
        <h2 id="email-gate-title" className="email-gate__title">
          What&apos;s your email?
        </h2>
        <p className="email-gate__subtitle">
          We&apos;ll use it to pull up your details if you&apos;ve chatted with us before, or set
          up a quick profile if this is your first time.
        </p>

        <form className="email-gate__form" onSubmit={handleSubmit}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="yourname@example.com"
            autoFocus
            required
          />

          {error && (
            <p className="email-gate__error">
              <AlertCircle size={14} />
              {error}
            </p>
          )}

          <button type="submit" disabled={isSubmitting || !email.trim()}>
            {isSubmitting && <Spinner size={14} className="spinner--on-dark" />}
            {isSubmitting ? "Checking…" : "Continue"}
          </button>
        </form>

      </div>
    </div>
  );
}