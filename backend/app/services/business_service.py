from sqlalchemy.orm import Session

from app.models.knowledge_base import Business, OpeningHour
from app.schemas.business import BusinessUpdate


class BusinessService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> Business | None:
        return self.db.query(Business).first()

    def update(self, payload: BusinessUpdate) -> Business:
        business = self.get()
        if business is None:
            business = Business(name=payload.name or "My Business")
            self.db.add(business)
            self.db.flush()

        data = payload.model_dump(exclude_unset=True, exclude={"opening_hours"})
        for field, value in data.items():
            setattr(business, field, value)

        if payload.opening_hours is not None:
            existing = {oh.day_of_week: oh for oh in business.opening_hours}
            for item in payload.opening_hours:
                row = existing.get(item.day_of_week)
                if row is None:
                    row = OpeningHour(business_id=business.id, day_of_week=item.day_of_week)
                    self.db.add(row)
                row.open_time = item.open_time
                row.close_time = item.close_time
                row.is_closed = item.is_closed

        self.db.commit()
        self.db.refresh(business)
        return business