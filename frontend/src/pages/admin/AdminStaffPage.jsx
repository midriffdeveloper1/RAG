import { useEffect, useState } from "react";
import StaffList from "../../components/Admin/StaffList.jsx";
import { listAllServices } from "../../services/adminApi.js";

export default function AdminStaffPage() {
  const [services, setServices] = useState([]);

  useEffect(() => {
    listAllServices()
      .then(setServices)
      .catch(() => setServices([]));
  }, []);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Staff</h1>
          <p>Manage the people customers can book appointments with.</p>
        </div>
      </div>
      <StaffList services={services} />
    </div>
  );
}
