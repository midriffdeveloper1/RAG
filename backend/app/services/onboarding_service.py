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
    """The reply for this turn, plus any leftover text worth handing to the
    main agent once the customer is identified (so 'hey it's a@b.com, do you
    have a slot tomorrow?' doesn't need to be repeated by the customer)."""

    def __init__(self, reply: str, remainder: str | None = None, identified: bool = False):
        self.reply = reply
        self.remainder = remainder
        self.identified = identified


class OnboardingService:
    """Every new chat session is short-term memory only (this conversation,
    until it's cleared) until it's bound to a long-term customer profile via
    email. This service is the mandatory gate that runs before the agent ever
    sees a message from an unidentified session."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerService(db)

    def handle(
        self, question: str, session: ChatSession, browser_id: str, is_first_turn: bool
    ) -> OnboardingResult:
        match = _EMAIL_PATTERN.search(question)

        if is_first_turn and match is None:
            return OnboardingResult(ASK_EMAIL_MESSAGE)

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