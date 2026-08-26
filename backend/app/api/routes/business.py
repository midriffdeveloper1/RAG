from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.business import BusinessOut, BusinessUpdate
from app.services.business_service import BusinessService

router = APIRouter(prefix="/admin/business", tags=["Admin Business"])


@router.get("", response_model=BusinessOut)
def get_business(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return BusinessService(db).get()


@router.put("", response_model=BusinessOut)
def update_business(
    payload: BusinessUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return BusinessService(db).update(payload)