/**
 * Formatting helpers for analyst query results.
 *
 * The agent writes its own column aliases, so we can't rely on a fixed schema.
 * Instead we infer how to present each column from its name and its values,
 * which is what makes an arbitrary result set still read well in the table.
 */

const CURRENCY_HINTS = [
  "amount",
  "total",
  "revenue",
  "subtotal",
  "price",
  "value",
  "spend",
  "cost",
  "tax",
  "balance",
];

const COUNT_HINTS = ["count", "number_of", "num_", "_count", "quantity", "qty"];

const PERCENT_HINTS = ["percent", "pct", "rate", "share", "confidence"];

const DATE_HINTS = ["date", "_at", "month", "period", "day", "year"];

/** Turn `total_revenue` into `Total revenue`. */
export function humanizeColumn(name) {
  if (!name) return "";

  return String(name)
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^./, (c) => c.toUpperCase());
}

function nameMatches(column, hints) {
  const lower = String(column || "").toLowerCase();
  return hints.some((hint) => lower.includes(hint));
}

export function isNumeric(value) {
  return typeof value === "number" && Number.isFinite(value);
}

/**
 * Decide how a whole column should be rendered, looking at both its name and
 * a sample of its values. Name alone is ambiguous ("value" could be text), and
 * values alone lose the currency/percent distinction.
 */
export function detectColumnType(column, rows, index) {
  const sample = rows
    .slice(0, 50)
    .map((row) => row[index])
    .filter((v) => v !== null && v !== undefined && v !== "");

  if (sample.length === 0) return "empty";

  const allNumeric = sample.every(isNumeric);

  if (allNumeric) {
    if (nameMatches(column, PERCENT_HINTS)) {
      // Confidence scores are stored 0..1; a "rate"/"percent" column may
      // already be 0..100. Only scale the ones that are clearly fractions.
      const allFractions = sample.every((v) => v >= 0 && v <= 1);
      return allFractions ? "fraction" : "percent";
    }
    if (nameMatches(column, CURRENCY_HINTS)) return "currency";
    if (nameMatches(column, COUNT_HINTS)) return "integer";
    return "number";
  }

  if (sample.every((v) => typeof v === "boolean")) return "boolean";

  if (sample.every((v) => Array.isArray(v) || (typeof v === "object" && v !== null))) {
    return "json";
  }

  if (
    nameMatches(column, DATE_HINTS) &&
    sample.every((v) => typeof v === "string" && /^\d{4}-\d{2}/.test(v))
  ) {
    return "date";
  }

  return "text";
}

const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});

const integerFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 0,
});

const currencyFormatter = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatValue(value, type) {
  if (value === null || value === undefined || value === "") return "—";

  switch (type) {
    case "currency":
      return isNumeric(value) ? currencyFormatter.format(value) : String(value);

    case "integer":
      return isNumeric(value) ? integerFormatter.format(value) : String(value);

    case "number":
      return isNumeric(value) ? numberFormatter.format(value) : String(value);

    case "fraction":
      return isNumeric(value) ? `${(value * 100).toFixed(0)}%` : String(value);

    case "percent":
      return isNumeric(value) ? `${numberFormatter.format(value)}%` : String(value);

    case "boolean":
      return value ? "Yes" : "No";

    case "date":
      return formatDateish(value);

    case "json":
      if (Array.isArray(value)) return value.join(", ");
      return JSON.stringify(value);

    default:
      return String(value);
  }
}

function formatDateish(value) {
  const str = String(value);

  // Month buckets from date_trunc come back as "2026-03-01" or a full
  // timestamp; show them as "Mar 2026" rather than a misleading exact day.
  const monthOnly = /^(\d{4})-(\d{2})-01(?:T00:00:00)?/.exec(str);
  if (monthOnly) {
    const date = new Date(Number(monthOnly[1]), Number(monthOnly[2]) - 1, 1);
    return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
  }

  const full = /^(\d{4})-(\d{2})-(\d{2})/.exec(str);
  if (full) {
    const date = new Date(Number(full[1]), Number(full[2]) - 1, Number(full[3]));
    return date.toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  return str;
}

/** Numeric columns are right-aligned so digits line up for scanning. */
export function alignmentFor(type) {
  return ["currency", "integer", "number", "percent", "fraction"].includes(type)
    ? "right"
    : "left";
}

/** Convert a result set to CSV for the download button. */
export function toCsv(columns, rows) {
  const escape = (value) => {
    if (value === null || value === undefined) return "";

    let str = Array.isArray(value) || typeof value === "object" ? JSON.stringify(value) : String(value);

    if (/[",\n]/.test(str)) {
      str = `"${str.replace(/"/g, '""')}"`;
    }

    return str;
  };

  const header = columns.map(escape).join(",");
  const body = rows.map((row) => row.map(escape).join(",")).join("\n");

  return `${header}\n${body}`;
}
