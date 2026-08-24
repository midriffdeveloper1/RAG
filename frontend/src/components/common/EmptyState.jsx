import { Inbox } from "./Icons.jsx";

export default function EmptyState({ icon: IconComponent = Inbox, title, description }) {
  return (
    <div className="empty-state">
      <IconComponent size={26} className="empty-state__icon" />
      <p className="empty-state__title">{title}</p>
      {description && <p className="empty-state__description">{description}</p>}
    </div>
  );
}