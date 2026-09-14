import { AlertCircle, CheckCircle2, Clock, RefreshCw, XCircle } from "../common/Icons.jsx";

const STATUS_CONFIG = {
  pending: { label: "Pending", icon: Clock },
  processing: { label: "Processing", icon: RefreshCw },
  completed: { label: "Completed", icon: CheckCircle2 },
  needs_review: { label: "Needs review", icon: AlertCircle },
  failed: { label: "Failed", icon: XCircle },
};

export default function BusinessDocumentStatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || { label: status, icon: null };
  const Icon = config.icon;

  return (
    <span className={`status-badge status-badge--${status}`}>
      {Icon && <Icon size={12} className="status-badge__icon" />}
      {config.label}
    </span>
  );
}