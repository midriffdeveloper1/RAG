import { humanizeFieldName } from "../../utils/businessDocuments.js";

function ObjectListTable({ items }) {
  if (!items.length) return <span className="field-value__empty">None extracted</span>;

  const columns = Array.from(
    items.reduce((set, item) => {
      Object.keys(item || {}).forEach((k) => set.add(k));
      return set;
    }, new Set())
  );

  return (
    <div className="field-value__table-wrapper">
      <table className="field-value__table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{humanizeFieldName(col)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={idx}>
              {columns.map((col) => (
                <td key={col}>{formatPrimitive(item?.[col])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatPrimitive(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString();
  return String(value);
}

export default function FieldValue({ value }) {
  if (value === null || value === undefined || value === "") {
    return <span className="field-value__empty">Not found</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="field-value__empty">None extracted</span>;
    if (typeof value[0] === "object" && value[0] !== null) {
      return <ObjectListTable items={value} />;
    }
    return (
      <div className="field-value__chips">
        {value.map((item, idx) => (
          <span key={idx} className="field-value__chip">
            {formatPrimitive(item)}
          </span>
        ))}
      </div>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value);
    if (!entries.length) return <span className="field-value__empty">None extracted</span>;
    return (
      <dl className="field-value__object">
        {entries.map(([k, v]) => (
          <div key={k} className="field-value__object-row">
            <dt>{humanizeFieldName(k)}</dt>
            <dd>{formatPrimitive(v)}</dd>
          </div>
        ))}
      </dl>
    );
  } 

  return <span>{formatPrimitive(value)}</span>;
}

export function isEditablePrimitive(value) {
  return value === null || value === undefined || typeof value !== "object";
}