import logging
from functools import lru_cache

from groq import Groq

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env — "
                "get a free key at https://console.groq.com/keys"
            )
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        kwargs: dict = {
            "model": self.model,
            "temperature": settings.groq_temperature,
            "max_tokens": settings.groq_max_tokens,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()