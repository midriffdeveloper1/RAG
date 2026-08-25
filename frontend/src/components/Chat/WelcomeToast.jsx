import { useEffect } from "react";
import { CheckCircle2 } from "../common/Icons.jsx";

const AUTO_DISMISS_MS = 4000;

export default function WelcomeToast({ isReturning, name, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const message = isReturning
    ? `Welcome back${name ? `, ${name}` : ""}!`
    : "Welcome! Great to have you here.";

  return (
    <div className="welcome-toast" role="status">
      <CheckCircle2 size={16} className="welcome-toast__icon" />
      <span>{message}</span>
    </div>
  );
}