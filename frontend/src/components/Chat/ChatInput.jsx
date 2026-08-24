// import { useState } from "react";

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
//       <button type="submit" disabled={disabled || !value.trim()}>
//         Send
//       </button>
//     </form>
//   );
// }


import { useState } from "react";
import { Send } from "../common/Icons.jsx";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask about hours, pricing, services…"
        disabled={disabled}
        aria-label="Type your question"
      />
      <button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
        <Send size={15} />
        <span>Send</span>
      </button>
    </form>
  );
}