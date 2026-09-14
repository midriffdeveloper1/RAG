import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { BUSINESS_DOCUMENT_TYPES } from "../../config/businessDocumentTypes.js";
import {
  BarChart3,
  Bot,
  Briefcase,
  Building2,
  Calendar,
  ChevronDown,
  FileText,
  FolderKanban,
  MessageCircle,
  UploadCloud,
  UserCog,
  Users,
  X,
} from "../common/Icons.jsx";

const NAV_ITEMS = [
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3, end: true },
  { to: "/admin/staff", label: "Staff", icon: Users },
  { to: "/admin/services", label: "Services", icon: Briefcase },
  { to: "/admin/appointments", label: "Appointments", icon: Calendar },
  { to: "/admin/conversations", label: "Conversations", icon: MessageCircle },
  { to: "/admin/customers", label: "Customers", icon: UserCog },
  { to: "/admin/knowledge-base", label: "Knowledge base", icon: FileText },
  { to: "/admin/business", label: "Business details", icon: Building2 },
  { to: "/admin/chatbot-config", label: "Chatbot configuration", icon: Bot },
];

const BUSINESS_MANAGEMENT_BASE = "/admin/business-management";

export default function AdminSidebar({ isOpen, onClose }) {
  const location = useLocation();
  const isOnBusinessManagement = location.pathname.startsWith(BUSINESS_MANAGEMENT_BASE);
  const [isDocsGroupOpen, setIsDocsGroupOpen] = useState(isOnBusinessManagement);

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

          <div className="admin-sidebar__group">
            <button
              type="button"
              className={`admin-sidebar__link admin-sidebar__group-toggle ${
                isOnBusinessManagement ? "admin-sidebar__link--active-group" : ""
              }`}
              onClick={() => setIsDocsGroupOpen((v) => !v)}
              aria-expanded={isDocsGroupOpen}
            >
              <FolderKanban size={18} />
              <span>Business management</span>
              <ChevronDown
                size={15}
                className={`admin-sidebar__group-chevron ${
                  isDocsGroupOpen ? "admin-sidebar__group-chevron--open" : ""
                }`}
              />
            </button>

            {isDocsGroupOpen && (
              <div className="admin-sidebar__submenu">
                <NavLink
                  to={`${BUSINESS_MANAGEMENT_BASE}/upload`}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `admin-sidebar__sublink ${isActive ? "admin-sidebar__sublink--active" : ""}`
                  }
                >
                  <UploadCloud size={15} />
                  <span>Upload documents</span>
                </NavLink>

                <p className="admin-sidebar__subheading">Document records</p>

                {BUSINESS_DOCUMENT_TYPES.map((docType) => (
                  <NavLink
                    key={docType.key}
                    to={`${BUSINESS_MANAGEMENT_BASE}/${docType.path}`}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `admin-sidebar__sublink ${isActive ? "admin-sidebar__sublink--active" : ""}`
                    }
                  >
                    <docType.icon size={15} />
                    <span>{docType.label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        </nav>
      </aside>

      {isOpen && <div className="admin-sidebar__backdrop" onClick={onClose} aria-hidden="true" />}
    </>
  );
}