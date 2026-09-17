import { AlertCircle, ShieldAlert, Sparkles } from "../common/Icons.jsx";
import AnalystChart from "./AnalystChart.jsx";
import AnalystResultTable from "./AnalystResultTable.jsx";


const STATUS_STYLES = {
  blocked: { icon: ShieldAlert, className: "analyst-msg--boundary" },
  error: { icon: AlertCircle, className: "analyst-msg--hiccup" },
};

export default function AnalystMessage({ message }) {
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

  return (
    <div className={`analyst-msg analyst-msg--assistant ${statusStyle?.className ?? ""}`}>
      <div className="analyst-msg__avatar" aria-hidden="true">
        {StatusIcon ? <StatusIcon size={15} /> : <Sparkles size={15} />}
      </div>

      <div className="analyst-msg__body">
        <p className="analyst-msg__answer">{message.content}</p>

        {isEmptyResult && (
          <p className="analyst-msg__empty">Nothing to show here — the table would&rsquo;ve been empty.</p>
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
      </div>
    </div>
  );
}