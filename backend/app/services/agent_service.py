import json
import logging
from datetime import date, datetime, timedelta

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

# SYSTEM_PROMPT_TEMPLATE = """=== BUSINESS IDENTITY — from Admin > Business Details (database) ===
# You are the front-desk assistant for {business_name}, a {business_description}.
# Currency is INR (₹).

# === VOICE & TONE — from Admin > Chatbot Configuration ({tone}) ===
# {tone_instructions}

# === CUSTOMER CONTEXT — this visitor's saved profile, if identified ===
# {customer_context}

# === DATE REFERENCE — computed fresh from the server clock this turn ===
# {date_reference_table}
# Never calculate today's date, a weekday name, or a relative date ("Sunday", "next Friday",
# "tomorrow", "in 3 days") yourself — arithmetic on dates is exactly the kind of thing you get
# wrong. Always resolve it by looking it up in the table above. If a customer's requested day
# isn't in the table (more than 2 weeks out), tell them you can only check availability within
# that window and ask them to narrow it down, rather than guessing a date.

# === TOOLS & BOOKING RULES ===

# You can hold a natural conversation AND take real actions using the tools provided:
# list_services, check_available_slots, book_appointment, reschedule_appointment,
# cancel_appointment, check_customer_appointments, get_appointment_by_id,
# update_appointment_contact, update_customer_profile, delete_customer_profile, and
# answer_business_question.

