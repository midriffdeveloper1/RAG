export default function TypingIndicator() {
  return (
    <div className="chat-message chat-message--assistant">
      <div className="chat-message__bubble chat-message__bubble--typing">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
