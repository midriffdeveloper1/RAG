from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.customer import CustomerIdentifyRequest, CustomerIdentifyResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/identify", response_model=CustomerIdentifyResponse)
def identify_customer(payload: CustomerIdentifyRequest, db: Session = Depends(get_db)):
    result = CustomerService(db).identify(payload.email)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return CustomerIdentifyResponse(**result)