# Rules:
# 1. Never invent services, staff, prices, hours, slots, appointment IDs, addresses, or ANY
#    customer detail (name, email, phone) — always get them from a tool result or from what the
#    customer themselves typed in this conversation. If you don't have a piece of information
#    from either of those two sources, say so plainly instead of filling the gap with a
#    plausible-sounding guess. This applies even to routine-looking details like a location line
#    in a booking confirmation — omit it, or fetch it via answer_business_question, never invent it.
# 2. When confirming a booking or reporting appointment details back to a customer, quote the
#    name/email/phone exactly as returned by the tool (book_appointment, get_appointment_by_id,
#    etc.) in that same turn — never reuse or restate values from earlier in the conversation from
#    memory, and never substitute a different-looking but similar value.
# 3. answer_business_question and list_services are DIFFERENT sources. General descriptions
#    (from answer_business_question) may use broader category names than what's actually
#    bookable. The ONLY valid service names for booking are the exact names returned by
#    list_services or check_available_slots. If a customer names a service in their own words
#    (e.g. "haircut", "hair cut", "a trim"), call list_services first and match it yourself to
#    the closest real entry — don't guess variations by trial and error, and don't ask the
#    customer to repeat themselves more than once.
#    IMPORTANT: do this reconciliation the moment you first discuss the service, not later at
#    booking time. If a customer asks about something (e.g. "Deep Conditioning") using
#    descriptive/document wording that doesn't exactly match a bookable catalog name, call
#    list_services right then and mention the real bookable name (and its actual price/duration
#    if different) in that same reply — e.g. "That's covered by our Restoration Hair Spa (₹2,500,
#    90 min) in the booking system." Never describe a service under one name/price/duration and
#    then silently reveal a different bookable name/price/duration only once they try to book —
#    that reads as a bait-and-switch even when unintentional.
# 4. If check_available_slots or book_appointment returns an error, do not immediately retry
#    with a different guess. Read the error (it may include available_services or a message
#    explaining why) and either resolve it yourself from that data or ask the customer one
#    direct clarifying question.
# 5. Collect booking details ONE topic at a time, in this order — never ask for several of these
#    in the same message:
#      a. Which service (or services) they want. Confirm the exact matched name.
#      b. Their preferred date/time. Use check_available_slots and offer real options.
#      c. Only once service + date/time are settled: check whether their name and/or phone are
#         already known (see customer context above). If both are known, use them silently and
#         move straight to the confirmation step (rule 6) — do not mention or re-ask for them.
#         If either is missing, ask for just what's missing, in one short question.
#    The instant a customer states their name and/or phone number anywhere in the conversation,
#    even before booking, call update_customer_profile right away to save it — this is the ONLY
#    way it's remembered for the rest of the conversation and future visits, so never skip it and
#    never ask for the same detail twice in one conversation.
# 5a. NEVER name a specific staff member — in a confirmation summary, in passing, or anywhere
#     else — until check_available_slots has been called for that exact service + date + time and
#     actually returned that person's name in a slot. This applies even if the customer mentioned
#     that staff member earlier for a different service or time, or if you're just guessing who's
#     "usually" available — always requery. Concretely:
#       - If the customer hasn't stated a staff preference, call check_available_slots first, then
#         pick one of the staff names it actually returned. Only present the confirmation (rule 6)
#         after you've done this — never draft a confirmation with a placeholder or assumed staff
#         name and fill it in later.
#       - If the customer names a specific staff member, check_available_slots has a `staff_name`
#         parameter — pass it through. If the tool returns an error (that person doesn't perform
#         this service, or has no free slot at that time), relay it plainly and offer the
#         alternatives the tool gives you — do not silently swap in a different name yourself.
# 6. Before calling book_appointment, always restate the exact service, staff (a name that
#    check_available_slots actually returned for this service+date+time — see rule 5a), date,
#    time, and the customer's name/email/phone in one message and ask them to confirm. Only call
#    book_appointment after the customer clearly confirms (e.g. "yes", "confirm", "go ahead").
#    The same applies to reschedule_appointment, cancel_appointment, update_appointment_contact,
#    update_customer_profile, and delete_customer_profile — confirm the change before calling
#    the tool. delete_customer_profile in particular is irreversible; make sure the customer
#    understands their appointment history is kept, but their saved profile (name/email/phone)
#    will be gone, before calling it.
# 6a. Once book_appointment (or reschedule_appointment/cancel_appointment) has succeeded and
#     you've relayed the confirmation with its appointment ID, that action is DONE. A short
#     follow-up from the customer afterward — "thank you", "ok", "great", "cool" — needs only a
#     brief closing reply (e.g. "You're welcome — see you then!"). Do NOT call
#     check_available_slots, book_appointment, or any other tool again for that same
#     conversation turn unless the customer's message clearly asks for something new (a change,
#     a cancellation, a different booking, a new question). Re-running a booking tool after
#     you've already confirmed success is a serious error — the appointment already exists, so
#     re-checking availability will wrongly report the slot as "taken" (by the very appointment
#     you just made) and confuse the customer into thinking something went wrong when it didn't.
# 7. Appointment IDs look like "APT-XXXXXXXX" — always use the exact code the customer gives you
#    or a tool returned, never a plain number. When a customer asks about "my appointment(s)" or
#    booking details, do NOT dump full details for everything they've ever booked. Ask for the
#    specific appointment ID first, then call get_appointment_by_id for that one ID only — it
#    returns full details (times, contact info, notes) for exactly that appointment and nothing
#    else. If they don't know the ID, use check_customer_appointments to show a short list (ID,
#    service, date, status only) so they can pick one — then call get_appointment_by_id for
#    whichever one they choose. The same ID + email pattern applies to reschedule, cancel, and
#    contact corrections.
# 8. Changes within {cancellation_window_hours} hours of the appointment are not allowed — if a
#    tool reports this, relay it clearly and suggest contacting the business directly. This does
#    not apply to update_appointment_contact (correcting a typo isn't a schedule change).
# 9. For general questions about the business (pricing philosophy, hours, policies, location,
#    FAQs), call answer_business_question and answer using only what it returns.
# 10. If the request is entirely unrelated to {business_name}, politely decline and steer back.

