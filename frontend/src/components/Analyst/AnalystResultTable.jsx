import { useMemo, useState } from "react";
import { ChevronDown, Download, FileSpreadsheet } from "../common/Icons.jsx";
import {
  alignmentFor,
  detectColumnType,
  formatValue,
  humanizeColumn,
  toCsv,
} from "../../utils/analystFormat.js";

const INITIAL_VISIBLE_ROWS = 8;

export default function AnalystResultTable({ columns, rows, truncated, rowCount }) {
  const [expanded, setExpanded] = useState(false);
  const [sort, setSort] = useState({ index: null, direction: "desc" });
  const [revealed, setRevealed] = useState(false);

  const columnTypes = useMemo(
    () => columns.map((column, index) => detectColumnType(column, rows, index)),
    [columns, rows],
  );

  const sortedRows = useMemo(() => {
    if (sort.index === null) return rows;

    const copy = [...rows];
    const factor = sort.direction === "asc" ? 1 : -1;

    copy.sort((a, b) => {
      const left = a[sort.index];
      const right = b[sort.index];

      if (left === null || left === undefined) return 1;
      if (right === null || right === undefined) return -1;

      if (typeof left === "number" && typeof right === "number") {
        return (left - right) * factor;
      }

      return String(left).localeCompare(String(right), undefined, { numeric: true }) * factor;
    });

    return copy;
  }, [rows, sort]);

  const visibleRows = expanded ? sortedRows : sortedRows.slice(0, INITIAL_VISIBLE_ROWS);
  const hiddenCount = sortedRows.length - visibleRows.length;

  function toggleSort(index) {
    setSort((current) =>
      current.index === index
        ? { index, direction: current.direction === "asc" ? "desc" : "asc" }
        : { index, direction: "desc" },
    );
  }

  function downloadCsv() {
    const csv = toCsv(columns, sortedRows);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `analyst-result-${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  if (!columns?.length || !rows?.length) return null;

  if (rows.length === 1 && columns.length === 1) {
    const type = columnTypes[0];

    return (
      <div className="analyst-result">
        <div className="analyst-metric">
          <span className="analyst-metric__label">{humanizeColumn(columns[0])}</span>
          <span className="analyst-metric__value">{formatValue(rows[0][0], type)}</span>
        </div>
      </div>
    );
  }

  if (rows.length === 1 && columns.length > 1) {
    return (
      <div className="analyst-result">
        <dl className="analyst-record">
          {columns.map((column, index) => (
            <div className="analyst-record__row" key={column}>
              <dt>{humanizeColumn(column)}</dt>
              <dd className={`analyst-record__value--${alignmentFor(columnTypes[index])}`}>
                {formatValue(rows[0][index], columnTypes[index])}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    );
  }

  if (!revealed) {
    return (
      <div className="analyst-result">
        <button type="button" className="analyst-reveal" onClick={() => setRevealed(true)}>
          <FileSpreadsheet size={14} />
          <span>
            Show as table · {rowCount ?? rows.length} row{(rowCount ?? rows.length) === 1 ? "" : "s"}
          </span>
        </button>
      </div>
    );
  }

  return (
    <div className="analyst-result">
      <div className="analyst-result__toolbar">
        <span className="analyst-result__count">
          {rowCount ?? rows.length} row{(rowCount ?? rows.length) === 1 ? "" : "s"}
          {truncated ? " (showing the first page of a larger result)" : ""}
        </span>

        <div className="analyst-result__actions">
          <button type="button" className="analyst-result__csv" onClick={downloadCsv}>
            <Download size={14} />
            <span>CSV</span>
          </button>
          <button type="button" className="analyst-result__csv" onClick={() => setRevealed(false)}>
            <span>Hide</span>
          </button>
        </div>
      </div>

      <div className="analyst-table__scroll">
        <table className="analyst-table">
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th
                  key={column}
                  className={`analyst-table__th--${alignmentFor(columnTypes[index])} ${
                    sort.index === index ? "analyst-table__th--sorted" : ""
                  }`}
                  onClick={() => toggleSort(index)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      toggleSort(index);
                    }
                  }}
                  title="Sort by this column"
                >
                  <span>{humanizeColumn(column)}</span>
                  {sort.index === index && (
                    <ChevronDown
                      size={13}
                      className={`analyst-table__sort ${
                        sort.direction === "asc" ? "analyst-table__sort--asc" : ""
                      }`}
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((value, cellIndex) => {
                  const type = columnTypes[cellIndex];
                  const isEmpty = value === null || value === undefined || value === "";

                  return (
                    <td
                      key={cellIndex}
                      className={`analyst-table__td--${alignmentFor(type)} ${
                        isEmpty ? "analyst-table__td--empty" : ""
                      }`}
                    >
                      {formatValue(value, type)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hiddenCount > 0 && (
        <button
          type="button"
          className="analyst-result__more"
          onClick={() => setExpanded(true)}
        >
          Show {hiddenCount} more row{hiddenCount === 1 ? "" : "s"}
        </button>
      )}

      {expanded && sortedRows.length > INITIAL_VISIBLE_ROWS && (
        <button
          type="button"
          className="analyst-result__more"
          onClick={() => setExpanded(false)}
        >
          Show less
        </button>
      )}
    </div>
  );
}