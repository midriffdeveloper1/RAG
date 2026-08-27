import { useEffect, useState } from "react";
import AppointmentList from "../../components/Admin/AppointmentList.jsx";
import { listAllServices, listAllStaff } from "../../services/adminApi.js";

export default function AdminAppointmentsPage() {
  const [services, setServices] = useState([]);
  const [staff, setStaff] = useState([]);

  useEffect(() => {
    listAllServices().then(setServices).catch(() => setServices([]));
    listAllStaff().then(setStaff).catch(() => setStaff([]));
  }, []);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Appointments</h1>
          <p>Every booking made through the chat assistant — or added manually.</p>
        </div>
      </div>
      <AppointmentList services={services} staff={staff} />
    </div>
  );
}