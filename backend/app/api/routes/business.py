from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.business import BusinessOut, BusinessUpdate
from app.schemas.faq_policy import FAQCreate, FAQOut, FAQUpdate, PolicyCreate, PolicyOut, PolicyUpdate
from app.services.business_service import BusinessService
from app.services.faq_policy_service import FAQPolicyService

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



@router.get("/faqs", response_model=list[FAQOut])
def list_faqs(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return FAQPolicyService(db).list_faqs()


@router.post("/faqs", response_model=FAQOut, status_code=status.HTTP_201_CREATED)
def create_faq(
    payload: FAQCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)
):
    return FAQPolicyService(db).create_faq(payload)


@router.patch("/faqs/{faq_id}", response_model=FAQOut)
def update_faq(
    faq_id: int,
    payload: FAQUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    faq = FAQPolicyService(db).update_faq(faq_id, payload)
    if faq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    return faq


@router.delete("/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faq(faq_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    if not FAQPolicyService(db).delete_faq(faq_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")



@router.get("/policies", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    return FAQPolicyService(db).list_policies()


@router.post("/policies", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)
):
    return FAQPolicyService(db).create_policy(payload)


@router.patch("/policies/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: int,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    policy = FAQPolicyService(db).update_policy(policy_id, payload)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)
):
    if not FAQPolicyService(db).delete_policy(policy_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")