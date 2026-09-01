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

// Staff (backend-paginated)
export async function listStaff({ page = 1, pageSize = 8 } = {}) {
  const { data } = await apiClient.get("/admin/staff", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function listAllStaff() {
  const { data } = await apiClient.get("/admin/staff", { params: { page: 1, page_size: 100 } });
  return data.items;
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

export async function createAppointment(payload) {
  const { data } = await apiClient.post("/admin/appointments", payload);
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

export async function listFaqs() {
  const { data } = await apiClient.get("/admin/business/faqs");
  return data;
}

export async function createFaq(payload) {
  const { data } = await apiClient.post("/admin/business/faqs", payload);
  return data;
}

export async function updateFaq(faqId, payload) {
  const { data } = await apiClient.patch(`/admin/business/faqs/${faqId}`, payload);
  return data;
}

export async function deleteFaq(faqId) {
  await apiClient.delete(`/admin/business/faqs/${faqId}`);
}

export async function listPolicies() {
  const { data } = await apiClient.get("/admin/business/policies");
  return data;
}

export async function createPolicy(payload) {
  const { data } = await apiClient.post("/admin/business/policies", payload);
  return data;
}

export async function updatePolicy(policyId, payload) {
  const { data } = await apiClient.patch(`/admin/business/policies/${policyId}`, payload);
  return data;
}

export async function deletePolicy(policyId) {
  await apiClient.delete(`/admin/business/policies/${policyId}`);
}

export async function listHolidays() {
  const { data } = await apiClient.get("/admin/holidays");
  return data;
}

export async function createHoliday(payload) {
  const { data } = await apiClient.post("/admin/holidays", payload);
  return data;
}

export async function updateHoliday(holidayId, payload) {
  const { data } = await apiClient.patch(`/admin/holidays/${holidayId}`, payload);
  return data;
}

export async function deleteHoliday(holidayId) {
  await apiClient.delete(`/admin/holidays/${holidayId}`);
}

export async function listConversations({ page = 1, pageSize = 10, needsHuman = false } = {}) {
  const { data } = await apiClient.get("/admin/conversations", {
    params: { page, page_size: pageSize, needs_human: needsHuman },
  });
  return data;
}

export async function getConversation(sessionId) {
  const { data } = await apiClient.get(`/admin/conversations/${sessionId}`);
  return data;
}

export async function resolveConversation(sessionId) {
  const { data } = await apiClient.post(`/admin/conversations/${sessionId}/resolve`);
  return data;
}

export async function reopenConversation(sessionId) {
  const { data } = await apiClient.post(`/admin/conversations/${sessionId}/reopen`);
  return data;
}

export async function deleteConversation(sessionId) {
  await apiClient.delete(`/admin/conversations/${sessionId}`);
}

export async function getChatbotConfig() {
  const { data } = await apiClient.get("/admin/chatbot-config");
  return data;
}

export async function updateChatbotConfig(payload) {
  const { data } = await apiClient.put("/admin/chatbot-config", payload);
  return data;
}

export async function previewSystemPrompt() {
  const { data } = await apiClient.get("/admin/chatbot-config/preview-prompt");
  return data.prompt;
}

export async function getAnalyticsOverview() {
  const { data } = await apiClient.get("/admin/analytics/overview");
  return data;
}

export async function listCustomers({ page = 1, pageSize = 8, search = "" } = {}) {
  const { data } = await apiClient.get("/admin/customers", {
    params: { page, page_size: pageSize, search: search || undefined },
  });
  return data;
}

export async function createCustomer(payload) {
  const { data } = await apiClient.post("/admin/customers", payload);
  return data;
}

export async function updateCustomer(customerId, payload) {
  const { data } = await apiClient.patch(`/admin/customers/${customerId}`, payload);
  return data;
}

export async function deleteCustomer(customerId) {
  await apiClient.delete(`/admin/customers/${customerId}`);
}