import AppointmentList from "../../components/Admin/AppointmentList.jsx";

export default function AdminAppointmentsPage() {
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Appointments</h1>
          <p>Every booking made through the chat assistant.</p>
        </div>
      </div>
      <AppointmentList />
    </div>
  );
}
