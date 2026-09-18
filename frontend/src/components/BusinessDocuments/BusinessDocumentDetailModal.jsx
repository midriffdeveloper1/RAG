import { useState } from "react";
import {
  deleteBusinessDocument,
  reprocessBusinessDocument,
  setBusinessDocumentStatus,
  updateBusinessDocument,
} from "../../services/adminApi.js";
import { getDocumentTypeConfig } from "../../config/businessDocumentTypes.js";
import { formatDateTime, formatFileSize, humanizeFieldName } from "../../utils/businessDocuments.js";
import Modal from "../common/Modal.jsx";
import { AlertCircle, CheckCircle2, Pencil, RefreshCw, RotateCcw, Save, Trash2 } from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";
import BusinessDocumentStatusBadge from "./BusinessDocumentStatusBadge.jsx";
import ConfidenceMeter from "./ConfidenceMeter.jsx";
import FieldValue, { isEditablePrimitive } from "./FieldValue.jsx";

export default function BusinessDocumentDetailModal({ document, onClose, onChanged, onDeleted }) {
  const [doc, setDoc] = useState(document);
  const [editingField, setEditingField] = useState(null);
  const [draftValue, setDraftValue] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  const typeConfig = getDocumentTypeConfig(doc.document_type);
  const errorsByField = new Map((doc.validation_errors || []).map((e) => [e.field, e.message]));
  const missingSet = new Set(doc.missing_fields || []);
  const fields = doc.extracted_data || {};
  const fieldNames = Object.keys(fields).length
    ? Object.keys(fields)
    : Array.from(missingSet);

  function startEdit(name, currentValue) {
    setEditingField(name);
    setDraftValue(currentValue === null || currentValue === undefined ? "" : String(currentValue));
  }

  async function saveEdit(name) {
    setIsSaving(true);
    setActionError(null);
    try {
      const updated = await updateBusinessDocument(doc.id, { [name]: draftValue });
      setDoc(updated);
      onChanged?.(updated);
      setEditingField(null);
    } catch (err) {
      setActionError(err.response?.data?.detail || "Couldn't save that change.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleReprocess() {
    setIsBusy(true);
    setActionError(null);
    try {
      const updated = await reprocessBusinessDocument(doc.id);
      setDoc(updated);
      onChanged?.(updated);
    } catch (err) {
      setActionError(err.response?.data?.detail || "Re-processing failed.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleStatusChange(nextStatus) {
    setIsBusy(true);
    setActionError(null);
    try {
      const updated = await setBusinessDocumentStatus(doc.id, nextStatus);
      setDoc(updated);
      onChanged?.(updated);
    } catch (err) {
      setActionError(err.response?.data?.detail || "Couldn't update the status.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this document and its extracted data?")) return;
    setIsBusy(true);
    try {
      await deleteBusinessDocument(doc.id);
      onDeleted?.(doc.id);
      onClose();
    } catch (err) {
      setActionError(err.response?.data?.detail || "Couldn't delete this document.");
      setIsBusy(false);
    }
  }

  return (
    <Modal title={doc.original_filename} onClose={onClose} width={720}>
      <div className="document-detail">
        <div className="document-detail__meta">
          <BusinessDocumentStatusBadge status={doc.status} />
          <span className="document-detail__type">{typeConfig ? typeConfig.label : "Unrecognized"}</span>
          {doc.confidence_score !== null && doc.confidence_score !== undefined && (
            <span className="document-detail__confidence">
              Overall confidence <ConfidenceMeter value={doc.confidence_score} />
            </span>
          )}
        </div>

        <div className="document-detail__submeta">
          <span>{formatFileSize(doc.file_size_bytes)}</span>
          <span>·</span>
          <span>Uploaded {formatDateTime(doc.uploaded_at)}</span>
          {doc.processed_at && (
            <>
              <span>·</span>
              <span>Processed {formatDateTime(doc.processed_at)}</span>
            </>
          )}
          {doc.reviewed && (
            <>
              <span>·</span>
              <span className="document-detail__reviewed">Manually reviewed</span>
            </>
          )}
        </div>

        {doc.error_message && (
          <p className="document-detail__error">
            <AlertCircle size={14} />
            {doc.error_message}
          </p>
        )}

        {actionError && (
          <p className="document-detail__error">
            <AlertCircle size={14} />
            {actionError}
          </p>
        )}

        {doc.document_type !== "unknown" && (
          <div className="document-detail__fields">
            {fieldNames.map((name) => {
              const value = fields[name];
              const confidence = doc.field_confidence?.[name];
              const errorMsg = errorsByField.get(name);
              const isMissing = missingSet.has(name);
              const editable = isEditablePrimitive(value) || isMissing;

              return (
                <div
                  key={name}
                  className={`document-detail__field ${isMissing ? "document-detail__field--missing" : ""} ${
                    errorMsg ? "document-detail__field--invalid" : ""
                  }`}
                >
                  <div className="document-detail__field-header">
                    <span className="document-detail__field-label">{humanizeFieldName(name)}</span>
                    {confidence !== undefined && confidence !== null && (
                      <ConfidenceMeter value={confidence} size="sm" />
                    )}
                  </div>

                  {editingField === name ? (
                    <div className="document-detail__edit-row">
                      <input
                        type="text"
                        value={draftValue}
                        onChange={(e) => setDraftValue(e.target.value)}
                        autoFocus
                      />
                      <button
                        type="button"
                        className="icon-button"
                        onClick={() => saveEdit(name)}
                        disabled={isSaving}
                        aria-label="Save field"
                      >
                        {isSaving ? <Spinner size={14} /> : <Save size={14} />}
                      </button>
                    </div>
                  ) : (
                    <div className="document-detail__field-value-row">
                      <FieldValue value={value} />
                      {editable && (
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => startEdit(name, value)}
                          aria-label={`Edit ${humanizeFieldName(name)}`}
                          title="Edit"
                        >
                          <Pencil size={13} />
                        </button>
                      )}
                    </div>
                  )}

                  {isMissing && <p className="document-detail__field-note">Required — not found</p>}
                  {errorMsg && <p className="document-detail__field-note document-detail__field-note--error">{errorMsg}</p>}
                </div>
              );
            })}
          </div>
        )}

        {doc.status === "needs_review" && (
          <p className="document-detail__hint">
            Automatic checks flagged this as incomplete — usually because a field is empty. If
            you&rsquo;ve looked it over and it&rsquo;s as complete as the source document allows (a
            field that&rsquo;s simply blank on the original isn&rsquo;t an extraction error), you can
            mark it complete yourself below.
          </p>
        )}

        <div className="document-detail__actions">
          <button type="button" className="icon-button" onClick={handleReprocess} disabled={isBusy}>
            {isBusy ? <Spinner size={14} /> : <RefreshCw size={14} />}
            Re-run extraction
          </button>

          {doc.status === "needs_review" && (
            <button
              type="button"
              className="icon-button icon-button--primary"
              onClick={() => handleStatusChange("completed")}
              disabled={isBusy}
              title="Mark this record as reviewed and complete"
            >
              <CheckCircle2 size={14} />
              Mark as complete
            </button>
          )}

          {doc.status === "completed" && (
            <button
              type="button"
              className="icon-button"
              onClick={() => handleStatusChange("needs_review")}
              disabled={isBusy}
              title="Reopen this record for another look"
            >
              <RotateCcw size={14} />
              Reopen for review
            </button>
          )}

          <button
            type="button"
            className="icon-button icon-button--danger"
            onClick={handleDelete}
            disabled={isBusy}
          >
            <Trash2 size={14} />
            Delete
          </button>
        </div>
      </div>
    </Modal>
  );
}