import { useState } from "react";
import { updateBusinessDocument } from "../../services/adminApi.js";
import { humanizeFieldName } from "../../utils/businessDocuments.js";
import Modal from "../common/Modal.jsx";
import { AlertCircle, Plus, Save, Trash2 } from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";

function emptyRow(itemFields) {
  const row = {};
  itemFields.forEach((f) => {
    row[f.name] = "";
  });
  return row;
}

export default function FieldListModal({ document, fieldName, fieldLabel, itemFields, onClose, onSaved }) {
  const initialRows = Array.isArray(document.extracted_data?.[fieldName])
    ? document.extracted_data[fieldName]
    : [];
  const [rows, setRows] = useState(
    initialRows.map((r) => {
      const copy = {};
      itemFields.forEach((f) => {
        const v = r[f.name];
        copy[f.name] = v === null || v === undefined ? "" : String(v);
      });
      return copy;
    })
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  function updateCell(rowIdx, fieldKey, value) {
    setRows((prev) => prev.map((r, i) => (i === rowIdx ? { ...r, [fieldKey]: value } : r)));
  }

  function addRow() {
    setRows((prev) => [...prev, emptyRow(itemFields)]);
  }

  function removeRow(rowIdx) {
    setRows((prev) => prev.filter((_, i) => i !== rowIdx));
  }

  async function handleSave() {
    setIsSaving(true);
    setError(null);
    try {
      // Coerce number-typed sub-fields back to numbers where possible; leave
      // everything else as text. Blank cells become null rather than "".
      const payloadRows = rows.map((row) => {
        const out = {};
        itemFields.forEach((f) => {
          const raw = row[f.name];
          if (raw === "" || raw === undefined) {
            out[f.name] = null;
            return;
          }
          if (f.type === "number") {
            const n = Number(raw);
            out[f.name] = Number.isNaN(n) ? raw : n;
          } else {
            out[f.name] = raw;
          }
        });
        return out;
      });

      const updated = await updateBusinessDocument(document.id, { [fieldName]: payloadRows });
      onSaved?.(updated);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't save these changes.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal title={`${fieldLabel} — ${document.original_filename}`} onClose={onClose} width={760}>
      <div className="field-list-modal">
        {error && (
          <p className="document-detail__error">
            <AlertCircle size={14} />
            {error}
          </p>
        )}

        <div className="field-list-modal__table-wrapper">
          <table className="field-list-modal__table">
            <thead>
              <tr>
                {itemFields.map((f) => (
                  <th key={f.name}>{f.label || humanizeFieldName(f.name)}</th>
                ))}
                <th aria-label="Row actions" />
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={itemFields.length + 1} className="field-list-modal__empty">
                    No rows yet — add one below.
                  </td>
                </tr>
              )}
              {rows.map((row, idx) => (
                <tr key={idx}>
                  {itemFields.map((f) => (
                    <td key={f.name}>
                      <input
                        type={f.type === "number" ? "number" : "text"}
                        value={row[f.name]}
                        onChange={(e) => updateCell(idx, f.name, e.target.value)}
                      />
                    </td>
                  ))}
                  <td>
                    <button
                      type="button"
                      className="icon-button icon-button--danger"
                      onClick={() => removeRow(idx)}
                      aria-label="Remove row"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="field-list-modal__actions">
          <button type="button" className="icon-button" onClick={addRow}>
            <Plus size={14} />
            Add row
          </button>
          <button type="button" className="icon-button icon-button--primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Spinner size={14} /> : <Save size={14} />}
            Save changes
          </button>
        </div>
      </div>
    </Modal>
  );
}