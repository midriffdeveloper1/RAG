import json
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.chat import ChatResponse, ChatTurn
from app.services.appointment_service import AppointmentService
from app.services.llm_service import get_llm_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """You are the front-desk assistant for {business_name}, a {business_description}.
Today is {today} ({weekday}). Currency is INR (₹).

You can hold a natural conversation AND take real actions using the tools provided:
list_services, check_available_slots, book_appointment, reschedule_appointment,
cancel_appointment, check_customer_appointments, update_appointment_contact, and
answer_business_question.

Rules:
1. Never invent services, staff, prices, hours, slots, appointment IDs, addresses, or ANY
   customer detail (name, email, phone) — always get them from a tool result or from what the
   customer themselves typed in this conversation. If you don't have a piece of information
   from either of those two sources, say so plainly instead of filling the gap with a
   plausible-sounding guess. This applies even to routine-looking details like a location line
   in a booking confirmation — omit it, or fetch it via answer_business_question, never invent it.
2. When confirming a booking or reporting appointment details back to a customer, quote the
   name/email/phone exactly as returned by the tool (book_appointment, check_customer_appointments,
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
   Ask for whatever is missing, one or two things at a time — don't demand all of it up front
   if the customer hasn't chosen a service and time yet.
6. Before calling book_appointment, always restate the exact service, staff (if chosen), date,
   time, and the customer's name/email/phone in one message and ask them to confirm. Only call
   book_appointment after the customer clearly confirms (e.g. "yes", "confirm", "go ahead").
   The same applies to reschedule_appointment, cancel_appointment, and
   update_appointment_contact — confirm the change before calling the tool.
7. To cancel, reschedule, check details, or correct contact info, you need the appointment ID
   and the email it was booked under, to
   confirm it belongs to them. If they don't know the ID, use check_customer_appointments first.
7. Changes within {cancellation_window_hours} hours of the appointment are not allowed — if a
   tool reports this, relay it clearly and suggest contacting the business directly. This does
   not apply to update_appointment_contact (correcting a typo isn't a schedule change).
8. For general questions about the business (pricing philosophy, hours, policies, location,
   FAQs), call answer_business_question and answer using only what it returns.
9. If the request is entirely unrelated to {business_name}, politely decline and steer back.

Style:
- Keep replies to about 50-80 words. Be direct and warm, never padded.
- Do not repeat the same stock openers or closers ("I'm sorry", "Thank you", "I'd be happy to")
  turn after turn — vary your phrasing naturally like a real front-desk person would.
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
                    "appointment_id": {"type": "integer"},
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
                    "appointment_id": {"type": "integer"},
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
                "List a customer's appointments by their email address, including the exact "
                "name/email/phone on file for each. Use this whenever a customer asks about "
                "their own booking details — never guess or restate contact info from memory."
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
            "name": "update_appointment_contact",
            "description": (
                "Correct the name, email, or phone number on an existing booked appointment. "
                "Requires the appointment ID and the email it's currently booked under, to "
                "verify ownership — same as cancel/reschedule."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "integer"},
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
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentService(db)
        self.vector_store = get_vector_store()
        self.llm = get_llm_service()

    def _dispatch(self, name: str, args: dict) -> dict:
        try:
            if name == "list_services":
                return self.appointments.list_services()
            if name == "check_available_slots":
                return self.appointments.find_available_slots(
                    args["service_name"], args["date"], args.get("staff_name")
                )
            if name == "book_appointment":
                return self.appointments.book(
                    service_name=args["service_name"],
                    date_str=args["date"],
                    start_time_str=args["start_time"],
                    customer_name=args["customer_name"],
                    customer_email=args["customer_email"],
                    customer_phone=args["customer_phone"],
                    staff_name=args.get("staff_name"),
                )
            if name == "reschedule_appointment":
                return self.appointments.reschedule(
                    appointment_id=int(args["appointment_id"]),
                    customer_email=args["customer_email"],
                    new_date_str=args["new_date"],
                    new_start_time_str=args["new_start_time"],
                )
            if name == "cancel_appointment":
                return self.appointments.cancel(
                    appointment_id=int(args["appointment_id"]),
                    customer_email=args["customer_email"],
                    reason=args.get("reason"),
                )
            if name == "check_customer_appointments":
                return self.appointments.list_for_customer(args["customer_email"])
            if name == "update_appointment_contact":
                return self.appointments.update_contact(
                    appointment_id=int(args["appointment_id"]),
                    customer_email=args["customer_email"],
                    new_name=args.get("new_name"),
                    new_email=args.get("new_email"),
                    new_phone=args.get("new_phone"),
                )
            if name == "answer_business_question":
                hits = self.vector_store.search(args["question"])
                if not hits:
                    return {"context": "No matching information found in the knowledge base."}
                return {"context": "\n\n".join(h["text"] for h in hits)}
            return {"error": f"Unknown tool '{name}'."}
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Tool '%s' failed with args %s: %s", name, args, exc)
            return {"error": f"Couldn't complete that — {exc}"}

    def _build_messages(self, question: str, history: list[ChatTurn]) -> list[dict]:
        today = date.today()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            business_name=settings.business_name,
            business_description=settings.business_description,
            today=today.isoformat(),
            weekday=today.strftime("%A"),
            cancellation_window_hours=settings.cancellation_window_hours,
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