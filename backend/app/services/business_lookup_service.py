import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.knowledge_base import FAQ, OpeningHour, Policy, Service
from app.models.staff import Staff

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
HOLIDAY_KEYWORDS = {
    "holiday", "holidays", "closed", "closure", "closures", "vacation",
    "festival", "leave", "offday",
}
SERVICE_KEYWORDS = {
    "service", "services", "treatment", "treatments", "offer", "offers",
    "offering", "offerings", "menu", "package", "packages", "price", "prices",
    "pricing", "cost", "costs", "rate", "rates",
}
STAFF_KEYWORDS = {
    "staff", "stylist", "stylists", "therapist", "therapists", "team",
    "employee", "employees", "specialist", "specialists", "barber", "barbers",
}

_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_WEEKDAY_TOKENS = {d.lower(): d for d in _WEEKDAY_NAMES}
_RELATIVE_DAY_OFFSETS = {"today": 0, "tonight": 0, "tomorrow": 1}


def _tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_PATTERN.findall(text.lower()) if t not in _STOPWORDS}


def _resolve_day_query(tokens: set[str]) -> tuple[str, date | None] | None:
    for token, offset in _RELATIVE_DAY_OFFSETS.items():
        if token in tokens:
            target = date.today() + timedelta(days=offset)
            return target.strftime("%A"), target
    for token, day in _WEEKDAY_TOKENS.items():
        if token in tokens:
            return day, None
    return None


class BusinessLookupService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def _match_hours(self, business, tokens: set[str], raw_question: str) -> str | None:
        from app.services.holiday_service import HolidayService

        holidays = HolidayService(self.db)

        named = holidays.find_by_name(business.id, raw_question)
        if named is not None:
            return holidays.describe_one(named)

        day_query = _resolve_day_query(tokens)
        if day_query is not None:
            day, exact_date = day_query
            opening = (
                self.db.query(OpeningHour)
                .filter(OpeningHour.business_id == business.id, OpeningHour.day_of_week == day)
                .first()
            )
            closure = (
                holidays.get_closure_for_date(business.id, exact_date)
                if exact_date is not None
                else holidays.get_recurring_closure(business.id, day)
            )
            plural = "s" if exact_date is None else ""

            if closure is not None and closure.is_full_day:
                note = f" ({closure.note})" if closure.note else ""
                return f"We're closed on {day}{plural}{note}."
            if opening is None or opening.is_closed or not opening.open_time:
                return f"We're closed on {day}{plural}."
            if closure is not None:
                note = f" ({closure.note})" if closure.note else ""
                return (
                    f"{day}: {opening.open_time}\u2013{opening.close_time}, except "
                    f"{closure.start_time}\u2013{closure.end_time} when we're closed{note}."
                )
            return f"{day}: {opening.open_time}\u2013{opening.close_time}"

        if not (tokens & HOURS_KEYWORDS):
            return None

        hours = (
            self.db.query(OpeningHour)
            .filter(OpeningHour.business_id == business.id)
            .all()
        )
        if not hours:
            return None
        by_day = {h.day_of_week: h for h in hours}
        lines = []
        for day in _WEEKDAY_NAMES:
            h = by_day.get(day)
            if h is None:
                continue
            closure = holidays.get_recurring_closure(business.id, day)
            if (closure is not None and closure.is_full_day) or h.is_closed or not h.open_time:
                note = f" ({closure.note})" if closure and closure.note else ""
                lines.append(f"{day}: Closed{note}")
            else:
                lines.append(f"{day}: {h.open_time}\u2013{h.close_time}")
        return "Opening hours:\n" + "\n".join(lines) if lines else None

    def _match_address(self, business, tokens: set[str], raw_question: str) -> str | None:
        if not (tokens & ADDRESS_KEYWORDS) or not business.address:
            return None
        return f"Address: {business.address}"

    def _match_contact(self, business, tokens: set[str], raw_question: str) -> str | None:
        if not (tokens & CONTACT_KEYWORDS):
            return None
        parts = []
        if business.phone:
            parts.append(f"Phone: {business.phone}")
        if business.email:
            parts.append(f"Email: {business.email}")
        return "\n".join(parts) if parts else None

    def _match_about(self, business, tokens: set[str], raw_question: str) -> str | None:
        if not (tokens & ABOUT_KEYWORDS) or not business.description:
            return None
        return f"{business.name}: {business.description}"

    def _match_services(self, business, tokens: set[str], raw_question: str) -> str | None:
        if not (tokens & SERVICE_KEYWORDS):
            return None
        services = (
            self.db.query(Service)
            .filter(Service.business_id == business.id)
            .order_by(Service.name)
            .all()
        )
        if not services:
            return None
        shown = services[:8]
        lines = []
        for s in shown:
            bits = [s.name]
            if s.price is not None:
                bits.append(f"\u20b9{s.price:g}")
            if s.duration_minutes:
                bits.append(f"{s.duration_minutes} min")
            lines.append(" — ".join(bits))
        note = (
            f"\n(+{len(services) - 8} more not shown — ask about a specific service or category)"
            if len(services) > 8
            else ""
        )
        return "Services:\n" + "\n".join(lines) + note

    def _match_staff(self, business, tokens: set[str], raw_question: str) -> str | None:
        if not (tokens & STAFF_KEYWORDS):
            return None
        staff = (
            self.db.query(Staff)
            .filter(Staff.is_active == True)  # noqa: E712
            .order_by(Staff.name)
            .all()
        )
        if not staff:
            return None
        return "Team: " + ", ".join(s.name for s in staff[:12])

    def _match_faq(self, business, tokens: set[str], raw_question: str) -> str | None:
        faqs = self.db.query(FAQ).filter(FAQ.business_id == business.id).all()
        best, best_overlap = None, 0
        for faq in faqs:
            overlap = len(tokens & _tokenize(faq.question))
            if overlap > best_overlap:
                best, best_overlap = faq, overlap
        if best is not None and tokens and best_overlap / len(tokens) >= 0.5:
            return best.answer
        return None

    def _match_holidays(self, business, tokens: set[str], raw_question: str) -> str | None:
        if not (tokens & HOLIDAY_KEYWORDS):
            return None
        from app.services.holiday_service import HolidayService

        return HolidayService(self.db).describe_upcoming(business.id)

    def _match_policy(self, business, tokens: set[str], raw_question: str) -> str | None:
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
            self._match_holidays,
            self._match_address,
            self._match_contact,
            # self._match_services,
            # self._match_staff,
            self._match_faq,
            self._match_policy,
            self._match_about,
        ):
            result = matcher(business, tokens, question)
            if result:
                return result
        return None