import ChatbotConfigForm from "../../components/Admin/ChatbotConfigForm.jsx";

export default function AdminChatbotConfigPage() {
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Chatbot configuration</h1>
          <p>Control how your assistant looks, sounds, and what it's allowed to do.</p>
        </div>
      </div>
      <ChatbotConfigForm />
    </div>
  );
}
