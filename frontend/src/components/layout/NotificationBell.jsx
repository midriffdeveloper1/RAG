import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getUnreadNotificationCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../services/adminApi.js";
import { formatRelativeTime } from "../../utils/time.js";
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  Info,
  XCircle,
} from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";

const POLL_INTERVAL_MS = 20000;

const SEVERITY_ICON = {
  info: Info,
  success: CheckCircle2,
  warning: AlertCircle,
  error: XCircle,
};

export default function NotificationBell() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef(null);

  const refreshUnreadCount = useCallback(async () => {
    try {
      setUnreadCount(await getUnreadNotificationCount());
    } catch {
      // silent — the bell just won't update this cycle
    }
  }, []);

  useEffect(() => {
    refreshUnreadCount();
    const interval = setInterval(refreshUnreadCount, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refreshUnreadCount]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleToggleOpen() {
    const next = !isOpen;
    setIsOpen(next);
    if (next) {
      setIsLoading(true);
      try {
        const data = await listNotifications({ pageSize: 15 });
        setNotifications(data.notifications);
        setUnreadCount(data.unread_count);
      } finally {
        setIsLoading(false);
      }
    }
  }

  async function handleItemClick(notification) {
    setIsOpen(false);
    if (!notification.is_read) {
      try {
        await markNotificationRead(notification.id);
        setUnreadCount((n) => Math.max(0, n - 1));
      } catch {
        // navigate anyway — read-state is a nice-to-have, not blocking
      }
    }
    if (notification.link) {
      navigate(notification.link);
    }
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore — next poll will reconcile
    }
  }

  return (
    <div className="notification-bell" ref={containerRef}>
      <button
        type="button"
        className="notification-bell__trigger"
        onClick={handleToggleOpen}
        aria-label={`Notifications${unreadCount ? ` (${unreadCount} unread)` : ""}`}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="notification-bell__badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div className="notification-bell__panel">
          <div className="notification-bell__header">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button type="button" className="notification-bell__mark-all" onClick={handleMarkAllRead}>
                Mark all read
              </button>
            )}
          </div>

          {isLoading ? (
            <div className="notification-bell__loading">
              <Spinner size={16} />
            </div>
          ) : notifications.length === 0 ? (
            <p className="notification-bell__empty">You&apos;re all caught up.</p>
          ) : (
            <ul className="notification-bell__list">
              {notifications.map((n) => {
                const Icon = SEVERITY_ICON[n.severity] || Info;
                return (
                  <li key={n.id}>
                    <button
                      type="button"
                      className={`notification-bell__item notification-bell__item--${n.severity} ${
                        n.is_read ? "" : "notification-bell__item--unread"
                      }`}
                      onClick={() => handleItemClick(n)}
                    >
                      <Icon size={15} className="notification-bell__item-icon" />
                      <span className="notification-bell__item-body">
                        <span className="notification-bell__item-title">{n.title}</span>
                        <span className="notification-bell__item-message">{n.message}</span>
                        <span className="notification-bell__item-time">
                          {formatRelativeTime(n.created_at)}
                        </span>
                      </span>
                      {!n.is_read && <span className="notification-bell__dot" aria-hidden="true" />}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}