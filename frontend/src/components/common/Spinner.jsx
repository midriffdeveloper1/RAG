import { Loader2 } from "./Icons.jsx";

export function Spinner({ size = 16, className = "" }) {
  return <Loader2 size={size} className={`spinner ${className}`} />;
}

export function LoadingState({ label = "Loading…", compact = false }) {
  return (
    <div className={`loading-state ${compact ? "loading-state--compact" : ""}`}>
      <Spinner size={compact ? 16 : 22} />
      <span>{label}</span>
    </div>
  );
}