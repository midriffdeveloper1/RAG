from sqlalchemy.orm import Session

from app.models.knowledge_base import Business, Service
from app.models.staff import Staff
from app.schemas.common import PageParams
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.schemas.staff import StaffCreate, StaffUpdate


class ServiceCatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Service]:
        return self.db.query(Service).order_by(Service.name).all()

    def list_paginated(self, params: PageParams) -> tuple[list[Service], int]:
        query = self.db.query(Service).order_by(Service.name)
        total = query.count()
        items = query.offset(params.offset).limit(params.page_size).all()
        return items, total

    def get(self, service_id: int) -> Service | None:
        return self.db.query(Service).filter(Service.id == service_id).first()

    def create(self, payload: ServiceCreate) -> Service:
        business = self.db.query(Business).first()
        service = Service(business_id=business.id, **payload.model_dump())
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def update(self, service_id: int, payload: ServiceUpdate) -> Service | None:
        service = self.get(service_id)
        if service is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(service, field, value)
        self.db.commit()
        self.db.refresh(service)
        return service

    def delete(self, service_id: int) -> bool:
        service = self.get(service_id)
        if service is None:
            return False
        self.db.delete(service)
        self.db.commit()
        return True


class StaffCatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Staff]:
        return self.db.query(Staff).order_by(Staff.name).all()

    def list_paginated(self, params: PageParams) -> tuple[list[Staff], int]:
        query = self.db.query(Staff).order_by(Staff.name)
        total = query.count()
        items = query.offset(params.offset).limit(params.page_size).all()
        return items, total

    def get(self, staff_id: int) -> Staff | None:
        return self.db.query(Staff).filter(Staff.id == staff_id).first()

    def _resolve_services(self, service_ids: list[int]) -> list[Service]:
        if not service_ids:
            return []
        return self.db.query(Service).filter(Service.id.in_(service_ids)).all()

    def create(self, payload: StaffCreate) -> Staff:
        staff = Staff(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            is_active=payload.is_active,
        )
        staff.services = self._resolve_services(payload.service_ids)
        self.db.add(staff)
        self.db.commit()
        self.db.refresh(staff)
        return staff

    def update(self, staff_id: int, payload: StaffUpdate) -> Staff | None:
        staff = self.get(staff_id)
        if staff is None:
            return None
        data = payload.model_dump(exclude_unset=True, exclude={"service_ids"})
        for field, value in data.items():
            setattr(staff, field, value)
        if payload.service_ids is not None:
            staff.services = self._resolve_services(payload.service_ids)
        self.db.commit()
        self.db.refresh(staff)
        return staff

    def delete(self, staff_id: int) -> bool:
        staff = self.get(staff_id)
        if staff is None:
            return False
        self.db.delete(staff)
        self.db.commit()
        return True