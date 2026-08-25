import json
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.customer import Customer
from app.schemas.chat import ChatResponse, ChatTurn
from app.services.appointment_service import AppointmentService
from app.services.customer_service import CustomerService
from app.services.llm_service import get_llm_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """You are the front-desk assistant for {business_name}, a {business_description}.
Today is {today} ({weekday}). Currency is INR (₹).

{customer_context}

You can hold a natural conversation AND take real actions using the tools provided:
list_services, check_available_slots, book_appointment, reschedule_appointment,
cancel_appointment, check_customer_appointments, get_appointment_by_id,
update_appointment_contact, update_customer_profile, delete_customer_profile, and
answer_business_question.

Rules:
1. Never invent services, staff, prices, hours, slots, appointment IDs, addresses, or ANY
   customer detail (name, email, phone) — always get them from a tool result or from what the
   customer themselves typed in this conversation. If you don't have a piece of information
   from either of those two sources, say so plainly instead of filling the gap with a
   plausible-sounding guess. This applies even to routine-looking details like a location line
   in a booking confirmation — omit it, or fetch it via answer_business_question, never invent it.
2. When confirming a booking or reporting appointment details back to a customer, quote the
   name/email/phone exactly as returned by the tool (book_appointment, get_appointment_by_id,
   etc.) in that same turn — never reuse or restate values from earlier in the conversation from
   memory, and never substitute a different-looking but similar value.
3. answer_business_question and list_services are DIFFERENT sources. General descriptions
   (from answer_business_question) may use broader category names than what's actually
   bookable. The ONLY valid service names for booking are the exact names returned by
   list_services or check_available_slots. If a customer names a service in their own words
   (e.g. "haircut", "hair cut", "a trim"), call list_services first and match it yourself to
   the closest real entry — don't guess variations by trial and error, and don't ask the
   customer to repeat themselves more than once.
4. If check_available_slots or book_appointment returns an error, do not immediately retry
   with a different guess. Read the error (it may include available_services or a message
   explaining why) and either resolve it yourself from that data or ask the customer one
   direct clarifying question.
5. To book an appointment you must have the customer's full name, email, and phone number.
   If the customer's name and/or phone are already known (see above), use them directly and
   don't ask again — just confirm the details before booking as usual. The instant a customer
   states their name and/or phone number anywhere in the conversation, even before booking,
   call update_customer_profile right away to save it — this is the ONLY way it's remembered
   for the rest of the conversation and future visits, so never skip it and never ask for the
   same detail twice in one conversation. Only ask for whatever is genuinely still missing.
6. Before calling book_appointment, always restate the exact service, staff (if chosen), date,
   time, and the customer's name/email/phone in one message and ask them to confirm. Only call
   book_appointment after the customer clearly confirms (e.g. "yes", "confirm", "go ahead").
   The same applies to reschedule_appointment, cancel_appointment, update_appointment_contact,
   update_customer_profile, and delete_customer_profile — confirm the change before calling
   the tool. delete_customer_profile in particular is irreversible; make sure the customer
   understands their appointment history is kept, but their saved profile (name/email/phone)
   will be gone, before calling it.
7. Appointment IDs look like "APT-XXXXXXXX" — always use the exact code the customer gives you
   or a tool returned, never a plain number. When a customer asks about "my appointment(s)" or
   booking details, do NOT dump full details for everything they've ever booked. Ask for the
   specific appointment ID first, then call get_appointment_by_id for that one ID only — it
   returns full details (times, contact info, notes) for exactly that appointment and nothing
   else. If they don't know the ID, use check_customer_appointments to show a short list (ID,
   service, date, status only) so they can pick one — then call get_appointment_by_id for
   whichever one they choose. The same ID + email pattern applies to reschedule, cancel, and
   contact corrections.
8. Changes within {cancellation_window_hours} hours of the appointment are not allowed — if a
   tool reports this, relay it clearly and suggest contacting the business directly. This does
   not apply to update_appointment_contact (correcting a typo isn't a schedule change).
9. For general questions about the business (pricing philosophy, hours, policies, location,
   FAQs), call answer_business_question and answer using only what it returns.
10. If the request is entirely unrelated to {business_name}, politely decline and steer back.

Style:
- Keep replies to about 50-80 words. Be direct and warm, never padded.
- Do not repeat the same stock openers or closers ("I'm sorry", "Thank you", "I'd be happy to")
  turn after turn — vary your phrasing naturally like a real front-desk person would.
- The customer was already identified before this conversation started — never ask for their
  email, never say things like "we already have your email on file", and never re-mention or
  re-confirm it unless they're actively changing it. Treat it as a given, silent fact.
- Never mention "tools", "functions", "context", or other internal system details.
"""

