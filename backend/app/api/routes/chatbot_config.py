from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.chatbot_config import ChatbotConfig
from app.schemas.chatbot_config import ChatbotConfigOut, ChatbotConfigUpdate
from app.services.chatbot_config_service import ChatbotConfigService

router = APIRouter(prefix="/admin/chatbot-config", tags=["Admin Chatbot Config"])


def _to_out(config: ChatbotConfig) -> ChatbotConfigOut:
    return ChatbotConfigOut(
        widget_title=config.widget_title,
        tagline=config.tagline,
        avatar_emoji=config.avatar_emoji,
        primary_color=config.primary_color,
        accent_color=config.accent_color,
        tone=config.tone,
        persona_instructions=config.persona_instructions,
        greeting_message=config.greeting_message,
        fallback_message=config.fallback_message,
        max_reply_words=config.max_reply_words,
        temperature=config.temperature,
        enable_appointment_booking=config.enable_appointment_booking,
        enable_knowledge_base=config.enable_knowledge_base,
        enable_email_gate=config.enable_email_gate,
        show_suggested_questions=config.show_suggested_questions,
        suggested_questions=config.suggested_questions_list,
    )


@router.get("", response_model=ChatbotConfigOut)
def get_chatbot_config(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    config = ChatbotConfigService(db).get_or_create()
    return _to_out(config)


@router.put("", response_model=ChatbotConfigOut)
def update_chatbot_config(
    payload: ChatbotConfigUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    config = ChatbotConfigService(db).update(payload)
    return _to_out(config)


@router.get("/preview-prompt")
def preview_system_prompt(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    
    from app.services.agent_service import AgentService

    try:
        agent = AgentService(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"prompt": agent.preview_system_prompt()}