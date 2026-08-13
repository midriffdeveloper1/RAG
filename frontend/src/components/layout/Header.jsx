import { BUSINESS_NAME } from "../../utils/constants.js";

export default function Header() {
  return (
    <header className="site-header">
      <div className="site-header__brand">
        <span className="site-header__mark" aria-hidden="true">
          ✦
        </span>
        <div>
          <p className="site-header__name">{BUSINESS_NAME}</p>
          <p className="site-header__tagline"></p>
        </div>
      </div>
    </header>
  );
}
