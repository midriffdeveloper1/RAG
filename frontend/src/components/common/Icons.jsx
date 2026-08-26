/**
 * A small, dependency-free icon set (no external icon library required).
 * Every icon accepts `size` and `className` and forwards any other svg props.
 */
const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function Svg({ size = 16, className = "", children, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={className}
      aria-hidden="true"
      focusable="false"
      {...base}
      {...rest}
    >
      {children}
    </svg>
  );
}

export function Plus(props) {
  return (
    <Svg {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Svg>
  );
}

export function Trash2(props) {
  return (
    <Svg {...props}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </Svg>
  );
}

export function UploadCloud(props) {
  return (
    <Svg {...props}>
      <path d="M7 18a4.6 4.4 0 0 1 0-9 5.5 5.5 0 0 1 10.6-1.7A4.5 4.5 0 0 1 17 18" />
      <polyline points="12 12 12 21" />
      <polyline points="9 15 12 12 15 15" />
    </Svg>
  );
}

export function RefreshCw(props) {
  return (
    <Svg {...props}>
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.5 9a8.5 8.5 0 0 1 14.6-4.4L23 10" />
      <path d="M20.5 15a8.5 8.5 0 0 1-14.6 4.4L1 14" />
    </Svg>
  );
}

export function LogOut(props) {
  return (
    <Svg {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </Svg>
  );
}

export function ChevronLeft(props) {
  return (
    <Svg {...props}>
      <polyline points="15 18 9 12 15 6" />
    </Svg>
  );
}

export function ChevronRight(props) {
  return (
    <Svg {...props}>
      <polyline points="9 18 15 12 9 6" />
    </Svg>
  );
}

export function ChevronsLeft(props) {
  return (
    <Svg {...props}>
      <polyline points="11 17 6 12 11 7" />
      <polyline points="18 17 13 12 18 7" />
    </Svg>
  );
}

export function ChevronsRight(props) {
  return (
    <Svg {...props}>
      <polyline points="13 17 18 12 13 7" />
      <polyline points="6 17 11 12 6 7" />
    </Svg>
  );
}

export function FileText(props) {
  return (
    <Svg {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
    </Svg>
  );
}

export function CheckCircle2(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <polyline points="8.5 12.5 11 15 15.5 9.5" />
    </Svg>
  );
}

export function XCircle(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <line x1="9" y1="9" x2="15" y2="15" />
      <line x1="15" y1="9" x2="9" y2="15" />
    </Svg>
  );
}

export function Clock(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15.5 14" />
    </Svg>
  );
}

export function Loader2(props) {
  return (
    <Svg {...props}>
      <path d="M12 3a9 9 0 1 0 9 9" />
    </Svg>
  );
}

export function Calendar(props) {
  return (
    <Svg {...props}>
      <rect x="3" y="4.5" width="18" height="16.5" rx="2" />
      <line x1="16" y1="2.5" x2="16" y2="6.5" />
      <line x1="8" y1="2.5" x2="8" y2="6.5" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </Svg>
  );
}

export function Users(props) {
  return (
    <Svg {...props}>
      <path d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20" />
      <circle cx="9" cy="8" r="3.2" />
      <path d="M20 20v-1.5a3.3 3.3 0 0 0-2.3-3.1" />
      <path d="M14.3 4.6a3.2 3.2 0 0 1 0 6.1" />
    </Svg>
  );
}

export function Briefcase(props) {
  return (
    <Svg {...props}>
      <rect x="2.5" y="7" width="19" height="13" rx="2" />
      <path d="M8 7V5.5A1.5 1.5 0 0 1 9.5 4h5A1.5 1.5 0 0 1 16 5.5V7" />
      <line x1="2.5" y1="12.5" x2="21.5" y2="12.5" />
    </Svg>
  );
}

export function MessageSquare(props) {
  return (
    <Svg {...props}>
      <path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </Svg>
  );
}

