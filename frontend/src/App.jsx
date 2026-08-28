import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import ProtectedRoute from "./components/Admin/ProtectedRoute.jsx";
import AdminLayout from "./components/layout/AdminLayout.jsx";
import Footer from "./components/layout/Footer.jsx";
import Header from "./components/layout/Header.jsx";
import AdminLogin from "./pages/AdminLogin.jsx";
import AdminAppointmentsPage from "./pages/admin/AdminAppointmentsPage.jsx";
import AdminBusinessPage from "./pages/admin/AdminBusinessPage.jsx";
import AdminChatbotConfigPage from "./pages/admin/AdminChatbotConfigPage.jsx";
import AdminConversationsPage from "./pages/admin/AdminConversationsPage.jsx";
import AdminCustomersPage from "./pages/admin/AdminCustomersPage.jsx";
import AdminKnowledgeBasePage from "./pages/admin/AdminKnowledgeBasePage.jsx";
import AdminOverview from "./pages/admin/AdminOverview.jsx";
import AdminServicesPage from "./pages/admin/AdminServicesPage.jsx";
import AdminStaffPage from "./pages/admin/AdminStaffPage.jsx";
import Home from "./pages/Home.jsx";

export default function App() {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith("/admin");

  return (
    <div className="app-shell">
      {!isAdminRoute && <Header />}
      <main className={isAdminRoute ? "app-main app-main--admin" : "app-main"}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/admin/login" element={<AdminLogin />} />

          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="analytics" replace />} />
            <Route path="analytics" element={<AdminOverview />} />
            <Route path="staff" element={<AdminStaffPage />} />
            <Route path="services" element={<AdminServicesPage />} />
            <Route path="appointments" element={<AdminAppointmentsPage />} />
            <Route path="conversations" element={<AdminConversationsPage />} />
            <Route path="customers" element={<AdminCustomersPage />} />
            <Route path="knowledge-base" element={<AdminKnowledgeBasePage />} />
            <Route path="business" element={<AdminBusinessPage />} />
            <Route path="chatbot-config" element={<AdminChatbotConfigPage />} />
          </Route>
        </Routes>
      </main>
      {!isAdminRoute && <Footer />}
    </div>
  );
}