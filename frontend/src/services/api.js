import axios from "axios";
import { getBrowserId } from "../utils/browserId.js";

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

export async function sendChatMessage({ question, sessionId }) {
  const { data } = await apiClient.post("/chat", {
    question,
    browser_id: getBrowserId(),
    session_id: sessionId || null,
  });
  return data;
}

export async function listChatSessions() {
  const { data } = await apiClient.get("/chat/sessions", {
    params: { browser_id: getBrowserId() },
  });
  return data.sessions;
}

export async function getChatSession(sessionId) {
  const { data } = await apiClient.get(`/chat/sessions/${sessionId}`, {
    params: { browser_id: getBrowserId() },
  });
  return data;
}

export async function deleteChatSession(sessionId) {
  await apiClient.delete(`/chat/sessions/${sessionId}`, {
    params: { browser_id: getBrowserId() },
  });
}

export async function checkHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}