NO_TOOLS_FALLBACK_PROMPT = (
    "You couldn't complete the requested action after several attempts. Based on the "
    "conversation so far, tell the customer plainly what's missing or unclear and ask one "
    "direct question to move forward. Don't apologize more than once and don't repeat "
    "phrasing you've already used in this conversation."
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_services",
            "description": (
                "Get the exact list of bookable services with their real names, prices, and "
                "durations. Call this whenever a customer names a service in casual language "
                "before checking slots or booking, to find the matching exact name — general "
                "business descriptions may use different wording than the bookable catalog."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_available_slots",
            "description": "Find open appointment slots for a service on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "staff_name": {"type": "string", "description": "Optional preferred staff member"},
                },
                "required": ["service_name", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment. Requires an exact slot returned by check_available_slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "start_time": {"type": "string", "description": "HH:MM, 24-hour"},
                    "customer_name": {"type": "string"},
                    "customer_email": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "staff_name": {"type": "string", "description": "Optional preferred staff member"},
                },
                "required": [
                    "service_name", "date", "start_time",
                    "customer_name", "customer_email", "customer_phone",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Move an existing booked appointment to a new date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment's reference code, e.g. APT-7K4M9QRT",
                    },
                    "customer_email": {"type": "string"},
                    "new_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "new_start_time": {"type": "string", "description": "HH:MM, 24-hour"},
                },
                "required": ["appointment_id", "customer_email", "new_date", "new_start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing booked appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment's reference code, e.g. APT-7K4M9QRT",
                    },
                    "customer_email": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["appointment_id", "customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_customer_appointments",
            "description": (
                "Get a short index of a customer's appointments by email — ID, service, date, "
                "and status only, NOT full contact/time details. Use this only to help a "
                "customer find an appointment ID they don't remember, then follow up with "
                "get_appointment_by_id for the one they actually want details on."
            ),
            "parameters": {
                "type": "object",
                "properties": {"customer_email": {"type": "string"}},
                "required": ["customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_appointment_by_id",
            "description": (
                "Look up ONE specific appointment by its reference code, verified against the "
                "email it was booked under. Returns only that appointment — never any other "
                "booking on the account, even if the email matches more than one. Use this "
                "when the customer already has a specific appointment ID and wants its status "
                "or details, rather than a list of everything they've booked."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment's reference code, e.g. APT-7K4M9QRT",
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "The email to verify against this appointment",
                    },
                },
                "required": ["appointment_id", "customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment_contact",
            "description": (
                "Correct the name, email, or phone number on an existing booked appointment. "
                "Requires the appointment ID and the email it's currently booked under, to "
                "verify ownership — same as cancel/reschedule."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment's reference code, e.g. APT-7K4M9QRT",
                    },
                    "customer_email": {"type": "string", "description": "The current email on the booking"},
                    "new_name": {"type": "string"},
                    "new_email": {"type": "string"},
                    "new_phone": {"type": "string"},
                },
                "required": ["appointment_id", "customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_customer_profile",
            "description": (
                "Update the customer's own saved profile (name, email, and/or phone) — the "
                "long-term details remembered across future visits so they don't have to be "
                "re-entered every time. This is the account profile, not any one appointment's "
                "contact info. Only pass the fields that are changing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "new_name": {"type": "string"},
                    "new_email": {"type": "string"},
                    "new_phone": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_customer_profile",
            "description": (
                "Permanently delete the customer's saved profile (name, email, phone) from our "
                "records, at their request. Their appointment history is kept regardless — this "
                "only removes the remembered profile used to skip re-entering details next time. "
                "Only call this after the customer has explicitly confirmed."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_business_question",
            "description": (
                "Look up information about the business itself — services, pricing, "
                "hours, policies, location, FAQs. Use this for anything not about a "
                "specific booking action."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]


class AgentService:
    def __init__(
        self, db: Session, browser_id: str | None = None, customer: Customer | None = None
    ) -> None:
        self.db = db
        self.appointments = AppointmentService(db)
        self.customers = CustomerService(db)
        self.vector_store = get_vector_store()
        self.llm = get_llm_service()
        self.browser_id = browser_id
        self.customer = customer

    def _save_kyc_from_booking(self, args: dict) -> None:
        """After a successful booking, fill in whatever the customer's long-term
        profile is still missing (name/phone) so future sessions don't need to
        ask again. Only ever writes to the currently-identified customer, and
        only if the booking's email matches theirs."""
        customer = self.customer
        if customer is None:
            return
        booking_email = (args.get("customer_email") or "").strip().lower()
        if booking_email != customer.email:
            return

        changed = False
        if not customer.name and args.get("customer_name"):
            customer.name = args["customer_name"].strip()
            changed = True
        if not customer.phone and args.get("customer_phone"):
            customer.phone = args["customer_phone"].strip()
            changed = True
        if changed:
            self.db.commit()

    def _dispatch(self, name: str, args: dict) -> dict:
        try:
            if name == "list_services":
                return self.appointments.list_services()
            if name == "check_available_slots":
                return self.appointments.find_available_slots(
                    args["service_name"], args["date"], args.get("staff_name")
                )
            if name == "book_appointment":
                result = self.appointments.book(
                    service_name=args["service_name"],
                    date_str=args["date"],
                    start_time_str=args["start_time"],
                    customer_name=args["customer_name"],
                    customer_email=args["customer_email"],
                    customer_phone=args["customer_phone"],
                    staff_name=args.get("staff_name"),
                )
                if "error" not in result:
                    self._save_kyc_from_booking(args)
                return result
            if name == "reschedule_appointment":
                return self.appointments.reschedule(
                    reference_code=str(args["appointment_id"]),
                    customer_email=args["customer_email"],
                    new_date_str=args["new_date"],
                    new_start_time_str=args["new_start_time"],
                )
            if name == "cancel_appointment":
                return self.appointments.cancel(
                    reference_code=str(args["appointment_id"]),
                    customer_email=args["customer_email"],
                    reason=args.get("reason"),
                )
            if name == "check_customer_appointments":
                return self.appointments.list_for_customer(args["customer_email"])
            if name == "get_appointment_by_id":
                return self.appointments.get_details_for_customer(
                    reference_code=str(args["appointment_id"]),
                    customer_email=args["customer_email"],
                )
            if name == "update_appointment_contact":
                return self.appointments.update_contact(
                    reference_code=str(args["appointment_id"]),
                    customer_email=args["customer_email"],
                    new_name=args.get("new_name"),
                    new_email=args.get("new_email"),
                    new_phone=args.get("new_phone"),
                )
            if name == "update_customer_profile":
                if self.customer is None or self.browser_id is None:
                    return {"error": "I don't have a verified profile for this conversation yet."}
                result = self.customers.update_profile(
                    email=self.customer.email,
                    browser_id=self.browser_id,
                    new_name=args.get("new_name"),
                    new_email=args.get("new_email"),
                    new_phone=args.get("new_phone"),
                )
                if "error" not in result:
                    self.customer = self.customers.get_by_email(result["customer"]["email"])
                return result
            if name == "delete_customer_profile":
                if self.customer is None or self.browser_id is None:
                    return {"error": "I don't have a verified profile for this conversation yet."}
                result = self.customers.delete_profile(email=self.customer.email, browser_id=self.browser_id)
                if "error" not in result:
                    self.customer = None
                return result
            if name == "answer_business_question":
                hits = self.vector_store.search(args["question"])
                if not hits:
                    return {"context": "No matching information found in the knowledge base."}
                return {"context": "\n\n".join(h["text"] for h in hits)}
            return {"error": f"Unknown tool '{name}'."}
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Tool '%s' failed with args %s: %s", name, args, exc)
            return {"error": f"Couldn't complete that — {exc}"}

    def _customer_context(self) -> str:
        if self.customer is None:
            return ""
        parts = [f"email is {self.customer.email}"]
        if self.customer.name:
            parts.append(f"name is {self.customer.name}")
        if self.customer.phone:
            parts.append(f"phone is {self.customer.phone}")
        known = ", ".join(parts)
        if self.customer.name and self.customer.phone:
            return (
                f"You already know this customer: {known}. Use these details directly for "
                "booking or account actions without asking again, unless they explicitly want "
                "to change something via update_customer_profile."
            )
        return (
            f"You know this much about this customer so far: {known}. Whatever's missing "
            "(name and/or phone) hasn't been collected yet — get it naturally when they book "
            "their first appointment, then it will be remembered for next time."
        )

    def _build_messages(self, question: str, history: list[ChatTurn]) -> list[dict]:
        today = date.today()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            business_name=settings.business_name,
            business_description=settings.business_description,
            today=today.isoformat(),
            weekday=today.strftime("%A"),
            cancellation_window_hours=settings.cancellation_window_hours,
            customer_context=self._customer_context(),
        )
        max_messages = settings.max_history_exchanges * 2
        trimmed_history = history[-max_messages:] if history else []

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend({"role": turn.role, "content": turn.content} for turn in trimmed_history)
        messages.append({"role": "user", "content": question})
        return messages

    def answer(
        self, question: str, session_id: str | None = None, history: list[ChatTurn] | None = None
    ) -> ChatResponse:
        messages = self._build_messages(question, history or [])

        for _ in range(settings.max_tool_iterations):
            message = self.llm.chat(messages, tools=TOOL_SCHEMAS)

            if not message.tool_calls:
                return ChatResponse(answer=message.content, sources=[], session_id=session_id)

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.function.name, "arguments": call.function.arguments},
                        }
                        for call in message.tool_calls
                    ],
                }
            )

            for call in message.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._dispatch(call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return ChatResponse(
            answer=self._final_fallback_reply(messages),
            sources=[],
            session_id=session_id,
        )

    def _final_fallback_reply(self, messages: list[dict]) -> str:
        messages = messages + [{"role": "user", "content": NO_TOOLS_FALLBACK_PROMPT}]
        try:
            final = self.llm.chat(messages, tools=None)
            if final.content:
                return final.content
        except Exception:  # noqa: BLE001 - best-effort fallback, never raise here
            logger.exception("Fallback reply generation failed")
        return "Let's take that one step at a time — could you tell me what you'd like to do next?"