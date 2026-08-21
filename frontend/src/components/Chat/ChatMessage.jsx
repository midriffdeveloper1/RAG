import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MESSAGE_ROLE } from "../../utils/constants.js";

export default function ChatMessage({ message }) {
  const isUser = message.role === MESSAGE_ROLE.USER;

  return (
    <div
      className={`chat-message ${
        isUser
          ? "chat-message--user"
          : "chat-message--assistant"
      }`}
    >
      <div className="chat-message__bubble">
        {isUser ? (
          <span>{message.content}</span>
        ) : (
          <div className="chat-message__markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}