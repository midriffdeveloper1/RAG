/**
 * Admin API — login and document management.
 *
 * Unlike services/api.js's sendChatMessage() (still a stub), every
 * function here is fully wired to the backend, since the admin
 * login + document ingestion pipeline is implemented end to end.
 */

import { apiClient } from "./api.js";

// --- Auth --------------------------------------------------------------

export async function adminLogin(email, password) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  return data; // { access_token, token_type, expires_in_minutes }
}

export async function getCurrentAdmin() {
  const { data } = await apiClient.get("/auth/me");
  return data; // { id, email }
}

// --- Documents -----------------------------------------------------------

export async function listDocuments() {
  const { data } = await apiClient.get("/admin/documents");
  return data; // { documents: [...], total }
}

export async function uploadDocument(file, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await apiClient.post("/admin/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return data; // DocumentOut
}

export async function reindexDocument(documentId) {
  const { data } = await apiClient.post(`/admin/documents/${documentId}/reindex`);
  return data; // DocumentOut
}

export async function deleteDocument(documentId) {
  const { data } = await apiClient.delete(`/admin/documents/${documentId}`);
  return data; // DocumentActionResponse
}