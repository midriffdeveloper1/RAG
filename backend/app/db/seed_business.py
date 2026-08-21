import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.knowledge_base import Business, OpeningHour, Service
from app.models.staff import Staff

logger = logging.getLogger(__name__)
settings = get_settings()

SERVICES = [
    {"name": "Haircut - Women", "description": "Wash, cut, and style.", "price": 800, "duration_minutes": 45},
    {"name": "Haircut - Men", "description": "Classic or modern cut with wash.", "price": 400, "duration_minutes": 30},
    {"name": "Hair Coloring", "description": "Global or root-touch-up coloring.", "price": 2500, "duration_minutes": 90},
    {"name": "Hair Spa", "description": "Deep conditioning and scalp massage.", "price": 1200, "duration_minutes": 60},
    {"name": "Bridal Makeup", "description": "Full bridal makeup with trial.", "price": 8000, "duration_minutes": 120},
    {"name": "Party Makeup", "description": "Event-ready makeup application.", "price": 2000, "duration_minutes": 60},
    {"name": "Manicure", "description": "Nail shaping, cuticle care, and polish.", "price": 500, "duration_minutes": 30},
    {"name": "Pedicure", "description": "Foot soak, exfoliation, and polish.", "price": 600, "duration_minutes": 40},
    {"name": "Facial", "description": "Cleansing, exfoliation, and hydration facial.", "price": 1500, "duration_minutes": 45},
]

OPENING_HOURS = [
    {"day_of_week": "Monday", "open_time": "10:00", "close_time": "19:00", "is_closed": False},
    {"day_of_week": "Tuesday", "open_time": "10:00", "close_time": "19:00", "is_closed": False},
    {"day_of_week": "Wednesday", "open_time": "10:00", "close_time": "19:00", "is_closed": False},
    {"day_of_week": "Thursday", "open_time": "10:00", "close_time": "19:00", "is_closed": False},
    {"day_of_week": "Friday", "open_time": "10:00", "close_time": "19:00", "is_closed": False},
    {"day_of_week": "Saturday", "open_time": "09:00", "close_time": "20:00", "is_closed": False},
    {"day_of_week": "Sunday", "open_time": "11:00", "close_time": "17:00", "is_closed": False},
]

STAFF = [
    {"name": "Ayesha Khan", "email": "ayesha@example.com", "phone": "9800000001",
     "services": ["Haircut - Women", "Hair Coloring", "Hair Spa", "Bridal Makeup", "Party Makeup"]},
    {"name": "Rohan Mehta", "email": "rohan@example.com", "phone": "9800000002",
     "services": ["Haircut - Men", "Hair Spa"]},
    {"name": "Simran Kaur", "email": "simran@example.com", "phone": "9800000003",
     "services": ["Manicure", "Pedicure", "Facial", "Party Makeup"]},
]


def seed_business_catalog() -> None:
    db: Session = SessionLocal()
    try:
        business = db.query(Business).first()
        if business is not None:
            return  # already seeded

        business = Business(
            name=settings.business_name or "Quasar Salon",
            description=settings.business_description or "luxury hair, skin, bridal, and spa studio",
            address="Sector 79, Sahibzada Ajit Singh Nagar(SAS Nagar / Mohali), Punjab",
            phone="+91-9915384074",
            email="contact@salon.example",
        )
        db.add(business)
        db.flush()

        service_by_name: dict[str, Service] = {}
        for item in SERVICES:
            service = Service(business_id=business.id, **item)
            db.add(service)
            service_by_name[item["name"]] = service

        for item in OPENING_HOURS:
            db.add(OpeningHour(business_id=business.id, **item))

        db.flush()

        for item in STAFF:
            staff = Staff(name=item["name"], email=item["email"], phone=item["phone"])
            staff.services = [service_by_name[name] for name in item["services"]]
            db.add(staff)

        db.commit()
        logger.info("Seeded demo business catalog: %s", business.name)
    finally:
        db.close()