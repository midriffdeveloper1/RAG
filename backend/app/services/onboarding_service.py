import re

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.services.customer_service import CustomerService

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

ASK_EMAIL_MESSAGE = (
    "Hi there! Before we get started, could you share your email address? It lets me "
    "pull up your details if you've chatted with us before, or set up a quick profile "
    "if this is your first time."
)
INVALID_EMAIL_MESSAGE = (
    "I'll need a valid email address to continue — could you share it? "
    "For example: yourname@example.com"
)


class OnboardingResult:

    def __init__(self, reply: str, remainder: str | None = None, identified: bool = False):
        self.reply = reply
        self.remainder = remainder
        self.identified = identified


class OnboardingService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerService(db)

    def _ask_email_message(self) -> str:
        try:
            from app.models.chatbot_config import ChatbotConfig

            config = self.db.query(ChatbotConfig).first()
            if config and config.greeting_message:
                return config.greeting_message
        except Exception:  # pragma: no cover - defensive, never block onboarding
            pass
        return ASK_EMAIL_MESSAGE

    def handle(
        self, question: str, session: ChatSession, browser_id: str, is_first_turn: bool
    ) -> OnboardingResult:
        match = _EMAIL_PATTERN.search(question)

        if is_first_turn and match is None:
            return OnboardingResult(self._ask_email_message())

        if match is None:
            return OnboardingResult(INVALID_EMAIL_MESSAGE)

        result = self.customers.identify(match.group(0))
        if "error" in result:
            return OnboardingResult(f"{result['error']} Could you double-check and resend your email?")

        session.customer_id = result["customer"]["id"]
        name = (result["customer"]["name"] or "").strip()

        if result["is_returning"]:
            greeting = f"Welcome back{f', {name}' if name else ''}! How can I help today?"
        else:
            greeting = "Welcome! Great to have you here — what can I help you with today?"

        remainder = _EMAIL_PATTERN.sub("", question).strip(" ,.-\n\t")
        return OnboardingResult(greeting, remainder=remainder or None, identified=True)