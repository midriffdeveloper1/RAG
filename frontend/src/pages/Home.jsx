import ChatWidget from "../components/Chat/ChatWidget.jsx";
import { BUSINESS_NAME } from "../utils/constants.js";

export default function Home() {
  return (
    <div className="home-page">
      <div className="home-page__intro">
        <h1>Ask us anything</h1>
        <p>
          Our assistant knows about services, pricing, hours, and policies —
          available around the clock.
        </p>
      </div>
      <ChatWidget />
    </div>
  );
}
