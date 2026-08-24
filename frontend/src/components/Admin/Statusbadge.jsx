// const STATUS_LABELS = {
//   pending: "Pending",
//   processing: "Processing",
//   completed: "Completed",
//   failed: "Failed",
//   booked: "Booked",
//   cancelled: "Cancelled",
// };

// export default function StatusBadge({ status }) {
//   return (
//     <span className={`status-badge status-badge--${status}`}>
//       {STATUS_LABELS[status] || status}
//     </span>
//   );
// }

import { CheckCircle2, Clock, RefreshCw, XCircle } from "../common/Icons.jsx";

const STATUS_CONFIG = {
  pending: { label: "Pending", icon: Clock },
  processing: { label: "Processing", icon: RefreshCw },
  completed: { label: "Completed", icon: CheckCircle2 },
  failed: { label: "Failed", icon: XCircle },
  booked: { label: "Booked", icon: Clock },
  cancelled: { label: "Cancelled", icon: XCircle },
};

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || { label: status, icon: null };
  const Icon = config.icon;

  return (
    <span className={`status-badge status-badge--${status}`}>
      {Icon && <Icon size={12} className="status-badge__icon" />}
      {config.label}
    </span>
  );
}