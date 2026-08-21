export const BUSINESS_NAME = "AI Support Assistant";

export const SUGGESTED_QUESTIONS = [
  "What is your business information?",
  "what is your services and cost?",
  "what is your opening hours and closing hours?",
]

export const MESSAGE_ROLE = {
  USER: "user",
  ASSISTANT: "assistant",
};

// Sent as `history` on every /chat request — kept in sync with the
// backend's MAX_HISTORY_EXCHANGES (3 exchanges = 6 messages).
export const MAX_HISTORY_MESSAGES = 6;