from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.customer import Customer

settings = get_settings()


def admin_config(db: Session) -> dict:
    from app.models.chatbot_config import ChatbotConfig
    from app.models.knowledge_base import Business

    business = db.query(Business).first()
    chatbot_config = db.query(ChatbotConfig).first()

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

    return {
        "business_name": business_name,
        "business_description": business_description,
        "tone": tone,
        "persona_instructions": persona_instructions,
        "reply_word_budget": reply_word_budget,
        "fallback_message": fallback_message,
    }


def tone_instructions(cfg: dict) -> str:
    text = f"Your tone should be {cfg['tone']}."
    if cfg["persona_instructions"]:
        text += f" {cfg['persona_instructions']}"
    return text


def date_reference_table(days_ahead: int = 14) -> str:
    today = date.today()
    lines = [f"- Today is {today.strftime('%A')}, {today.isoformat()}."]
    for offset in range(1, days_ahead + 1):
        d = today + timedelta(days=offset)
        label = "Tomorrow" if offset == 1 else d.strftime("%A")
        lines.append(f"- {label}: {d.isoformat()}")
    return "\n".join(lines)


def customer_context(customer: Customer | None) -> str:
    if customer is None:
        return ""
    parts = [f"email is {customer.email}"]
    if customer.name:
        parts.append(f"name is {customer.name}")
    if customer.phone:
        parts.append(f"phone is {customer.phone}")
    known = ", ".join(parts)
    if customer.name and customer.phone:
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