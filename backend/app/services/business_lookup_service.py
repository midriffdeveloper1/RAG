import re

from sqlalchemy.orm import Session

from app.models.knowledge_base import FAQ, OpeningHour, Policy

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "by", "can", "do", "does", "for",
    "how", "i", "if", "in", "is", "it", "of", "on", "or", "our", "the",
    "to", "we", "what", "when", "where", "which", "who", "why", "will",
    "with", "you", "your", "please", "tell", "me", "about",
}

HOURS_KEYWORDS = {"hour", "hours", "open", "opens", "opening", "close", "closes", "closing", "timing", "timings"}
ADDRESS_KEYWORDS = {"address", "location", "located", "directions", "where"}
CONTACT_KEYWORDS = {"phone", "call", "number", "contact", "reach", "email", "mail"}
ABOUT_KEYWORDS = {"about", "who", "describe", "description"}


def _tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_PATTERN.findall(text.lower()) if t not in _STOPWORDS}


class BusinessLookupService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def _match_hours(self, business, tokens: set[str]) -> str | None:
        if not (tokens & HOURS_KEYWORDS):
            return None
        hours = (
            self.db.query(OpeningHour)
            .filter(OpeningHour.business_id == business.id)
            .all()
        )
        if not hours:
            return None
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_day = {h.day_of_week: h for h in hours}
        lines = []
        for day in day_order:
            h = by_day.get(day)
            if h is None:
                continue
            if h.is_closed or not h.open_time:
                lines.append(f"{day}: Closed")
            else:
                lines.append(f"{day}: {h.open_time}–{h.close_time}")
        return "Opening hours:\n" + "\n".join(lines) if lines else None

    def _match_address(self, business, tokens: set[str]) -> str | None:
        if not (tokens & ADDRESS_KEYWORDS) or not business.address:
            return None
        return f"Address: {business.address}"

    def _match_contact(self, business, tokens: set[str]) -> str | None:
        if not (tokens & CONTACT_KEYWORDS):
            return None
        parts = []
        if business.phone:
            parts.append(f"Phone: {business.phone}")
        if business.email:
            parts.append(f"Email: {business.email}")
        return "\n".join(parts) if parts else None

    def _match_about(self, business, tokens: set[str]) -> str | None:
        if not (tokens & ABOUT_KEYWORDS) or not business.description:
            return None
        return f"{business.name}: {business.description}"

    def _match_faq(self, business, tokens: set[str]) -> str | None:
        faqs = self.db.query(FAQ).filter(FAQ.business_id == business.id).all()
        best, best_overlap = None, 0
        for faq in faqs:
            overlap = len(tokens & _tokenize(faq.question))
            if overlap > best_overlap:
                best, best_overlap = faq, overlap
        if best is not None and tokens and best_overlap / len(tokens) >= 0.5:
            return best.answer
        return None

    def _match_policy(self, business, tokens: set[str]) -> str | None:
        policies = self.db.query(Policy).filter(Policy.business_id == business.id).all()
        best, best_overlap = None, 0
        for policy in policies:
            overlap = len(tokens & _tokenize(policy.title))
            if overlap > best_overlap:
                best, best_overlap = policy, overlap
        if best is not None and tokens and best_overlap / len(tokens) >= 0.5:
            return best.content
        return None

    def answer(self, business, question: str) -> str | None:
        if business is None:
            return None
        tokens = _tokenize(question)

        for matcher in (
            self._match_hours,
            self._match_address,
            self._match_contact,
            self._match_faq,
            self._match_policy,
            self._match_about,
        ):
            result = matcher(business, tokens)
            if result:
                return result
        return None