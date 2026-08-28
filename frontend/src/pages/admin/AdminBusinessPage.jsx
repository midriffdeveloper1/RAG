import BusinessForm from "../../components/Admin/BusinessForm.jsx";
import FaqPolicyManager from "../../components/Admin/FaqPolicyManager.jsx";
import HolidayManager from "../../components/Admin/HolidayManager.jsx";

export default function AdminBusinessPage() {
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Business details</h1>
          <p>The facts your chatbot uses to describe your business and its hours.</p>
        </div>
      </div>
      <BusinessForm />
      <HolidayManager />
      <FaqPolicyManager />
    </div>
  );
}