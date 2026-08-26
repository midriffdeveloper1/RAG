import AdminLoginForm from "../components/Admin/AdminLoginForm.jsx";

export default function AdminLogin() {
  return (
    <div className="admin-login-page">
      <div className="admin-login-card">
        <h1>Admin sign in</h1>
        <p>Manage the knowledge base that powers the support assistant.</p>
        <AdminLoginForm />
      </div>
    </div>
  );
}