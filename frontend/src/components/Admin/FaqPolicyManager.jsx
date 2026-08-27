import { useEffect, useState } from "react";
import {
  createFaq,
  createPolicy,
  deleteFaq,
  deletePolicy,
  listFaqs,
  listPolicies,
  updateFaq,
  updatePolicy,
} from "../../services/adminApi.js";
import { Plus, Trash2 } from "../common/Icons.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";

const EMPTY_FAQ = { question: "", answer: "", category: "" };
const EMPTY_POLICY = { title: "", content: "" };

export default function FaqPolicyManager() {
  const [faqs, setFaqs] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [faqForm, setFaqForm] = useState(EMPTY_FAQ);
  const [policyForm, setPolicyForm] = useState(EMPTY_POLICY);
  const [busyId, setBusyId] = useState(null);

  function reload() {
    setIsLoading(true);
    Promise.all([listFaqs(), listPolicies()])
      .then(([faqData, policyData]) => {
        setFaqs(faqData);
        setPolicies(policyData);
        setError(null);
      })
      .catch(() => setError("Couldn't load FAQs and policies."))
      .finally(() => setIsLoading(false));
  }

  useEffect(reload, []);

  async function handleAddFaq(e) {
    e.preventDefault();
    if (!faqForm.question.trim() || !faqForm.answer.trim()) return;
    await createFaq({ ...faqForm, category: faqForm.category || null });
    setFaqForm(EMPTY_FAQ);
    reload();
  }

  async function handleFaqFieldSave(faq, field, value) {
    setBusyId(faq.id);
    try {
      const updated = await updateFaq(faq.id, { [field]: value });
      setFaqs((prev) => prev.map((f) => (f.id === faq.id ? updated : f)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDeleteFaq(id) {
    if (!window.confirm("Delete this FAQ?")) return;
    setBusyId(id);
    try {
      await deleteFaq(id);
      reload();
    } finally {
      setBusyId(null);
    }
  }

  async function handleAddPolicy(e) {
    e.preventDefault();
    if (!policyForm.title.trim() || !policyForm.content.trim()) return;
    await createPolicy(policyForm);
    setPolicyForm(EMPTY_POLICY);
    reload();
  }

  async function handlePolicyFieldSave(policy, field, value) {
    setBusyId(policy.id);
    try {
      const updated = await updatePolicy(policy.id, { [field]: value });
      setPolicies((prev) => prev.map((p) => (p.id === policy.id ? updated : p)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDeletePolicy(id) {
    if (!window.confirm("Delete this policy?")) return;
    setBusyId(id);
    try {
      await deletePolicy(id);
      reload();
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading) return <LoadingState label="Loading FAQs and policies…" />;
  if (error) return <p className="admin-dashboard__error">{error}</p>;

  return (
    <>
      <div className="settings-form__section">
        <h2>FAQs</h2>
        <p className="settings-form__hint">
          Auto-filled from uploaded documents, or add your own below — either way, you can edit
          or delete any entry.
        </p>

        {faqs.length > 0 && (
          <ul className="faq-policy-list">
            {faqs.map((faq) => (
              <li key={faq.id} className="faq-policy-item">
                <input
                  className="faq-policy-item__title-input"
                  defaultValue={faq.question}
                  disabled={busyId === faq.id}
                  onBlur={(e) => {
                    if (e.target.value !== faq.question) handleFaqFieldSave(faq, "question", e.target.value);
                  }}
                />
                <textarea
                  rows={2}
                  defaultValue={faq.answer}
                  disabled={busyId === faq.id}
                  onBlur={(e) => {
                    if (e.target.value !== faq.answer) handleFaqFieldSave(faq, "answer", e.target.value);
                  }}
                />
                <button
                  type="button"
                  className="icon-button icon-button--danger"
                  disabled={busyId === faq.id}
                  onClick={() => handleDeleteFaq(faq.id)}
                  aria-label="Delete FAQ"
                >
                  {busyId === faq.id ? <Spinner size={14} /> : <Trash2 size={14} />}
                </button>
              </li>
            ))}
          </ul>
        )}

        <form className="faq-policy-add-form" onSubmit={handleAddFaq}>
          <input
            placeholder="Question (e.g. Do you accept walk-ins?)"
            value={faqForm.question}
            onChange={(e) => setFaqForm({ ...faqForm, question: e.target.value })}
          />
          <textarea
            rows={2}
            placeholder="Answer"
            value={faqForm.answer}
            onChange={(e) => setFaqForm({ ...faqForm, answer: e.target.value })}
          />
          <button type="submit">
            <Plus size={14} />
            Add FAQ
          </button>
        </form>
      </div>

      <div className="settings-form__section">
        <h2>Policies</h2>
        <p className="settings-form__hint">
          Cancellation rules, deposits, age restrictions, etc. — also auto-filled from uploaded
          documents when mentioned.
        </p>

        {policies.length > 0 && (
          <ul className="faq-policy-list">
            {policies.map((policy) => (
              <li key={policy.id} className="faq-policy-item">
                <input
                  className="faq-policy-item__title-input"
                  defaultValue={policy.title}
                  disabled={busyId === policy.id}
                  onBlur={(e) => {
                    if (e.target.value !== policy.title) handlePolicyFieldSave(policy, "title", e.target.value);
                  }}
                />
                <textarea
                  rows={2}
                  defaultValue={policy.content}
                  disabled={busyId === policy.id}
                  onBlur={(e) => {
                    if (e.target.value !== policy.content) handlePolicyFieldSave(policy, "content", e.target.value);
                  }}
                />
                <button
                  type="button"
                  className="icon-button icon-button--danger"
                  disabled={busyId === policy.id}
                  onClick={() => handleDeletePolicy(policy.id)}
                  aria-label="Delete policy"
                >
                  {busyId === policy.id ? <Spinner size={14} /> : <Trash2 size={14} />}
                </button>
              </li>
            ))}
          </ul>
        )}

        <form className="faq-policy-add-form" onSubmit={handleAddPolicy}>
          <input
            placeholder="Title (e.g. Cancellation Policy)"
            value={policyForm.title}
            onChange={(e) => setPolicyForm({ ...policyForm, title: e.target.value })}
          />
          <textarea
            rows={2}
            placeholder="Full policy text"
            value={policyForm.content}
            onChange={(e) => setPolicyForm({ ...policyForm, content: e.target.value })}
          />
          <button type="submit">
            <Plus size={14} />
            Add policy
          </button>
        </form>
      </div>
    </>
  );
}