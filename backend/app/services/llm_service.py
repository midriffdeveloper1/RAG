# import json
# import logging
# from functools import lru_cache
# from typing import Iterator

# from groq import Groq

# from app.core.config import get_settings

# logger = logging.getLogger(__name__)
# settings = get_settings()


# class LLMService:
#     def __init__(self) -> None:
#         if not settings.groq_api_key:
#             raise RuntimeError(
#                 "GROQ_API_KEY is not set. Add it to backend/.env — "
#                 "get a free key at https://console.groq.com/keys"
#             )
#         self.client = Groq(api_key=settings.groq_api_key, max_retries=0, timeout=20.0)
#         self.model = settings.groq_model

#     def generate(
#         self,
#         system_prompt: str,
#         user_prompt: str,
#         max_tokens: int | None = None,
#         temperature: float | None = None,
#     ) -> str:
#         response = self.client.chat.completions.create(
#             model=self.model,
#             temperature=settings.groq_temperature if temperature is None else temperature,
#             max_tokens=settings.groq_max_tokens if max_tokens is None else max_tokens,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt},
#             ],
#         )
#         return response.choices[0].message.content

#     def generate_stream(
#         self,
#         system_prompt: str,
#         user_prompt: str,
#         max_tokens: int | None = None,
#         temperature: float | None = None,
#     ) -> Iterator[str]:
       
#         stream = self.client.chat.completions.create(
#             model=self.model,
#             temperature=settings.groq_temperature if temperature is None else temperature,
#             max_tokens=settings.groq_max_tokens if max_tokens is None else max_tokens,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt},
#             ],
#             stream=True,
#         )
#         for chunk in stream:
#             delta = chunk.choices[0].delta.content
#             if delta:
#                 yield delta

#     def generate_json(
#         self,
#         system_prompt: str,
#         user_prompt: str,
#         max_tokens: int | None = None,
#         temperature: float | None = None,
#     ) -> dict:
#         response = self.client.chat.completions.create(
#             model=self.model,
#             temperature=settings.groq_temperature if temperature is None else temperature,
#             max_tokens=settings.groq_max_tokens if max_tokens is None else max_tokens,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt},
#             ],
#             response_format={"type": "json_object"},
#         )
#         return json.loads(response.choices[0].message.content)

#     def chat(self, messages: list[dict], tools: list[dict] | None = None):
#         kwargs: dict = {
#             "model": self.model,
#             "temperature": settings.groq_temperature,
#             "max_tokens": settings.groq_max_tokens,
#             "messages": messages,
#         }
#         if tools:
#             kwargs["tools"] = tools
#             kwargs["tool_choice"] = "auto"

#         response = self.client.chat.completions.create(**kwargs)
#         return response.choices[0].message


# @lru_cache
# def get_llm_service() -> LLMService:
#     return LLMService()

import logging
from functools import lru_cache
from typing import Iterator
 
from openai import OpenAI
 
from app.core.config import get_settings
 
logger = logging.getLogger(__name__)
settings = get_settings()
 
 
class LLMService:
    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env — "
                "get a key at https://openrouter.ai/keys"
            )
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            timeout=20.0,
            default_headers={
                # Optional but recommended by OpenRouter for analytics/rankings
                "HTTP-Referer": settings.openrouter_site_url or "",
                "X-Title": settings.openrouter_site_name or "",
            },
        )
        self.model = settings.openrouter_model
 
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=settings.openrouter_temperature if temperature is None else temperature,
            max_tokens=settings.openrouter_max_tokens if max_tokens is None else max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
 
    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]:
        """Yield response text incrementally, for progressive display/TTS.
 
        Used by the voice layer so the assistant's text (and, downstream,
        speech) can start rendering before the full reply is generated. Chat
        mode doesn't need this today but can adopt it the same way.
        """
        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=settings.openrouter_temperature if temperature is None else temperature,
            max_tokens=settings.openrouter_max_tokens if max_tokens is None else max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
 
    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        kwargs: dict = {
            "model": self.model,
            "temperature": settings.openrouter_temperature,
            "max_tokens": settings.openrouter_max_tokens,
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