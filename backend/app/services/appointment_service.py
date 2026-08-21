import difflib
import re
from datetime import date as date_type
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.knowledge_base import Business, OpeningHour, Service
from app.models.staff import Staff
from app.schemas.appointment import AdminAppointmentUpdate, AppointmentOut
from app.services.time_utils import day_name, is_valid_email, is_valid_phone, parse_date, parse_time

settings = get_settings()


def to_appointment_out(appointment: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
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
        return False  # short tokens (e.g. "men") only match by exact equality,
        # otherwise "men" would wrongly match inside "women"
    return a in b or b in a


class AppointmentPolicyError(ValueError):
    """Raised when a customer-facing action breaks a booking rule."""


class AppointmentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # Lookups

    @staticmethod
    def _resolve_by_name(query: str, options: dict[str, object]) -> object | None:
        """Matches `query` against `options` (lowercase-name -> object) by
        exact match, substring containment, word-overlap, then character
        similarity — so casual/reordered phrasing like "men's hair cut"
        still resolves to "Haircut - Men"."""
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
                    return None  # ambiguous (e.g. "hair cut" alone matches both men's and
                    # women's cuts) — let the caller ask the customer to clarify instead
                    # of silently guessing

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

    def get(self, appointment_id: int) -> Appointment | None:
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()

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
        exclude_appointment_id: int | None = None,
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
        exclude_appointment_id: int | None = None,
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
            "appointment_id": appointment.id,
            "service": service.name,
            "staff": match["staff_name"],
            "date": str(target_date),
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
            "status": "booked",
        }

    # Ownership + policy

    def _verify_owned_booking(self, appointment_id: int, customer_email: str) -> Appointment | dict:
        appointment = self.get(appointment_id)
        if appointment is None:
            return {"error": f"No appointment found with ID {appointment_id}."}
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

    def cancel(self, appointment_id: int, customer_email: str, reason: str | None = None) -> dict:
        result = self._verify_owned_booking(appointment_id, customer_email)
        if isinstance(result, dict):
            return result
        appointment = result

        policy_error = self._check_cancellation_window(appointment)
        if policy_error:
            return {"error": policy_error}

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = reason
        self.db.commit()
        return {"appointment_id": appointment.id, "status": "cancelled"}

    def reschedule(
        self,
        appointment_id: int,
        customer_email: str,
        new_date_str: str,
        new_start_time_str: str,
    ) -> dict:
        result = self._verify_owned_booking(appointment_id, customer_email)
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

        booking_result["rescheduled_from"] = appointment_id
        return booking_result

    def list_for_customer(self, customer_email: str) -> dict:
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
                    "appointment_id": a.id,
                    "service": a.service.name,
                    "staff": a.staff.name,
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
        staff_id: int | None = None,
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

    def admin_update(self, appointment_id: int, payload: AdminAppointmentUpdate) -> Appointment:
        appointment = self.get(appointment_id)
        if appointment is None:
            raise ValueError("Appointment not found.")

        if payload.staff_id is not None:
            appointment.staff_id = payload.staff_id
        if payload.appointment_date is not None:
            appointment.appointment_date = payload.appointment_date
        if payload.start_time is not None:
            appointment.start_time = payload.start_time
            appointment.end_time = (
                datetime.combine(appointment.appointment_date, payload.start_time)
                + timedelta(minutes=appointment.service.duration_minutes)
            ).time()
        if payload.status is not None:
            appointment.status = payload.status
        if payload.notes is not None:
            appointment.notes = payload.notes
        if payload.cancellation_reason is not None:
            appointment.cancellation_reason = payload.cancellation_reason

        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def admin_delete(self, appointment_id: int) -> bool:
        appointment = self.get(appointment_id)
        if appointment is None:
            return False
        self.db.delete(appointment)
        self.db.commit()
        return True