from datetime import date, datetime, time

from pydantic import BaseModel

from app.models.appointment import AppointmentStatus


class SlotOut(BaseModel):
    start_time: time
    end_time: time
    staff_id: int
    staff_name: str


class AppointmentOut(BaseModel):
    id: int
    service_id: int
    service_name: str
    staff_id: int
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


class AdminAppointmentUpdate(BaseModel):
    appointment_date: date | None = None
    start_time: time | None = None
    staff_id: int | None = None
    status: AppointmentStatus | None = None
    notes: str | None = None
    cancellation_reason: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None