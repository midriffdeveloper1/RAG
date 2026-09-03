from sqlalchemy.orm import Session

from app.models.chatbot_config import ChatbotConfig
from app.schemas.chatbot_config import ChatbotConfigUpdate


class ChatbotConfigService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self) -> ChatbotConfig:
        config = self.db.query(ChatbotConfig).first()
        if config is None:
            config = ChatbotConfig()
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update(self, payload: ChatbotConfigUpdate) -> ChatbotConfig:
        config = self.get_or_create()
        data = payload.model_dump(exclude_unset=True, exclude={"suggested_questions"})
        for field, value in data.items():
            setattr(config, field, value)

        if payload.suggested_questions is not None:
            config.set_suggested_questions(payload.suggested_questions)

        self.db.commit()
        self.db.refresh(config)
        return config