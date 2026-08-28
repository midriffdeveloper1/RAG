from datetime import date as date_type
import re

from sqlalchemy.orm import Session

from app.models.knowledge_base import Holiday
from app.schemas.holiday import HolidayCreate, HolidayUpdate
from app.services.business_service import BusinessService
from app.services.time_utils import day_name


class HolidayService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.business = BusinessService(db)

    def list(self, include_inactive: bool = True) -> list[Holiday]:
        business = self.business.get()
        query = self.db.query(Holiday).filter(Holiday.business_id == business.id)
        if not include_inactive:
            query = query.filter(Holiday.is_active.is_(True))
        return query.order_by(Holiday.date.is_(None), Holiday.date, Holiday.day_of_week).all()

    def create(self, payload: HolidayCreate) -> Holiday:
        business = self.business.get()
        data = payload.model_dump()
        if data.get("day_of_week"):
            data["day_of_week"] = data["day_of_week"].title()
        holiday = Holiday(business_id=business.id, **data)
        self.db.add(holiday)
        self.db.commit()
        self.db.refresh(holiday)
        return holiday

    def update(self, holiday_id: str, payload: HolidayUpdate) -> Holiday | None:
        holiday = self.db.query(Holiday).filter(Holiday.id == holiday_id).first()
        if holiday is None:
            return None
        updates = payload.model_dump(exclude_unset=True)
        if updates.get("day_of_week"):
            updates["day_of_week"] = updates["day_of_week"].title()
        # Switching from one-off <-> recurring should clear the other key.
        if "date" in updates and updates["date"] is not None:
            holiday.day_of_week = None
        if "day_of_week" in updates and updates["day_of_week"] is not None:
            holiday.date = None
        for field, value in updates.items():
            setattr(holiday, field, value)
        self.db.commit()
        self.db.refresh(holiday)
        return holiday

    def delete(self, holiday_id: str) -> bool:
        holiday = self.db.query(Holiday).filter(Holiday.id == holiday_id).first()
        if holiday is None:
            return False
        self.db.delete(holiday)
        self.db.commit()
        return True

    # Booking-time lookup

    def get_closure_for_date(self, business_id: str, target_date: date_type) -> Holiday | None:
        one_off = (
            self.db.query(Holiday)
            .filter(
                Holiday.business_id == business_id,
                Holiday.is_active.is_(True),
                Holiday.date == target_date,
            )
            .first()
        )
        if one_off is not None:
            return one_off

        return (
            self.db.query(Holiday)
            .filter(
                Holiday.business_id == business_id,
                Holiday.is_active.is_(True),
                Holiday.day_of_week == day_name(target_date),
            )
            .first()
        )

    def get_recurring_closure(self, business_id: str, day_of_week: str) -> Holiday | None:
        return (
            self.db.query(Holiday)
            .filter(
                Holiday.business_id == business_id,
                Holiday.is_active.is_(True),
                Holiday.day_of_week == day_of_week,
            )
            .first()
        )

    def find_by_name(self, business_id: str, question: str) -> Holiday | None:
        holidays = (
            self.db.query(Holiday)
            .filter(
                Holiday.business_id == business_id,
                Holiday.is_active.is_(True),
                Holiday.note.isnot(None),
            )
            .all()
        )
        q_tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
        best, best_len = None, 0
        for holiday in holidays:
            note_tokens = set(re.findall(r"[a-z0-9]+", holiday.note.lower()))
            if not note_tokens or not note_tokens.issubset(q_tokens):
                continue
            if len(note_tokens) > best_len:
                best, best_len = holiday, len(note_tokens)
        return best

    def describe_one(self, holiday: Holiday) -> str:
        when = str(holiday.date) if holiday.date else f"every {holiday.day_of_week}"
        scope = "closed all day" if holiday.is_full_day else f"closed {holiday.start_time}-{holiday.end_time}"
        note = f" ({holiday.note})" if holiday.note else ""
        return f"On {when}, we're {scope}{note}."

    def describe_upcoming(self, business_id: str, days_ahead: int = 30) -> str | None:
       
        holidays = (
            self.db.query(Holiday)
            .filter(Holiday.business_id == business_id, Holiday.is_active.is_(True))
            .all()
        )
        if not holidays:
            return None

        lines = []
        for h in holidays:
            when = str(h.date) if h.date else f"every {h.day_of_week}"
            scope = "closed all day" if h.is_full_day else f"closed {h.start_time}-{h.end_time}"
            note = f" ({h.note})" if h.note else ""
            lines.append(f"- {when}: {scope}{note}")
        return "Holidays / closures:\n" + "\n".join(lines)