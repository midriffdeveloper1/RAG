from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.models.customer import Customer
from app.services.time_utils import is_valid_email, is_valid_phone


def _serialize(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "email": customer.email,
        "name": customer.name,
        "phone": customer.phone,
    }


class CustomerService:

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    def get_by_email(self, email: str) -> Customer | None:
        return self.db.query(Customer).filter(Customer.email == self._normalize_email(email)).first()

    def identify(self, email: str) -> dict:
        
        if not is_valid_email(email):
            return {"error": "That email address doesn't look valid."}

        normalized = self._normalize_email(email)
        customer = self.get_by_email(normalized)
        is_returning = customer is not None

        if customer is None:
            customer = Customer(email=normalized)
            self.db.add(customer)
            self.db.flush()

        self.db.commit()
        self.db.refresh(customer)

        return {"is_returning": is_returning, "customer": _serialize(customer)}

    def _authorize(self, email: str, browser_id: str) -> Customer | dict:
        customer = self.get_by_email(email)
        if customer is None:
            return {"error": "No profile found for that email."}

        linked_session = (
            self.db.query(ChatSession)
            .filter(ChatSession.browser_id == browser_id, ChatSession.customer_id == customer.id)
            .first()
        )
        if linked_session is None:
            return {"error": "This browser session isn't verified for that email yet."}
        return customer

    def update_profile(
        self,
        email: str,
        browser_id: str,
        new_name: str | None = None,
        new_email: str | None = None,
        new_phone: str | None = None,
    ) -> dict:
        result = self._authorize(email, browser_id)
        if isinstance(result, dict):
            return result
        customer = result

        if new_email is not None and not is_valid_email(new_email):
            return {"error": "That email address doesn't look valid."}
        if new_phone is not None and not is_valid_phone(new_phone):
            return {"error": "That phone number doesn't look valid."}
        if not any([new_name, new_email, new_phone]):
            return {"error": "Nothing to update — provide a new name, email, or phone."}

        if new_email:
            normalized = self._normalize_email(new_email)
            existing = self.get_by_email(normalized)
            if existing is not None and existing.id != customer.id:
                return {"error": "Another profile already uses that email."}
            customer.email = normalized
        if new_name:
            customer.name = new_name.strip()
        if new_phone:
            customer.phone = new_phone.strip()

        self.db.commit()
        self.db.refresh(customer)
        return {"status": "updated", "customer": _serialize(customer)}

    def delete_profile(self, email: str, browser_id: str) -> dict:
        result = self._authorize(email, browser_id)
        if isinstance(result, dict):
            return result
        customer = result

        self.db.query(ChatSession).filter(ChatSession.customer_id == customer.id).update(
            {ChatSession.customer_id: None}, synchronize_session=False
        )
        self.db.delete(customer)
        self.db.commit()
        return {"status": "deleted"}

    

    def admin_list_paginated(
        self, page: int = 1, page_size: int = 10, search: str | None = None
    ) -> tuple[list[Customer], int]:
        query = self.db.query(Customer)
        if search:
            like = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(func.lower(Customer.email).like(like), func.lower(Customer.name).like(like))
            )
        query = query.order_by(Customer.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def admin_create(self, email: str, name: str | None = None, phone: str | None = None) -> Customer:
        if not is_valid_email(email):
            raise ValueError("That email address doesn't look valid.")
        normalized = self._normalize_email(email)
        if self.get_by_email(normalized) is not None:
            raise ValueError("A customer with that email already exists.")
        if phone and not is_valid_phone(phone):
            raise ValueError("That phone number doesn't look valid.")

        customer = Customer(email=normalized, name=(name or None), phone=(phone or None))
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def admin_update(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
        phone: str | None = None,
    ) -> Customer:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None:
            raise LookupError("Customer not found.")

        if email is not None:
            if not is_valid_email(email):
                raise ValueError("That email address doesn't look valid.")
            normalized = self._normalize_email(email)
            existing = self.get_by_email(normalized)
            if existing is not None and existing.id != customer.id:
                raise ValueError("Another customer already uses that email.")
            customer.email = normalized
        if name is not None:
            customer.name = name.strip() or None
        if phone is not None:
            if phone and not is_valid_phone(phone):
                raise ValueError("That phone number doesn't look valid.")
            customer.phone = phone.strip() or None

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def admin_delete(self, customer_id: str) -> bool:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None:
            return False
        self.db.query(ChatSession).filter(ChatSession.customer_id == customer.id).update(
            {ChatSession.customer_id: None}, synchronize_session=False
        )
        self.db.delete(customer)
        self.db.commit()
        return True