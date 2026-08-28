from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.holiday import HolidayCreate, HolidayOut, HolidayUpdate
from app.services.holiday_service import HolidayService

router = APIRouter(prefix="/admin/holidays", tags=["Admin Holidays"])


@router.get("", response_model=list[HolidayOut])
def list_holidays(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return HolidayService(db).list()


@router.post("", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
def create_holiday(
    payload: HolidayCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)
):
    return HolidayService(db).create(payload)


@router.patch("/{holiday_id}", response_model=HolidayOut)
def update_holiday(
    holiday_id: str,
    payload: HolidayUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    holiday = HolidayService(db).update(holiday_id, payload)
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")
    return holiday


@router.delete("/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(
    holiday_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)
):
    if not HolidayService(db).delete(holiday_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")