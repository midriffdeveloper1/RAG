import CustomerList from "../../components/Admin/CustomerList.jsx";

export default function AdminCustomersPage() {
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Customers</h1>
          <p>Everyone who's chatted with your assistant, plus anyone you've added manually.</p>
        </div>
      </div>
      <CustomerList />
    </div>
  );
}