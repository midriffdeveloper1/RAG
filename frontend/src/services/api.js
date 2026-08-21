import axios from "axios";

export const ADMIN_TOKEN_STORAGE_KEY = "ai_support_agent_admin_token";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});


export async function sendChatMessage({ question, sessionId, history }) {
  const { data } = await apiClient.post("/chat", {
    question,
    session_id: sessionId,
    history: history || [],
  });
  return data;
}

export async function checkHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}