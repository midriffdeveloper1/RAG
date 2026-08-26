import BusinessForm from "../../components/Admin/BusinessForm.jsx";

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
    </div>
  );
}
