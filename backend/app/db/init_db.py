import logging
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.admin import Admin

from app import models as _models  # noqa: F401  (registers all mappers)

logger = logging.getLogger(__name__)
settings = get_settings()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_admin() -> None:
   
    db: Session = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.email == settings.admin_email).first()

        if existing is None:
            admin = Admin(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Seeded admin account: %s", settings.admin_email)
        elif settings.admin_seed_force_update:
            existing.hashed_password = hash_password(settings.admin_password)
            db.commit()
            logger.info("Updated admin password for: %s", settings.admin_email)
    finally:
        db.close()


def init_db() -> None:
    create_tables()
    seed_admin()

    from app.db.seed_business import seed_business_catalog

    seed_business_catalog()