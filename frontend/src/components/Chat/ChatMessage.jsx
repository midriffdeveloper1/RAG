import { MESSAGE_ROLE } from "../../utils/constants.js";

export default function ChatMessage({ message }) {
  const isUser = message.role === MESSAGE_ROLE.USER;

  return (
    <div className={`chat-message ${isUser ? "chat-message--user" : "chat-message--assistant"}`}>
      <div className="chat-message__bubble">{message.content}</div>
    </div>
  );
}
