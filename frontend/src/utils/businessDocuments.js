import { parseApiTimestamp } from "./time.js";

export function humanizeFieldName(name) {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatFileSize(bytes) {
  if (bytes === undefined || bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDateTime(isoString) {
  const date = parseApiTimestamp(isoString);
  return date ? date.toLocaleString() : "—";
}

export function formatConfidencePct(value) {
  if (value === undefined || value === null) return null;
  return Math.round(value * 100);
}

export function confidenceTier(value) {
  if (value === undefined || value === null) return "unknown";
  if (value >= 0.8) return "high";
  if (value >= 0.5) return "medium";
  return "low";
}

const HEADLINE_FIELDS_BY_TYPE = {
  invoice: ["invoice_number", "vendor_name", "total_amount"],
  receipt: ["merchant_name", "total_amount"],
  purchase_order: ["po_number", "vendor_name", "total_amount"],
  resume: ["candidate_name", "email"],
  expense_report: ["employee_name", "total_amount"],
  application_form: ["applicant_name", "position_applied_for"],
  contract: ["contract_title", "party_a", "party_b"],
};

export function getHeadline(documentType, extractedData) {
  if (!extractedData) return null;
  const fields = HEADLINE_FIELDS_BY_TYPE[documentType] || [];
  const parts = fields
    .map((f) => extractedData[f])
    .filter((v) => v !== undefined && v !== null && v !== "");
  return parts.length ? parts.join(" · ") : null;
}

export function isPrimitive(value) {
  return value === null || typeof value !== "object";
}