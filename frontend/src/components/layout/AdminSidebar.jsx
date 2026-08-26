import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Bot,
  Briefcase,
  Building2,
  Calendar,
  FileText,
  Users,
  X,
} from "../common/Icons.jsx";

const NAV_ITEMS = [
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3, end: true },
  { to: "/admin/staff", label: "Staff", icon: Users },
  { to: "/admin/services", label: "Services", icon: Briefcase },
  { to: "/admin/appointments", label: "Appointments", icon: Calendar },
  { to: "/admin/knowledge-base", label: "Knowledge base", icon: FileText },
  { to: "/admin/business", label: "Business details", icon: Building2 },
  { to: "/admin/chatbot-config", label: "Chatbot configuration", icon: Bot },
];

export default function AdminSidebar({ isOpen, onClose }) {
  return (
    <>
      <aside className={`admin-sidebar ${isOpen ? "admin-sidebar--open" : ""}`}>
        <div className="admin-sidebar__header">
          <span className="admin-sidebar__mark" aria-hidden="true">
            ✦
          </span>
          <span className="admin-sidebar__title">Admin panel</span>
          <button
            type="button"
            className="admin-sidebar__close"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="admin-sidebar__nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                `admin-sidebar__link ${isActive ? "admin-sidebar__link--active" : ""}`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {isOpen && <div className="admin-sidebar__backdrop" onClick={onClose} aria-hidden="true" />}
    </>
  );
}
