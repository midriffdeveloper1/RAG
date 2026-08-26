import ServiceList from "../../components/Admin/ServiceList.jsx";

export default function AdminServicesPage() {
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Services</h1>
          <p>The bookable catalog your chatbot quotes prices and durations from.</p>
        </div>
      </div>
      <ServiceList />
    </div>
  );
}
