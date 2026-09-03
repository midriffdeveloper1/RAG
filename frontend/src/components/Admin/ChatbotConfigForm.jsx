import { useEffect, useState } from "react";
import { getChatbotConfig, previewSystemPrompt, updateChatbotConfig } from "../../services/adminApi.js";
import { AlertCircle, CheckCircle2, Plus, Trash2 } from "../common/Icons.jsx";
import { LoadingState, Spinner } from "../common/Spinner.jsx";

const TONE_OPTIONS = ["friendly", "professional", "casual", "formal", "playful", "empathetic"];

const VOICE_NAME_OPTIONS = [
  { value: "aura-asteria-en", label: "Asteria — warm, friendly (default)" },
  { value: "aura-luna-en", label: "Luna — calm, approachable" },
  { value: "aura-stella-en", label: "Stella — upbeat, clear" },
  { value: "aura-orion-en", label: "Orion — confident (male)" },
  { value: "aura-arcas-en", label: "Arcas — casual (male)" },
];

export default function ChatbotConfigForm() {
  const [form, setForm] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [newQuestion, setNewQuestion] = useState("");
  const [promptPreview, setPromptPreview] = useState(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  useEffect(() => {
    getChatbotConfig()
      .then(setForm)
      .catch(() => setError("Couldn't load chatbot configuration."))
      .finally(() => setIsLoading(false));
  }, []);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function addQuestion() {
    const q = newQuestion.trim();
    if (!q) return;
    update("suggested_questions", [...form.suggested_questions, q]);
    setNewQuestion("");
  }

  function removeQuestion(index) {
    update(
      "suggested_questions",
      form.suggested_questions.filter((_, i) => i !== index)
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setIsSaving(true);
    try {
      const updated = await updateChatbotConfig(form);
      setForm(updated);
      setSaved(true);
      setPromptPreview(null); // stale now that settings changed — reload on next "Preview" click
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save chatbot configuration.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handlePreview() {
    setIsPreviewLoading(true);
    setPreviewError(null);
    try {
      const prompt = await previewSystemPrompt();
      setPromptPreview(prompt);
    } catch (err) {
      setPreviewError(err.response?.data?.detail || "Couldn't generate a preview.");
    } finally {
      setIsPreviewLoading(false);
    }
  }

  if (isLoading) return <LoadingState label="Loading chatbot configuration…" />;
  if (!form) return <p className="admin-dashboard__error">{error}</p>;

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <div className="settings-form__section">
        <h2>Identity &amp; branding</h2>
        <div className="settings-form__grid">
          <label className="settings-form__field">
            Widget title
            <input value={form.widget_title} onChange={(e) => update("widget_title", e.target.value)} />
          </label>
          <label className="settings-form__field">
            Tagline
            <input value={form.tagline} onChange={(e) => update("tagline", e.target.value)} />
          </label>
          <label className="settings-form__field">
            Avatar emoji
            <input
              value={form.avatar_emoji}
              maxLength={4}
              onChange={(e) => update("avatar_emoji", e.target.value)}
            />
          </label>
          <label className="settings-form__field">
            Primary color
            <div className="settings-form__color">
              <input type="color" value={form.primary_color} onChange={(e) => update("primary_color", e.target.value)} />
              <input value={form.primary_color} onChange={(e) => update("primary_color", e.target.value)} />
            </div>
          </label>
          <label className="settings-form__field">
            Accent color
            <div className="settings-form__color">
              <input type="color" value={form.accent_color} onChange={(e) => update("accent_color", e.target.value)} />
              <input value={form.accent_color} onChange={(e) => update("accent_color", e.target.value)} />
            </div>
          </label>
        </div>
      </div>

      <div className="settings-form__section">
        <h2>Voice &amp; behaviour</h2>
        <div className="settings-form__grid">
          <label className="settings-form__field">
            Tone
            <select value={form.tone} onChange={(e) => update("tone", e.target.value)}>
              {TONE_OPTIONS.map((tone) => (
                <option key={tone} value={tone}>
                  {tone[0].toUpperCase() + tone.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label className="settings-form__field">
            Max reply length (words)
            <input
              type="number"
              min={20}
              max={300}
              value={form.max_reply_words}
              onChange={(e) => update("max_reply_words", Number(e.target.value))}
            />
          </label>
          <label className="settings-form__field">
            Creativity (temperature)
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={form.temperature}
              onChange={(e) => update("temperature", Number(e.target.value))}
            />
            <span className="settings-form__range-value">{form.temperature.toFixed(2)}</span>
          </label>
          <label className="settings-form__field settings-form__field--wide">
            Persona instructions
            <textarea
              rows={3}
              placeholder="Optional extra guidance, e.g. 'Always mention our loyalty program when relevant.'"
              value={form.persona_instructions || ""}
              onChange={(e) => update("persona_instructions", e.target.value)}
            />
          </label>
          <label className="settings-form__field settings-form__field--wide">
            Greeting message (first thing customers see)
            <textarea
              rows={2}
              value={form.greeting_message}
              onChange={(e) => update("greeting_message", e.target.value)}
            />
          </label>
          <label className="settings-form__field settings-form__field--wide">
            Fallback message (when the bot can't complete a request)
            <textarea
              rows={2}
              value={form.fallback_message}
              onChange={(e) => update("fallback_message", e.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="settings-form__section">
        <h2>Features</h2>
        <div className="settings-toggle-grid">
          {[
            ["enable_appointment_booking", "Appointment booking"],
            ["enable_knowledge_base", "Knowledge base answers (RAG)"],
            ["enable_email_gate", "Require email before chatting"],
            ["show_suggested_questions", "Show suggested questions"],
          ].map(([field, label]) => (
            <label key={field} className="settings-toggle">
              <input
                type="checkbox"
                checked={form[field]}
                onChange={(e) => update(field, e.target.checked)}
              />
              <span className="settings-toggle__track" aria-hidden="true" />
              {label}
            </label>
          ))}
        </div>
      </div>

      <div className="settings-form__section">
        <h2>Voice call</h2>
        <p className="settings-form__hint">
          Lets customers talk to the assistant out loud instead of typing. Voice reuses the
          exact same orchestrator, agents, and knowledge base as chat — this only controls the
          call experience itself.
        </p>
        <div className="settings-toggle-grid">
          <label className="settings-toggle">
            <input
              type="checkbox"
              checked={form.voice_enabled}
              onChange={(e) => update("voice_enabled", e.target.checked)}
            />
            <span className="settings-toggle__track" aria-hidden="true" />
            Enable voice calling
          </label>
        </div>
        <div className="settings-form__grid">
          <label className="settings-form__field">
            Assistant voice
            <select
              value={form.voice_name}
              onChange={(e) => update("voice_name", e.target.value)}
              disabled={!form.voice_enabled}
            >
              {VOICE_NAME_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="settings-form__field settings-form__field--wide">
            Voice call greeting (optional — falls back to the greeting message above)
            <textarea
              rows={2}
              placeholder="e.g. Hi, thanks for calling — how can I help today?"
              value={form.voice_greeting_message || ""}
              onChange={(e) => update("voice_greeting_message", e.target.value)}
              disabled={!form.voice_enabled}
            />
          </label>
        </div>
        {form.voice_enabled && (
          <p className="settings-form__hint">
            Requires <code>DEEPGRAM_API_KEY</code> and <code>DEEPGRAM_PROJECT_ID</code> to be set
            in the backend environment — ask your developer if calls fail to connect.
          </p>
        )}
      </div>

      <div className="settings-form__section">
        <h2>Suggested questions</h2>
        <ul className="suggested-questions-list">
          {form.suggested_questions.map((q, i) => (
            <li key={i}>
              <span>{q}</span>
              <button type="button" className="icon-button icon-button--danger" onClick={() => removeQuestion(i)}>
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
        <div className="suggested-questions-add">
          <input
            placeholder="Add a suggested question…"
            value={newQuestion}
            onChange={(e) => setNewQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addQuestion();
              }
            }}
          />
          <button type="button" onClick={addQuestion}>
            <Plus size={14} />
            Add
          </button>
        </div>
      </div>

      <div className="settings-form__section">
        <h2>Preview compiled prompt</h2>
        <p className="settings-form__hint">
          See exactly what gets sent to the chatbot right now — each section is labeled with
          which admin page controls it, so it's clear where tone, business info, and the
          fallback message actually come from.
        </p>
        <button
          type="button"
          className="settings-form__preview-btn"
          onClick={handlePreview}
          disabled={isPreviewLoading}
        >
          {isPreviewLoading && <Spinner size={14} />}
          {isPreviewLoading ? "Compiling…" : "Preview prompt"}
        </button>
        {previewError && (
          <p className="admin-dashboard__error">
            <AlertCircle size={14} />
            {previewError}
          </p>
        )}
        {promptPreview && <pre className="settings-form__prompt-preview">{promptPreview}</pre>}
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
          Chatbot configuration saved.
        </p>
      )}

      <button type="submit" className="settings-form__submit" disabled={isSaving}>
        {isSaving && <Spinner size={14} className="spinner--on-dark" />}
        {isSaving ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}