import { useState } from "react";
import { AlertCircle, Check, ChevronDown, Code2, ShieldAlert, Sparkles } from "../common/Icons.jsx";
import AnalystChart from "./AnalystChart.jsx";
import AnalystResultTable from "./AnalystResultTable.jsx";

const STATUS_STYLES = {
  out_of_scope: { icon: AlertCircle, className: "analyst-msg--notice" },
  needs_clarification: { icon: AlertCircle, className: "analyst-msg--notice" },
  blocked: { icon: ShieldAlert, className: "analyst-msg--blocked" },
  error: { icon: AlertCircle, className: "analyst-msg--error" },
};

export default function AnalystMessage({ message }) {
  const [showSql, setShowSql] = useState(false);
  const [copied, setCopied] = useState(false);

  if (message.role === "user") {
    return (
      <div className="analyst-msg analyst-msg--user">
        <div className="analyst-msg__bubble">{message.content}</div>
      </div>
    );
  }

  const statusStyle = STATUS_STYLES[message.status];
  const StatusIcon = statusStyle?.icon;

  const hasResult = Boolean(message.result_columns?.length && message.result_rows?.length);
  const isEmptyResult = message.status === "ok" && !hasResult;

  async function copySql() {
    try {
      await navigator.clipboard.writeText(message.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard can be blocked by permissions; the SQL is still visible
      // on screen to select manually, so failing quietly is fine here.
    }
  }

  return (
    <div className={`analyst-msg analyst-msg--assistant ${statusStyle?.className ?? ""}`}>
      <div className="analyst-msg__avatar" aria-hidden="true">
        {StatusIcon ? <StatusIcon size={15} /> : <Sparkles size={15} />}
      </div>

      <div className="analyst-msg__body">
        <p className="analyst-msg__answer">{message.content}</p>

        {isEmptyResult && (
          <p className="analyst-msg__empty">No rows matched this query.</p>
        )}

        {message.chart && hasResult && (
          <AnalystChart
            chart={message.chart}
            columns={message.result_columns}
            rows={message.result_rows}
          />
        )}

        {hasResult && (
          <AnalystResultTable
            columns={message.result_columns}
            rows={message.result_rows}
            truncated={message.truncated}
            rowCount={message.row_count}
          />
        )}

        {message.sql && (
          <div className="analyst-sql">
            <button
              type="button"
              className="analyst-sql__toggle"
              onClick={() => setShowSql((v) => !v)}
              aria-expanded={showSql}
            >
              <Code2 size={13} />
              <span>{showSql ? "Hide" : "View"} SQL</span>
              <ChevronDown
                size={13}
                className={`analyst-sql__chevron ${
                  showSql ? "analyst-sql__chevron--open" : ""
                }`}
              />
              {message.duration_ms != null && (
                <span className="analyst-sql__timing">{message.duration_ms} ms</span>
              )}
            </button>

            {showSql && (
              <div className="analyst-sql__panel">
                <pre className="analyst-sql__code">{message.sql}</pre>
                <button type="button" className="analyst-sql__copy" onClick={copySql}>
                  {copied ? <Check size={13} /> : <Code2 size={13} />}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
