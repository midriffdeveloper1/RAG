from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.appointment import AppointmentStatus
from app.schemas.appointment import AdminAppointmentUpdate, AppointmentListResponse, AppointmentOut
from app.services.appointment_service import AppointmentService, to_appointment_out

router = APIRouter(prefix="/admin/appointments", tags=["Admin Appointments"])


@router.get("", response_model=AppointmentListResponse)
def list_appointments(
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
    staff_id: str | None = None,
    customer_email: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    appointments = AppointmentService(db).admin_list(
        status=status_filter,
        staff_id=staff_id,
        customer_email=customer_email,
        date_from=date_from,
        date_to=date_to,
    )
    return AppointmentListResponse(
        appointments=[to_appointment_out(a) for a in appointments], total=len(appointments)
    )


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    appointment = AppointmentService(db).get(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return to_appointment_out(appointment)


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: str,
    payload: AdminAppointmentUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    try:
        appointment = AppointmentService(db).admin_update(appointment_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return to_appointment_out(appointment)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    deleted = AppointmentService(db).admin_delete(appointment_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")