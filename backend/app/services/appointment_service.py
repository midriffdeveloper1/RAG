import difflib
import re
import secrets
from datetime import date as date_type
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.knowledge_base import Business, OpeningHour, Service
from app.models.staff import Staff
from app.schemas.appointment import AdminAppointmentCreate, AdminAppointmentUpdate, AppointmentOut
from app.services.time_utils import day_name, is_valid_email, is_valid_phone, parse_date, parse_time

settings = get_settings()

_REFERENCE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_REFERENCE_LENGTH = 8


def generate_reference_code() -> str:
    return "APT-" + "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(_REFERENCE_LENGTH))


def to_appointment_out(appointment: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
        reference_code=appointment.reference_code,
        service_id=appointment.service_id,
        service_name=appointment.service.name,
        staff_id=appointment.staff_id,
        staff_name=appointment.staff.name,
        customer_name=appointment.customer_name,
        customer_email=appointment.customer_email,
        customer_phone=appointment.customer_phone,
        appointment_date=appointment.appointment_date,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        status=appointment.status,
        notes=appointment.notes,
        cancellation_reason=appointment.cancellation_reason,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


_FILLER_WORDS = {"service", "services", "please", "appointment", "for", "the", "a", "an"}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stemmed = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words]
    return [w for w in stemmed if len(w) >= 3 and w not in _FILLER_WORDS]


def _tokens_overlap(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) < 4 or len(b) < 4:
        return False  
    return a in b or b in a


class AppointmentPolicyError(ValueError):
    """Raised when a customer-facing action breaks a booking rule."""


class AppointmentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # Lookups

    @staticmethod
    def _resolve_by_name(query: str, options: dict[str, object]) -> object | None:
        
        cleaned = query.strip().lower()
        if not cleaned or not options:
            return None
        if cleaned in options:
            return options[cleaned]

        contains = [name for name in options if cleaned in name or name in cleaned]
        if len(contains) == 1:
            return options[contains[0]]

        query_tokens = _tokens(query)
        if query_tokens:
            scores: dict[str, float] = {}
            for name in options:
                name_tokens = _tokens(name)
                if not name_tokens:
                    continue
                matched = sum(
                    1 for qt in query_tokens if any(_tokens_overlap(qt, nt) for nt in name_tokens)
                )
                scores[name] = matched / len(query_tokens)
            if scores:
                best_score = max(scores.values())
                if best_score >= 0.6:
                    top = [name for name, score in scores.items() if score == best_score]
                    if len(top) == 1:
                        return options[top[0]]
                    return None  

        close = difflib.get_close_matches(cleaned, options.keys(), n=1, cutoff=0.6)
        if close:
            return options[close[0]]
        return None

    def _get_service(self, name: str) -> Service | None:
        services = self.db.query(Service).all()
        return self._resolve_by_name(name, {s.name.lower(): s for s in services})

    def _get_staff(self, name: str) -> Staff | None:
        staff = self.db.query(Staff).filter(Staff.is_active.is_(True)).all()
        return self._resolve_by_name(name, {s.name.lower(): s for s in staff})

    def list_services(self) -> dict:
        services = self.db.query(Service).order_by(Service.name).all()
        return {
            "services": [
                {
                    "name": s.name,
                    "description": s.description,
                    "price": s.price,
                    "duration_minutes": s.duration_minutes,
                }
                for s in services
            ]
        }

    def get(self, appointment_id: str) -> Appointment | None:
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()

    def get_by_reference(self, reference_code: str) -> Appointment | None:
        return (
            self.db.query(Appointment)
            .filter(Appointment.reference_code == reference_code.strip().upper())
            .first()
        )

    def _generate_unique_reference_code(self) -> str:
        for _ in range(10):
            code = generate_reference_code()
            exists = self.db.query(Appointment.id).filter(Appointment.reference_code == code).first()
            if exists is None:
                return code
        raise RuntimeError("Could not generate a unique appointment reference code.")

    def _validate_window(self, target_date: date_type) -> str | None:
        today = date_type.today()
        if target_date < today:
            return "That date has already passed."
        if (target_date - today).days > settings.booking_window_days:
            return f"We only take bookings up to {settings.booking_window_days} days in advance."
        return None

    # Slot search

    def find_available_slots(
        self,
        service_name: str,
        date_str: str,
        staff_name: str | None = None,
        exclude_appointment_id: str | None = None,
    ) -> dict:
        service = self._get_service(service_name)
        if service is None:
            return {
                "error": f"We don't have a service called '{service_name}'.",
                "available_services": [s.name for s in self.db.query(Service).order_by(Service.name).all()],
            }

        try:
            target_date = parse_date(date_str)
        except ValueError as exc:
            return {"error": str(exc)}

        window_error = self._validate_window(target_date)
        if window_error:
            return {"error": window_error}

        business = self.db.query(Business).first()
        opening = (
            self.db.query(OpeningHour)
            .filter(
                OpeningHour.business_id == business.id,
                OpeningHour.day_of_week == day_name(target_date),
            )
            .first()
        )
        if opening is None or opening.is_closed or not opening.open_time:
            return {"slots": [], "message": f"We're closed on {day_name(target_date)}s."}

        from app.services.holiday_service import HolidayService

        closure = HolidayService(self.db).get_closure_for_date(business.id, target_date)
        closed_start = closed_end = None
        if closure is not None:
            if closure.is_full_day:
                reason = f" — {closure.note}" if closure.note else ""
                return {"slots": [], "message": f"We're closed on {target_date}{reason}."}
            closed_start = parse_time(closure.start_time)
            closed_end = parse_time(closure.end_time)

        qualified_staff = [s for s in service.staff if s.is_active]
        if staff_name:
            staff = self._get_staff(staff_name)
            if staff is None:
                return {"error": f"No staff member named '{staff_name}'."}
            if staff not in qualified_staff:
                return {"error": f"{staff.name} doesn't perform {service.name}."}
            qualified_staff = [staff]

        if not qualified_staff:
            return {"error": f"No staff are currently assigned to {service.name}."}

        open_t = parse_time(opening.open_time)
        close_t = parse_time(opening.close_time)
        duration = service.duration_minutes
        step = timedelta(minutes=settings.slot_step_minutes)
        now = datetime.now()

        slots: list[dict] = []
        for staff in qualified_staff:
            busy_query = self.db.query(Appointment).filter(
                Appointment.staff_id == staff.id,
                Appointment.appointment_date == target_date,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            if exclude_appointment_id is not None:
                busy_query = busy_query.filter(Appointment.id != exclude_appointment_id)
            busy_ranges = [(b.start_time, b.end_time) for b in busy_query.all()]
            if closed_start is not None and closed_end is not None:
                busy_ranges.append((closed_start, closed_end))

            cursor = datetime.combine(target_date, open_t)
            day_end = datetime.combine(target_date, close_t)
            while cursor + timedelta(minutes=duration) <= day_end:
                if target_date == now.date() and cursor <= now:
                    cursor += step
                    continue

                slot_start = cursor.time()
                slot_end = (cursor + timedelta(minutes=duration)).time()
                overlaps = any(
                    slot_start < b_end and b_start < slot_end for b_start, b_end in busy_ranges
                )
                if not overlaps:
                    slots.append(
                        {
                            "start_time": slot_start.strftime("%H:%M"),
                            "end_time": slot_end.strftime("%H:%M"),
                            "staff_id": staff.id,
                            "staff_name": staff.name,
                        }
                    )
                cursor += step

        slots.sort(key=lambda s: s["start_time"])
        return {
            "service": service.name,
            "duration_minutes": duration,
            "date": str(target_date),
            "slots": slots[:12],
        }

    # Booking

    def book(
        self,
        service_name: str,
        date_str: str,
        start_time_str: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        staff_name: str | None = None,
        exclude_appointment_id: str | None = None,
    ) -> dict:
        if not customer_name or not customer_name.strip():
            return {"error": "Customer name is required to book."}
        if not is_valid_email(customer_email):
            return {"error": "That email address doesn't look valid."}
        if not is_valid_phone(customer_phone):
            return {"error": "That phone number doesn't look valid."}

        service = self._get_service(service_name)
        if service is None:
            return {
                "error": f"We don't have a service called '{service_name}'.",
                "available_services": [s.name for s in self.db.query(Service).order_by(Service.name).all()],
            }

        try:
            target_date = parse_date(date_str)
            start_time = parse_time(start_time_str)
        except ValueError as exc:
            return {"error": str(exc)}

        
        existing = (
            self.db.query(Appointment)
            .filter(
                Appointment.service_id == service.id,
                Appointment.customer_email == customer_email.strip().lower(),
                Appointment.appointment_date == target_date,
                Appointment.start_time == start_time,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            .first()
        )
        if existing is not None:
            staff = self.db.query(Staff).filter(Staff.id == existing.staff_id).first()
            return {
                "appointment_id": existing.reference_code,
                "service": service.name,
                "staff": staff.name if staff else None,
                "date": str(existing.appointment_date),
                "start_time": existing.start_time.strftime("%H:%M"),
                "end_time": existing.end_time.strftime("%H:%M"),
                "status": "booked",
                "already_booked": True,
            }

        window_error = self._validate_window(target_date)
        if window_error:
            return {"error": window_error}

        available = self.find_available_slots(
            service_name, date_str, staff_name, exclude_appointment_id=exclude_appointment_id
        )
        if "error" in available:
            return available

        match = next(
            (s for s in available["slots"] if s["start_time"] == start_time.strftime("%H:%M")),
            None,
        )
        if match is None:
            return {"error": "That slot isn't available anymore. Please pick another time."}

        end_time = (
            datetime.combine(target_date, start_time) + timedelta(minutes=service.duration_minutes)
        ).time()

        appointment = Appointment(
            reference_code=self._generate_unique_reference_code(),
            service_id=service.id,
            staff_id=match["staff_id"],
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip().lower(),
            customer_phone=customer_phone.strip(),
            appointment_date=target_date,
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.BOOKED,
        )
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)

        return {
            "appointment_id": appointment.reference_code,
            "service": service.name,
            "staff": match["staff_name"],
            "date": str(target_date),
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
            "status": "booked",
        }

    # Ownership + policy

    def _verify_owned_booking(self, reference_code: str, customer_email: str) -> Appointment | dict:
        appointment = self.get_by_reference(reference_code)
        if appointment is None:
            return {"error": f"No appointment found with ID {reference_code}."}
        if appointment.customer_email.lower() != customer_email.strip().lower():
            return {"error": "That email doesn't match this appointment's records."}
        if appointment.status != AppointmentStatus.BOOKED:
            return {"error": f"This appointment is already {appointment.status.value}."}
        return appointment

    def _check_cancellation_window(self, appointment: Appointment) -> str | None:
        appointment_dt = datetime.combine(appointment.appointment_date, appointment.start_time)
        if appointment_dt - datetime.now() < timedelta(hours=settings.cancellation_window_hours):
            return (
                f"Changes aren't allowed within {settings.cancellation_window_hours} hours "
                "of the appointment. Please contact us directly for urgent changes."
            )
        return None

    def cancel(self, reference_code: str, customer_email: str, reason: str | None = None) -> dict:
        result = self._verify_owned_booking(reference_code, customer_email)
        if isinstance(result, dict):
            return result
        appointment = result

        policy_error = self._check_cancellation_window(appointment)
        if policy_error:
            return {"error": policy_error}

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = reason
        self.db.commit()
        return {"appointment_id": appointment.reference_code, "status": "cancelled"}

    def update_contact(
        self,
        reference_code: str,
        customer_email: str,
        new_name: str | None = None,
        new_email: str | None = None,
        new_phone: str | None = None,
    ) -> dict:
        result = self._verify_owned_booking(reference_code, customer_email)
        if isinstance(result, dict):
            return result
        appointment = result

        if new_email is not None and not is_valid_email(new_email):
            return {"error": "That email address doesn't look valid."}
        if new_phone is not None and not is_valid_phone(new_phone):
            return {"error": "That phone number doesn't look valid."}
        if not any([new_name, new_email, new_phone]):
            return {"error": "Nothing to update — provide a new name, email, or phone."}

        if new_name:
            appointment.customer_name = new_name.strip()
        if new_email:
            appointment.customer_email = new_email.strip().lower()
        if new_phone:
            appointment.customer_phone = new_phone.strip()

        self.db.commit()
        return {
            "appointment_id": appointment.reference_code,
            "customer_name": appointment.customer_name,
            "customer_email": appointment.customer_email,
            "customer_phone": appointment.customer_phone,
            "status": "updated",
        }

    def reschedule(
        self,
        reference_code: str,
        customer_email: str,
        new_date_str: str,
        new_start_time_str: str,
    ) -> dict:
        result = self._verify_owned_booking(reference_code, customer_email)
        if isinstance(result, dict):
            return result
        appointment = result

        policy_error = self._check_cancellation_window(appointment)
        if policy_error:
            return {"error": policy_error}

        service = appointment.service
        staff = appointment.staff

        booking_result = self.book(
            service_name=service.name,
            date_str=new_date_str,
            start_time_str=new_start_time_str,
            customer_name=appointment.customer_name,
            customer_email=appointment.customer_email,
            customer_phone=appointment.customer_phone,
            staff_name=staff.name,
            exclude_appointment_id=appointment.id,
        )
        if "error" in booking_result:
            return booking_result

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = "Rescheduled by customer"
        self.db.commit()

        booking_result["rescheduled_from"] = appointment.reference_code
        return booking_result

    def get_details_for_customer(self, reference_code: str, customer_email: str) -> dict:
        """Look up a single appointment by its public reference code, but only ever
        return it if the given email matches the appointment's own record. Never
        distinguishes "wrong ID" from "wrong email" in the error, so a guess can't be
        used to probe whether a given reference code exists."""
        if not is_valid_email(customer_email):
            return {"error": "That email address doesn't look valid."}

        appointment = self.get_by_reference(reference_code)
        if appointment is None or appointment.customer_email.lower() != customer_email.strip().lower():
            return {"error": "No appointment found with that ID and email combination."}

        return {
            "appointment_id": appointment.reference_code,
            "service": appointment.service.name,
            "staff": appointment.staff.name,
            "date": str(appointment.appointment_date),
            "start_time": appointment.start_time.strftime("%H:%M"),
            "end_time": appointment.end_time.strftime("%H:%M"),
            "status": appointment.status.value,
            "customer_name": appointment.customer_name,
            "customer_email": appointment.customer_email,
            "customer_phone": appointment.customer_phone,
            "notes": appointment.notes,
            "cancellation_reason": appointment.cancellation_reason,
        }

    def list_for_customer(self, customer_email: str) -> dict:
        """A short index only — ID, service, date, status. Deliberately does NOT
        repeat the customer's own name/email/phone on every row (they already
        know it, and it's not needed to pick which appointment they mean).
        Full details for one specific appointment come from
        get_details_for_customer() instead."""
        if not is_valid_email(customer_email):
            return {"error": "That email address doesn't look valid."}

        appointments = (
            self.db.query(Appointment)
            .filter(func.lower(Appointment.customer_email) == customer_email.strip().lower())
            .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
            .limit(20)
            .all()
        )
        return {
            "appointments": [
                {
                    "appointment_id": a.reference_code,
                    "service": a.service.name,
                    "date": str(a.appointment_date),
                    "start_time": a.start_time.strftime("%H:%M"),
                    "status": a.status.value,
                }
                for a in appointments
            ]
        }

    # Admin CRUD — not bound by the 24-hour customer policy

    def admin_list(
        self,
        status: AppointmentStatus | None = None,
        staff_id: str | None = None,
        customer_email: str | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
    ) -> list[Appointment]:
        query = self.db.query(Appointment)
        if status is not None:
            query = query.filter(Appointment.status == status)
        if staff_id is not None:
            query = query.filter(Appointment.staff_id == staff_id)
        if customer_email:
            query = query.filter(func.lower(Appointment.customer_email) == customer_email.lower())
        if date_from is not None:
            query = query.filter(Appointment.appointment_date >= date_from)
        if date_to is not None:
            query = query.filter(Appointment.appointment_date <= date_to)
        return query.order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()

    def admin_list_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        status: AppointmentStatus | None = None,
        staff_id: str | None = None,
        customer_email: str | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
    ) -> tuple[list[Appointment], int]:
        query = self.db.query(Appointment)
        if status is not None:
            query = query.filter(Appointment.status == status)
        if staff_id is not None:
            query = query.filter(Appointment.staff_id == staff_id)
        if customer_email:
            query = query.filter(func.lower(Appointment.customer_email) == customer_email.lower())
        if date_from is not None:
            query = query.filter(Appointment.appointment_date >= date_from)
        if date_to is not None:
            query = query.filter(Appointment.appointment_date <= date_to)

        query = query.order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def admin_update(self, appointment_id: str, payload: AdminAppointmentUpdate) -> Appointment:
        appointment = self.get(appointment_id)
        if appointment is None:
            raise ValueError("Appointment not found.")

        if payload.service_id is not None:
            service = self.db.query(Service).filter(Service.id == payload.service_id).first()
            if service is None:
                raise ValueError("Service not found.")
            appointment.service_id = service.id
        if payload.staff_id is not None:
            appointment.staff_id = payload.staff_id
        if payload.appointment_date is not None:
            appointment.appointment_date = payload.appointment_date
        if payload.start_time is not None:
            appointment.start_time = payload.start_time
        if payload.start_time is not None or payload.service_id is not None:
            duration = appointment.service.duration_minutes
            if duration is None:
                raise ValueError(
                    f"{appointment.service.name} doesn't have a duration set yet — "
                    "add one on the Services page first."
                )
            appointment.end_time = (
                datetime.combine(appointment.appointment_date, appointment.start_time)
                + timedelta(minutes=duration)
            ).time()
        if payload.status is not None:
            appointment.status = payload.status
        if payload.notes is not None:
            appointment.notes = payload.notes
        if payload.cancellation_reason is not None:
            appointment.cancellation_reason = payload.cancellation_reason
        if payload.customer_name is not None:
            appointment.customer_name = payload.customer_name
        if payload.customer_email is not None:
            appointment.customer_email = payload.customer_email.strip().lower()
        if payload.customer_phone is not None:
            appointment.customer_phone = payload.customer_phone

        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def admin_create(self, payload: AdminAppointmentCreate) -> Appointment:
        service = self.db.query(Service).filter(Service.id == payload.service_id).first()
        if service is None:
            raise ValueError("Service not found.")
        if service.duration_minutes is None:
            raise ValueError(
                f"{service.name} doesn't have a duration set yet — add one on the Services page first."
            )
        staff = self.db.query(Staff).filter(Staff.id == payload.staff_id).first()
        if staff is None:
            raise ValueError("Staff member not found.")
        if not is_valid_email(payload.customer_email):
            raise ValueError("That email address doesn't look valid.")
        if not is_valid_phone(payload.customer_phone):
            raise ValueError("That phone number doesn't look valid.")

        end_time = (
            datetime.combine(payload.appointment_date, payload.start_time)
            + timedelta(minutes=service.duration_minutes)
        ).time()

        conflict = (
            self.db.query(Appointment)
            .filter(
                Appointment.staff_id == staff.id,
                Appointment.appointment_date == payload.appointment_date,
                Appointment.status == AppointmentStatus.BOOKED,
                Appointment.start_time < end_time,
                Appointment.end_time > payload.start_time,
            )
            .first()
        )
        if conflict is not None:
            raise ValueError(f"{staff.name} already has an overlapping appointment at that time.")

        appointment = Appointment(
            reference_code=self._generate_unique_reference_code(),
            service_id=service.id,
            staff_id=staff.id,
            customer_name=payload.customer_name.strip(),
            customer_email=payload.customer_email.strip().lower(),
            customer_phone=payload.customer_phone.strip(),
            appointment_date=payload.appointment_date,
            start_time=payload.start_time,
            end_time=end_time,
            status=AppointmentStatus.BOOKED,
            notes=payload.notes,
        )
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def admin_delete(self, appointment_id: str) -> bool:
        appointment = self.get(appointment_id)
        if appointment is None:
            return False
        self.db.delete(appointment)
        self.db.commit()
        return True