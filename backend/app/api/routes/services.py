from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.services.catalog_service import ServiceCatalogService

router = APIRouter(prefix="/admin/services", tags=["Admin Services"])


@router.get("", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return ServiceCatalogService(db).list_all()


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return ServiceCatalogService(db).create(payload)


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    service = ServiceCatalogService(db).update(service_id, payload)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    deleted = ServiceCatalogService(db).delete(service_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")