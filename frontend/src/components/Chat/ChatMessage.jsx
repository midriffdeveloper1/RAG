import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MESSAGE_ROLE } from "../../utils/constants.js";

export default function ChatMessage({ message }) {
  const isUser = message.role === MESSAGE_ROLE.USER;
  const isVoice = message.channel === "voice";

  return (
    <div
      className={`chat-message ${
        isUser
          ? "chat-message--user"
          : "chat-message--assistant"
      }`}
    >
      <div className="chat-message__bubble">
        {isVoice && (
          <span className="chat-message__channel-icon" aria-label={isUser ? "Said by voice" : "Spoken reply"}>
            {isUser ? "🎙" : "🔊"}
          </span>
        )}
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