import re

from app.models.chat_session import ChatSession

_EXPLICIT_PATTERNS = [
    r"\btalk(ing)? to (the |a |an )?(human|person|agent|someone|somebody|staff|team|representative)\b",
    r"\bspeak (to|with) (the |a |an )?(human|person|agent|someone|somebody|staff|team|representative|manager)\b",
    r"\breal (human|person)\b",
    r"\bcustomer (service|support)\b",
    r"\bconnect me\b",
    r"\btransfer me\b",
    r"\bhuman (agent|support|help)\b",
    r"\bcan i (talk|speak) to (the |a |an )?(someone|somebody|person|human|agent|staff|manager)\b",
    r"\bi (need|want|would like) to (talk|speak) (to|with) (the |a |an )?(someone|somebody|person|human|agent|staff|manager)\b",
    r"\bthis (bot|chatbot|ai) (is|isn'?t|not) (helping|working|useful)\b",
    r"\bi want a (manager|supervisor)\b",
    r"\braise (a |the )?(support )?ticket\b",
    r"\b(open|create|file) a (support )?ticket\b",
    r"\bescalate (this|it)\b",
]

_FRUSTRATION_PATTERNS = [
    r"\bthis is (useless|ridiculous|a joke|pointless)\b",
    r"\byou'?re not (listening|helping|understanding)\b",
    r"\b(so|really|extremely) (frustrated|annoyed|angry)\b",
    r"\bworst (support|service|bot|assistant)\b",
    r"\bwaste of (my )?time\b",
    r"\bnever mind,? forget it\b",
    r"\bi give up\b",
    r"\byou'?re (shit|useless|stupid|garbage|terrible|awful|rubbish|dumb)\b",
    r"\b(this is )?(shit|nonsense|rubbish|garbage)\b",
    r"\b(idiot|stupid|dumb) (bot|chatbot|ai|assistant)\b",
]

UNRESOLVED_STREAK_THRESHOLD = 2


def _matches_any(patterns: list[str], text: str) -> bool:
    lowered = text.lower()
    return any(re.search(p, lowered) for p in patterns)


class SupportAgent:
    agent_name = "support"

    def check_message(self, question: str) -> str | None:
        if _matches_any(_EXPLICIT_PATTERNS, question):
            return "Customer explicitly asked to speak with a human."
        if _matches_any(_FRUSTRATION_PATTERNS, question):
            return "Customer showed signs of frustration with the assistant."
        return None

    def check_streak(self, session: ChatSession) -> str | None:
        if session.unresolved_streak >= UNRESOLVED_STREAK_THRESHOLD:
            return (
                f"Assistant could not resolve the request after "
                f"{session.unresolved_streak} consecutive attempts."
            )
        return None

    def handoff_reply(self, ticket_number: str) -> str:
        return (
            "I've flagged this conversation for our team so a person can take it from here — "
            f"they'll follow up with you directly. Your ticket number is {ticket_number} — you "
            "can check its status any time from the panel at the bottom of the sidebar. If you "
            "have another question in the meantime, please feel free to start a new chat. Thanks "
            "for your patience!"
        )