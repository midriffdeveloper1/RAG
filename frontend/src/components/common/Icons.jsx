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