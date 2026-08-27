from sqlalchemy.orm import Session

from app.models.knowledge_base import FAQ, Policy
from app.schemas.faq_policy import FAQCreate, FAQUpdate, PolicyCreate, PolicyUpdate
from app.services.business_service import BusinessService


class FAQPolicyService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.business = BusinessService(db)

    def list_faqs(self) -> list[FAQ]:
        business = self.business.get()
        return self.db.query(FAQ).filter(FAQ.business_id == business.id).order_by(FAQ.id).all()

    def create_faq(self, payload: FAQCreate) -> FAQ:
        business = self.business.get()
        faq = FAQ(business_id=business.id, **payload.model_dump())
        self.db.add(faq)
        self.db.commit()
        self.db.refresh(faq)
        return faq

    def update_faq(self, faq_id: int, payload: FAQUpdate) -> FAQ | None:
        faq = self.db.query(FAQ).filter(FAQ.id == faq_id).first()
        if faq is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(faq, field, value)
        self.db.commit()
        self.db.refresh(faq)
        return faq

    def delete_faq(self, faq_id: int) -> bool:
        faq = self.db.query(FAQ).filter(FAQ.id == faq_id).first()
        if faq is None:
            return False
        self.db.delete(faq)
        self.db.commit()
        return True


    def list_policies(self) -> list[Policy]:
        business = self.business.get()
        return self.db.query(Policy).filter(Policy.business_id == business.id).order_by(Policy.id).all()

    def create_policy(self, payload: PolicyCreate) -> Policy:
        business = self.business.get()
        policy = Policy(business_id=business.id, **payload.model_dump())
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def update_policy(self, policy_id: int, payload: PolicyUpdate) -> Policy | None:
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if policy is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(policy, field, value)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_policy(self, policy_id: int) -> bool:
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if policy is None:
            return False
        self.db.delete(policy)
        self.db.commit()
        return True