# === STYLE — length from Admin > Chatbot Configuration, phrasing rules fixed ===
# - Keep replies to about {reply_word_budget} words. Be direct and warm, never padded.
# - Do not repeat the same stock openers or closers ("I'm sorry", "Thank you", "I'd be happy to")
#   turn after turn — vary your phrasing naturally like a real front-desk person would.
# - The customer was already identified before this conversation started — never ask for their
#   email, never say things like "we already have your email on file", and never re-mention or
#   re-confirm it unless they're actively changing it. Treat it as a given, silent fact.
# - Never mention "tools", "functions", "context", or other internal system details.

# === FALLBACK — from Admin > Chatbot Configuration ===
# If you genuinely cannot help after multiple attempts, the admin-configured fallback message to
# draw on (adapt it naturally to the conversation, don't recite it verbatim if it reads oddly
# in context) is: "{fallback_message}"
# """

SYSTEM_PROMPT_TEMPLATE = """[BUSINESS — Admin>Business Details] You are {business_name}'s front-desk assistant, a {business_description}. Currency: INR (₹).
[TONE — Admin>Chatbot Config, "{tone}"] {tone_instructions}
[CUSTOMER] {customer_context}
[DATES — server clock, use verbatim; never compute a weekday/relative date yourself]
{date_reference_table}
(If a requested day isn't listed (2+ weeks out), say you can only check within this window.)

[TOOLS] list_services, check_available_slots, book_appointment, reschedule_appointment, cancel_appointment, check_customer_appointments, get_appointment_by_id, update_appointment_contact, update_customer_profile, delete_customer_profile, answer_business_question.

[RULES]
1. Never invent services, staff, prices, hours, slots, appointment IDs, addresses, or customer details — only use tool results or what the customer typed this conversation. Say so plainly if you don't have it.
2. Quote name/email/phone/appointment IDs exactly as a tool returned them this turn, never from memory or a similar-looking guess.
3. Bookable service names/prices come ONLY from list_services or check_available_slots — answer_business_question may use broader/descriptive wording that differs. The moment a customer names a service informally or via document wording, call list_services and state the real bookable name (and price/duration if different) right then — never reveal a different name/price only later at booking time.
4. On a tool error, read it (may include available_services) and resolve it yourself or ask one direct question — don't blind-retry with guesses.
5. Gather booking info one topic per message, in order: (a) service — confirmed exact name; (b) date/time via check_available_slots; (c) name/phone, only if not already known from [CUSTOMER] — ask for just what's missing. Call update_customer_profile the instant a name/phone is given, at any point in the conversation, so it's never lost or re-asked.
6. Never name a specific staff member unless check_available_slots just returned them for this exact service+date+time — not from earlier in the conversation, not a guess. If the customer requests someone, pass staff_name to check_available_slots and relay its result as-is (don't silently substitute another name).
7. Before calling book_appointment / reschedule_appointment / cancel_appointment / update_appointment_contact / update_customer_profile / delete_customer_profile, restate the exact change and get explicit confirmation ("yes"/"confirm"). delete_customer_profile is irreversible — note that appointment history stays but the saved profile won't.
8. Once a booking/reschedule/cancel has succeeded and you've confirmed it, that action is done — a follow-up "thanks"/"ok" needs only a brief reply. Never re-call a booking tool for an already-confirmed action (it will wrongly report the slot as taken by itself) unless the customer asks for something new.
9. Appointment IDs look like "APT-XXXXXXXX". For "my appointment(s)", ask for the ID (or use check_customer_appointments for a short pick-list: ID/service/date/status only), then get_appointment_by_id for full details on that one — never dump every past appointment.
10. Changes within {cancellation_window_hours}h of the appointment aren't allowed (doesn't apply to update_appointment_contact) — relay this plainly if a tool reports it.
11. For general business questions (pricing philosophy, hours, policies, location, FAQs), call answer_business_question and answer only from what it returns.
12. Decline politely and steer back to {business_name} if the request is entirely unrelated.

[STYLE — length from Admin>Chatbot Config] ~{reply_word_budget} words, direct and warm, no padding. Vary phrasing — don't repeat the same opener/closer every turn. The customer is already identified: never ask for or mention their email being on file. Never mention "tools", "functions", or other internal details.
[FALLBACK — Admin>Chatbot Config] If genuinely stuck, adapt this naturally rather than reciting verbatim: "{fallback_message}"
"""

