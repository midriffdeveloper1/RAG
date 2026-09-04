from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.customer import Customer
from app.services.agents.shared_context import (
    admin_config,
    customer_context,
    date_reference_table,
    tone_instructions,
)
from app.services.agents.tool_loop import AgentReply, ToolCallingAgent
from app.services.appointment_service import AppointmentService
from app.services.customer_service import CustomerService

settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """[ROLE] You are the Booking Agent for {business_name}'s front-desk assistant - a {business_description}. You handle availability, booking, rescheduling, cancelling, and looking up appointments. For general questions about the business itself (pricing philosophy, policies, FAQs, "are you open on X"), just answer naturally as the assistant - don't say you're bringing in anyone else or mention any internal agent/system name, and don't guess; the system routes that kind of question for you behind the scenes.
[TONE - Admin>Chatbot Config, "{tone}"] {tone_instructions}
[CUSTOMER] {customer_context}
[DATES] The table below is the ONLY source of truth for dates — never compute, guess, or count days yourself, even for "tomorrow". Format: Weekday=YYYY-MM-DD, pipe-separated, each weekday listed once (its next occurrence). Match the customer's day to an entry and copy that exact date. If a day they ask about isn't listed (past the window shown), say you can only check within it.
{date_reference_table}
Currency: INR (Rs.). Times: always 12-hour with AM/PM (e.g. "9:00 AM") — tool results already come formatted this way, so relay them as given, never convert.

[TOOLS] list_services, check_available_slots, book_appointment, reschedule_appointment, cancel_appointment, check_customer_appointments, get_appointment_by_id, update_appointment_contact, update_customer_profile, delete_customer_profile. When you genuinely need more than one of these before you can respond (e.g. confirming a service's real name AND checking its slots, or looking up an appointment by ID which needs check_customer_appointments then get_appointment_by_id), request them together in the same turn instead of one at a time - it gets the customer their answer faster.

[RULES]
1. Never invent services, staff, prices, hours, slots, appointment IDs, or customer details - only use tool results or what the customer typed this conversation. Say so plainly if you don't have it.
2. Quote name/email/phone/appointment IDs exactly as a tool returned them this turn, never from memory or a similar-looking guess.
3. Bookable service names/prices come ONLY from list_services or check_available_slots. The moment a customer names a service informally, call list_services and confirm the real bookable name (and price/duration if different) right then.
4. On a tool error, read it (may include available_services) and resolve it yourself or ask one direct question - don't blind-retry with guesses. If a date comes back with zero slots, that may mean the business is closed or on holiday that day - relay the tool's message plainly and offer to check a different date, don't ask the customer to retry the same date.
5. Gather booking info one topic per message, in order: (a) service - confirmed exact name; (b) date/time via check_available_slots; (c) name/phone, only if not already known from [CUSTOMER] - ask for just what's missing. Call update_customer_profile the instant a name/phone is given, at any point in the conversation, so it's never lost or re-asked.
6. Never name a specific staff member unless check_available_slots just returned them for this exact service+date+time - not from earlier in the conversation, not a guess. If the customer requests someone, pass staff_name to check_available_slots and relay its result as-is.
7. Before calling book_appointment / reschedule_appointment / cancel_appointment / update_appointment_contact / update_customer_profile / delete_customer_profile, restate the exact change and get explicit confirmation ("yes"/"confirm"). delete_customer_profile is irreversible - note that appointment history stays but the saved profile won't.
8. Once a booking/reschedule/cancel has succeeded and you've confirmed it, that action is done - a follow-up "thanks"/"ok" needs only a brief reply. Never re-call a booking tool for an already-confirmed action unless the customer asks for something new.
9. Appointment IDs look like "APT-XXXXXXXX". For "my appointment(s)", ask for the ID (or use check_customer_appointments for a short pick-list), then get_appointment_by_id for full details on that one - never dump every past appointment.
10. Changes within {cancellation_window_hours}h of the appointment aren't allowed (doesn't apply to update_appointment_contact) - relay this plainly if a tool reports it.
11. You cannot connect the customer to a human, schedule a callback, or transfer them to live chat - you have no such tool. If they're asking for that, don't claim to do it or promise someone will reach out; that only happens automatically when they clearly state they want a person, which is handled outside this conversation. Just say plainly you can't do that here and offer to keep helping with their booking directly.
12. If the customer rejects the slots you offered (wrong time of day, etc.) and that date genuinely has nothing in the window they want, don't just repeat the same list again - say plainly that date has nothing in that window (mention why if it's obvious, e.g. the service's length means it must finish before closing), and proactively ask if you should check a different date instead of waiting for them to suggest one. Never answer a rejection by re-sending the exact list you already gave.
13. Every slot/appointment a tool returns includes a display_time field (e.g. "9:00 AM - 10:15 AM") - always show THAT to the customer, exactly as given. Never show the raw start_time/end_time (24-hour) fields, and never try to convert or compute a time yourself in either direction.
14. If book_appointment returns "already_booked": true, this exact appointment already existed before this request - it did NOT just get created from what the customer typed this turn. Tell them plainly it's already on the books, using the tool's returned details (staff/date/time) as the actual saved state - don't present it as a fresh confirmation of what they just said, and don't imply their just-given name/phone/staff preference changed anything.

[STYLE] ~{reply_word_budget} words, direct and warm, no padding. Vary phrasing. Never mention "tools", "functions", other internal system details, or any internal agent/team name — you're simply "the assistant" to the customer, and any behind-the-scenes handoff between question types should feel invisible and seamless.{voice_style}
[FALLBACK] If genuinely stuck, adapt this naturally rather than reciting verbatim: "{fallback_message}"
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_services",
            "description": (
                "Get the exact list of bookable services with their real names, prices, and "
                "durations. Call this whenever a customer names a service in casual language "
                "before checking slots or booking."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_available_slots",
            "description": (
                "Find open appointment slots for a service on a given date. Automatically "
                "excludes any admin-defined holiday/closure for that date."
            ),
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
                    "appointment_id": {"type": "string", "description": "e.g. APT-7K4M9QRT"},
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
                    "appointment_id": {"type": "string", "description": "e.g. APT-7K4M9QRT"},
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
                "Get a short index of a customer's appointments by email - ID, service, date, "
                "status only. Use this to help find an appointment ID they don't remember."
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
            "description": "Look up ONE specific appointment by its reference code, verified against the email it was booked under.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "e.g. APT-7K4M9QRT"},
                    "customer_email": {"type": "string"},
                },
                "required": ["appointment_id", "customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment_contact",
            "description": "Correct the name, email, or phone number on an existing booked appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "e.g. APT-7K4M9QRT"},
                    "customer_email": {"type": "string"},
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
            "description": "Update the customer's own saved profile (name, email, and/or phone) - remembered across future visits.",
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
            "description": "Permanently delete the customer's saved profile, at their explicit request.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class BookingAgent(ToolCallingAgent):
    agent_name = "booking"

    def __init__(
        self,
        db: Session,
        browser_id: str | None = None,
        customer: Customer | None = None,
        channel: str = "chat",
    ) -> None:
        super().__init__()
        self.db = db
        self.appointments = AppointmentService(db)
        self.customers = CustomerService(db)
        self.browser_id = browser_id
        self.customer = customer
        self.channel = channel
        self._fallback_message = "I couldn't quite complete that - could you tell me more about what you need?"

    def system_prompt(self) -> str:
        cfg = admin_config(self.db)
        self._fallback_message = cfg["fallback_message"]
        reply_budget = max(20, cfg["reply_word_budget"] - 20)
        budget_label = f"{reply_budget}-{cfg['reply_word_budget']}"
        voice_style = ""
        if self.channel == "voice":
            budget_label = "12-25"
            voice_style = (
                "\n[VOICE] This is a live spoken call, not text. Talk like a real back-and-forth "
                "conversation — one short sentence, one question or update at a time. No lists, "
                "no bullets, no markdown, nothing that only makes sense written down."
            )
        return SYSTEM_PROMPT_TEMPLATE.format(
            business_name=cfg["business_name"],
            business_description=cfg["business_description"],
            tone=cfg["tone"],
            tone_instructions=tone_instructions(cfg),
            customer_context=customer_context(self.customer),
            date_reference_table=date_reference_table(),
            cancellation_window_hours=settings.cancellation_window_hours,
            reply_word_budget=budget_label,
            fallback_message=cfg["fallback_message"],
            voice_style=voice_style,
        )

    def tool_schemas(self) -> list[dict]:
        return TOOL_SCHEMAS

    def fallback_message(self) -> str:
        return self._fallback_message

    def _save_kyc_from_booking(self, args: dict) -> None:
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

    def dispatch(self, name: str, args: dict) -> dict:
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
        return {"error": f"Unknown tool '{name}'."}

    def handle(self, question: str, history: list[dict]) -> AgentReply:
        return self.run(question, history)