from datetime import date, datetime, time

from pydantic import BaseModel

from app.models.appointment import AppointmentStatus


class SlotOut(BaseModel):
    start_time: time
    end_time: time
    staff_id: str
    staff_name: str


class AppointmentOut(BaseModel):
    id: str
    reference_code: str | None = None
    service_id: str
    service_name: str
    staff_id: str
    staff_name: str
    customer_name: str
    customer_email: str
    customer_phone: str
    appointment_date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    notes: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentOut]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int = 1


class AdminAppointmentCreate(BaseModel):
    service_id: str
    staff_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    appointment_date: date
    start_time: time
    notes: str | None = None


class AdminAppointmentUpdate(BaseModel):
    service_id: str | None = None
    appointment_date: date | None = None
    start_time: time | None = None
    staff_id: str | None = None
    status: AppointmentStatus | None = None
    notes: str | None = None
    cancellation_reason: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None