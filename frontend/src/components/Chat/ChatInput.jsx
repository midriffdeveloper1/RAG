// import { useState } from "react";
// import { Send } from "../common/Icons.jsx";

// export default function ChatInput({ onSend, disabled }) {
//   const [value, setValue] = useState("");

//   function handleSubmit(e) {
//     e.preventDefault();
//     if (!value.trim() || disabled) return;
//     onSend(value);
//     setValue("");
//   }

//   return (
//     <form className="chat-input" onSubmit={handleSubmit}>
//       <input
//         type="text"
//         value={value}
//         onChange={(e) => setValue(e.target.value)}
//         placeholder="Ask about hours, pricing, services…"
//         disabled={disabled}
//         aria-label="Type your question"
//       />
//       <button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
//         <Send size={15} />
//         <span>Send</span>
//       </button>
//     </form>
//   );
// }

import { useEffect, useRef, useState } from "react";
import { Send } from "../common/Icons.jsx";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!disabled) {
      inputRef.current?.focus();
    }
  }, [disabled]);

  function handleSubmit(e) {
    e.preventDefault();

    const message = value.trim();

    if (!message || disabled) {
      return;
    }

    onSend(message);
    setValue("");
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask about hours, pricing, services…"
        disabled={disabled}
        aria-label="Type your question"
        autoComplete="off"
      />

      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send message"
      >
        <Send size={15} />
        <span>Send</span>
      </button>
    </form>
  );
}