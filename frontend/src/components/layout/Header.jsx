import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { BUSINESS_NAME } from "../../utils/constants.js";

export default function Header() {
  const { isAuthenticated } = useAuth();

  return (
    <header className="site-header">
      <div className="site-header__brand">
        <span className="site-header__mark" aria-hidden="true">
          ✦
        </span>
        <div>
          <p className="site-header__name">{BUSINESS_NAME}</p>
          <p className="site-header__tagline">Support Assistant</p>
        </div>
      </div>

      <Link className="site-header__admin-link" to={isAuthenticated ? "/admin" : "/admin/login"}>
        {isAuthenticated ? "Admin dashboard" : "Admin login"}
      </Link>
    </header>
  );
}