export function Send(props) {
  return (
    <Svg {...props}>
      <line x1="21" y1="3" x2="10.5" y2="13.5" />
      <polygon points="21 3 14.5 21 10.5 13.5 3 9.5 21 3" />
    </Svg>
  );
}

export function Inbox(props) {
  return (
    <Svg {...props}>
      <polyline points="4 12 8.5 12 10.5 15 13.5 15 15.5 12 20 12" />
      <path d="M5.4 5.1 3 12v6a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6l-2.4-6.9A2 2 0 0 0 16.7 3H7.3a2 2 0 0 0-1.9 2.1z" />
    </Svg>
  );
}

export function AlertCircle(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="8" x2="12" y2="13" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </Svg>
  );
}

export function UserCog(props) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="8" r="3.3" />
      <path d="M3.5 20v-1.2A3.8 3.8 0 0 1 7.3 15h1.4a3.8 3.8 0 0 1 3.4 2.1" />
      <circle cx="18" cy="16" r="2.3" />
      <path d="M18 12.7v1M18 18.3v1M15.2 14.4l.9.5M20 17l.9.5M15.2 17.6l.9-.5M20 15l.9-.5" />
    </Svg>
  );
}

export function LayoutDashboard(props) {
  return (
    <Svg {...props}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </Svg>
  );
}

export function Bot(props) {
  return (
    <Svg {...props}>
      <rect x="4" y="8" width="16" height="12" rx="2.5" />
      <path d="M12 8V4" />
      <circle cx="12" cy="3" r="1.2" />
      <circle cx="9" cy="14" r="1.3" />
      <circle cx="15" cy="14" r="1.3" />
      <path d="M9 17.5c1.4.9 4.6.9 6 0" />
    </Svg>
  );
}

export function Building2(props) {
  return (
    <Svg {...props}>
      <rect x="4" y="3" width="10" height="18" rx="1" />
      <rect x="14" y="9" width="6" height="12" rx="1" />
      <line x1="7" y1="7" x2="7" y2="7.01" />
      <line x1="11" y1="7" x2="11" y2="7.01" />
      <line x1="7" y1="11" x2="7" y2="11.01" />
      <line x1="11" y1="11" x2="11" y2="11.01" />
      <line x1="7" y1="15" x2="7" y2="15.01" />
      <line x1="11" y1="15" x2="11" y2="15.01" />
    </Svg>
  );
}

export function Settings(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </Svg>
  );
}

export function BarChart3(props) {
  return (
    <Svg {...props}>
      <line x1="4" y1="20" x2="4" y2="10" />
      <line x1="11" y1="20" x2="11" y2="4" />
      <line x1="18" y1="20" x2="18" y2="14" />
      <line x1="3" y1="21" x2="21" y2="21" />
    </Svg>
  );
}

export function Menu(props) {
  return (
    <Svg {...props}>
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </Svg>
  );
}

export function X(props) {
  return (
    <Svg {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </Svg>
  );
}

export function MessageCircle(props) {
  return (
    <Svg {...props}>
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </Svg>
  );
}

export function Palette(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="8.5" cy="10.5" r="1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="8" r="1" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="10.5" r="1" fill="currentColor" stroke="none" />
      <circle cx="9.5" cy="14.5" r="1" fill="currentColor" stroke="none" />
      <path d="M12 21a1.5 1.5 0 0 1 0-3h1a2.5 2.5 0 0 0 0-5h-.5A6.5 6.5 0 1 1 19 8" />
    </Svg>
  );
}

export function ToggleLeft(props) {
  return (
    <Svg {...props}>
      <rect x="1" y="6" width="22" height="12" rx="6" />
      <circle cx="8" cy="12" r="3.2" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function ToggleRight(props) {
  return (
    <Svg {...props}>
      <rect x="1" y="6" width="22" height="12" rx="6" />
      <circle cx="16" cy="12" r="3.2" fill="currentColor" stroke="none" />
    </Svg>
  );
}