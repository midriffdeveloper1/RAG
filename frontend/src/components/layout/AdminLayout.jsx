import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { LogOut, Menu } from "../common/Icons.jsx";
import AdminSidebar from "./AdminSidebar.jsx";

export default function AdminLayout() {
  const { admin, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/admin/login", { replace: true });
  }

  return (
    <div className="admin-shell">
      <AdminSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div className="admin-shell__main">
        <div className="admin-topbar">
          <button
            type="button"
            className="admin-topbar__menu-btn"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>

          <div className="admin-topbar__spacer" />

          <div className="admin-topbar__account">
            <span className="admin-topbar__email">{admin?.email}</span>
            <button type="button" className="admin-topbar__logout" onClick={handleLogout}>
              <LogOut size={15} />
              Log out
            </button>
          </div>
        </div>

        <div className="admin-shell__content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
