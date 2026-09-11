import { MessageSquare, PhoneCall } from "../common/Icons.jsx";

export default function ModeChoice({ businessName, onChat, onVoice }) {
  return (
    <section className="chat-widget mode-choice" aria-label="Choose how to get help">
      <div className="mode-choice__intro">
        <h2>How would you like to get help{businessName ? ` from ${businessName}` : ""}?</h2>
        <p>Type your questions, or talk it through on a live voice call — either way, same assistant.</p>
      </div>

      <div className="mode-choice__options">
        <button type="button" className="mode-choice__card" onClick={onChat}>
          <span className="mode-choice__icon">
            <MessageSquare size={26} />
          </span>
          <span className="mode-choice__title">Chat</span>
          <span className="mode-choice__desc">Type your questions and get quick, clear replies.</span>
        </button>

        <button type="button" className="mode-choice__card" onClick={onVoice}>
          <span className="mode-choice__icon">
            <PhoneCall size={26} />
          </span>
          <span className="mode-choice__title">Voice Call</span>
          <span className="mode-choice__desc">Talk it through live, hands-free, like a phone call.</span>
        </button>
      </div>
    </section>
  );
}