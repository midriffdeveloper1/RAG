import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { BUSINESS_NAME } from "../../utils/constants.js";
import { LogOut } from "../common/Icons.jsx";

export default function Header() {
  const { isAuthenticated, admin, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/admin/login", { replace: true });
  }

  return (
    <header className="site-header">
      <Link to="/" className="site-header__brand">
        <span className="site-header__mark" aria-hidden="true">
          ✦
        </span>
        <div>
          <p className="site-header__name">{BUSINESS_NAME}</p>
          <p className="site-header__tagline">Support Assistant</p>
        </div>
      </Link>

      {isAuthenticated ? (
        <div className="site-header__account">
          <Link className="site-header__admin-link" to="/admin">
            Admin dashboard
          </Link>
          <span className="site-header__email">{admin?.email}</span>
          <button type="button" className="site-header__logout" onClick={handleLogout}>
            <LogOut size={15} />
            Log out
          </button>
        </div>
      ) : (
        <Link className="site-header__admin-link" to="/admin/login">
          Admin login
        </Link>
      )}
    </header>
  );
}
