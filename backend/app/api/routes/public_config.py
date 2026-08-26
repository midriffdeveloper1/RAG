from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.chatbot_config_service import ChatbotConfigService

router = APIRouter(prefix="/chatbot-config", tags=["Public Chatbot Config"])


@router.get("")
def get_public_chatbot_config(db: Session = Depends(get_db)):
    config = ChatbotConfigService(db).get_or_create()
    return {
        "widget_title": config.widget_title,
        "tagline": config.tagline,
        "avatar_emoji": config.avatar_emoji,
        "primary_color": config.primary_color,
        "accent_color": config.accent_color,
        "greeting_message": config.greeting_message,
        "enable_appointment_booking": config.enable_appointment_booking,
        "show_suggested_questions": config.show_suggested_questions,
        "suggested_questions": config.suggested_questions_list,
    }