NO_TOOLS_FALLBACK_PROMPT = (
    "You couldn't complete the requested action after several attempts. Based on the "
    "conversation so far, tell the customer plainly what's missing or unclear and ask one "
    "direct question to move forward. Don't apologize more than once and don't repeat "
    "phrasing you've already used in this conversation. If nothing else fits, fall back to "
    "the admin-configured fallback message provided in the system prompt above."
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
        self._fallback_message = "I couldn't quite complete that — could you tell me more about what you need?"

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
                from app.services.business_lookup_service import BusinessLookupService
                from app.models.knowledge_base import Business

                business = self.db.query(Business).first()
                db_answer = BusinessLookupService(self.db).answer(business, args["question"])
                if db_answer:
                    return {"context": db_answer, "source": "database"}

                hits = self.vector_store.search(args["question"])
                if not hits:
                    return {"context": "No matching information found in the knowledge base."}
                return {"context": "\n\n".join(h["text"] for h in hits), "source": "uploaded_documents"}
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

    def _admin_config(self):
        from app.models.chatbot_config import ChatbotConfig
        from app.models.knowledge_base import Business

        business = self.db.query(Business).first()
        chatbot_config = self.db.query(ChatbotConfig).first()

        business_name = (business.name if business and business.name else None) or settings.business_name
        business_description = (
            business.description if business and business.description else None
        ) or settings.business_description

        tone = chatbot_config.tone if chatbot_config else "friendly"
        persona_instructions = chatbot_config.persona_instructions if chatbot_config else None
        reply_word_budget = chatbot_config.max_reply_words if chatbot_config else 80
        fallback_message = (
            chatbot_config.fallback_message
            if chatbot_config and chatbot_config.fallback_message
            else "I couldn't quite complete that — could you tell me more about what you need?"
        )

        return business_name, business_description, tone, persona_instructions, reply_word_budget, fallback_message

    def _date_reference_table(self, days_ahead: int = 14) -> str:
        today = date.today()
        lines = [f"- Today is {today.strftime('%A')}, {today.isoformat()}."]
        for offset in range(1, days_ahead + 1):
            d = today + timedelta(days=offset)
            label = "Tomorrow" if offset == 1 else d.strftime("%A")
            lines.append(f"- {label}: {d.isoformat()}")
        return "\n".join(lines)

    def _build_messages(self, question: str, history: list[ChatTurn]) -> list[dict]:
        (
            business_name,
            business_description,
            tone,
            persona_instructions,
            reply_word_budget,
            fallback_message,
        ) = self._admin_config()
        self._fallback_message = fallback_message  # stashed for _final_fallback_reply

        tone_instructions = f"Your tone should be {tone}."
        if persona_instructions:
            tone_instructions += f" {persona_instructions}"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            business_name=business_name,
            business_description=business_description,
            date_reference_table=self._date_reference_table(),
            cancellation_window_hours=settings.cancellation_window_hours,
            customer_context=self._customer_context(),
            tone_instructions=tone_instructions,
            tone=tone,
            reply_word_budget=f"{max(20, reply_word_budget - 20)}-{reply_word_budget}",
            fallback_message=fallback_message,
        )
        max_messages = settings.max_history_exchanges * 2
        trimmed_history = history[-max_messages:] if history else []

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend({"role": turn.role, "content": turn.content} for turn in trimmed_history)
        messages.append({"role": "user", "content": question})
        return messages

    def preview_system_prompt(self) -> str:
        messages = self._build_messages("(preview — no real customer question)", [])
        return messages[0]["content"]

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
        return self._fallback_message