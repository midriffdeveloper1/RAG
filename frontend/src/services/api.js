import axios from "axios";
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Send a user question to the backend RAG endpoint.
 * TODO: implement once POST /chat is live.
 *
 * @param {{ question: string, sessionId?: string }} params
 * @returns {Promise<{ answer: string, sources: Array, session_id: string }>}
 */
export async function sendChatMessage(/* { question, sessionId } */) {
  throw new Error("sendChatMessage() is not implemented yet — wire this up to POST /chat.");
}
export async function checkHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}
