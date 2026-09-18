const HAS_TIMEZONE = /(?:[zZ]|[+-]\d{2}:?\d{2})$/;

export function parseApiTimestamp(value) {
  if (!value) return null;
  if (value instanceof Date) return value;

  const normalized = HAS_TIMEZONE.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);

  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatRelativeTime(isoString) {
  const then = parseApiTimestamp(isoString);
  if (!then) return "";

  const diffSec = Math.round((Date.now() - then.getTime()) / 1000);

  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return then.toLocaleDateString();
}

export function formatDateTime(isoString) {
  const date = parseApiTimestamp(isoString);
  return date ? date.toLocaleString() : "";
}

export function formatDate(isoString) {
  const date = parseApiTimestamp(isoString);
  return date ? date.toLocaleDateString() : "";
}