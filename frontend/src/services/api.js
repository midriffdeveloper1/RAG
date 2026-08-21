/**
 * API client — public/customer-facing endpoints.
 *
 * `apiClient` carries the baseURL, JSON header, and admin JWT (when
 * present). The functions below are fully wired to the backend.
 */

import axios from "axios";

export const ADMIN_TOKEN_STORAGE_KEY = "ai_support_agent_admin_token";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach the admin JWT (if present) to every request. Public routes like
// /health simply ignore the header, so this is safe to apply globally.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Send a user question to the backend RAG endpoint.
 *
 * @param {{ question: string, sessionId?: string, history?: Array<{role: string, content: string}> }} params
 * @returns {Promise<{ answer: string, sources: Array, session_id: string }>}
 */
export async function sendChatMessage({ question, sessionId, history }) {
  const { data } = await apiClient.post("/chat", {
    question,
    session_id: sessionId,
    history: history || [],
  });
  return data;
}

/**
 * Check backend health. This one works out of the box against
 * GET /api/v1/health.
 */
export async function checkHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}