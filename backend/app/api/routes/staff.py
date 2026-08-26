import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.common import PageParams
from app.schemas.staff import StaffCreate, StaffListResponse, StaffOut, StaffUpdate
from app.services.catalog_service import StaffCatalogService

router = APIRouter(prefix="/admin/staff", tags=["Admin Staff"])


@router.get("", response_model=StaffListResponse)
def list_staff(
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    items, total = StaffCatalogService(db).list_paginated(params)
    return StaffListResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=max(1, math.ceil(total / params.page_size)),
    )


@router.post("", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return StaffCatalogService(db).create(payload)


@router.patch("/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: str,
    payload: StaffUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    staff = StaffCatalogService(db).update(staff_id, payload)
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return staff


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    deleted = StaffCatalogService(db).delete(staff_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")