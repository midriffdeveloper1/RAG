import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.common import PageParams
from app.schemas.customer import (
    CustomerAdminCreate,
    CustomerAdminOut,
    CustomerAdminUpdate,
    CustomerIdentifyRequest,
    CustomerIdentifyResponse,
    CustomerListResponse,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/identify", response_model=CustomerIdentifyResponse)
def identify_customer(payload: CustomerIdentifyRequest, db: Session = Depends(get_db)):
    result = CustomerService(db).identify(payload.email)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return CustomerIdentifyResponse(**result)



admin_router = APIRouter(prefix="/admin/customers", tags=["Admin Customers"])


@admin_router.get("", response_model=CustomerListResponse)
def list_customers(
    search: str | None = None,
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    items, total = CustomerService(db).admin_list_paginated(
        page=params.page, page_size=params.page_size, search=search
    )
    return CustomerListResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=max(1, math.ceil(total / params.page_size)),
    )


@admin_router.post("", response_model=CustomerAdminOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerAdminCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    try:
        return CustomerService(db).admin_create(payload.email, payload.name, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@admin_router.patch("/{customer_id}", response_model=CustomerAdminOut)
def update_customer(
    customer_id: str,
    payload: CustomerAdminUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    try:
        return CustomerService(db).admin_update(
            customer_id, email=payload.email, name=payload.name, phone=payload.phone
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@admin_router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)
):
    if not CustomerService(db).admin_delete(customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")