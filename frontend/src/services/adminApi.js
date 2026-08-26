import { apiClient } from "./api.js";

export async function adminLogin(email, password) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  return data;
}

export async function getCurrentAdmin() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export async function listDocuments({ page = 1, pageSize = 8 } = {}) {
  const { data } = await apiClient.get("/admin/documents", {
    params: { page, page_size: pageSize },
  });
  return {
    items: data.documents,
    total: data.total,
    page: data.page,
    page_size: data.page_size,
    total_pages: data.total_pages,
  };
}

export async function uploadDocument(file, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await apiClient.post("/admin/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return data;
}

export async function reindexDocument(documentId) {
  const { data } = await apiClient.post(`/admin/documents/${documentId}/reindex`);
  return data;
}

export async function deleteDocument(documentId) {
  const { data } = await apiClient.delete(`/admin/documents/${documentId}`);
  return data;
}

export async function listServices({ page = 1, pageSize = 8 } = {}) {
  const { data } = await apiClient.get("/admin/services", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function listAllServices() {
  const { data } = await apiClient.get("/admin/services", { params: { page: 1, page_size: 100 } });
  return data.items;
}

export async function createService(payload) {
  const { data } = await apiClient.post("/admin/services", payload);
  return data;
}

export async function updateService(serviceId, payload) {
  const { data } = await apiClient.patch(`/admin/services/${serviceId}`, payload);
  return data;
}

export async function deleteService(serviceId) {
  await apiClient.delete(`/admin/services/${serviceId}`);
}

export async function listStaff({ page = 1, pageSize = 8 } = {}) {
  const { data } = await apiClient.get("/admin/staff", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function createStaff(payload) {
  const { data } = await apiClient.post("/admin/staff", payload);
  return data;
}

export async function updateStaff(staffId, payload) {
  const { data } = await apiClient.patch(`/admin/staff/${staffId}`, payload);
  return data;
}

export async function deleteStaff(staffId) {
  await apiClient.delete(`/admin/staff/${staffId}`);
}

export async function listAppointments({ page = 1, pageSize = 8, filters = {} } = {}) {
  const { data } = await apiClient.get("/admin/appointments", {
    params: { page, page_size: pageSize, ...filters },
  });
  return {
    items: data.appointments,
    total: data.total,
    page: data.page,
    page_size: data.page_size,
    total_pages: data.total_pages,
  };
}

export async function updateAppointment(appointmentId, payload) {
  const { data } = await apiClient.patch(`/admin/appointments/${appointmentId}`, payload);
  return data;
}

export async function deleteAppointment(appointmentId) {
  await apiClient.delete(`/admin/appointments/${appointmentId}`);
}

export async function getBusiness() {
  const { data } = await apiClient.get("/admin/business");
  return data;
}

export async function updateBusiness(payload) {
  const { data } = await apiClient.put("/admin/business", payload);
  return data;
}

export async function getChatbotConfig() {
  const { data } = await apiClient.get("/admin/chatbot-config");
  return data;
}

export async function updateChatbotConfig(payload) {
  const { data } = await apiClient.put("/admin/chatbot-config", payload);
  return data;
}

export async function getAnalyticsOverview() {
  const { data } = await apiClient.get("/admin/analytics/overview");
  return data;
}
