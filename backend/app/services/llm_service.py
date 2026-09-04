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

import json
import logging
from functools import lru_cache
from typing import Any, Iterator

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env"
            )

        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            timeout=20.0,
            default_headers={
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
            temperature=(
                settings.openrouter_temperature
                if temperature is None
                else temperature
            ),
            max_tokens=(
                settings.openrouter_max_tokens
                if max_tokens is None
                else max_tokens
            ),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content or ""

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=(
                settings.openrouter_temperature
                if temperature is None
                else temperature
            ),
            max_tokens=(
                settings.openrouter_max_tokens
                if max_tokens is None
                else max_tokens
            ),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        choice = response.choices[0]
        content = choice.message.content or ""

        logger.debug(
            "LLM JSON response: content=%r finish_reason=%s",
            content,
            choice.finish_reason,
        )

        if not content:
            raise ValueError("LLM returned an empty response")

        # Detect truncation before trying json.loads().
        if choice.finish_reason == "length":
            logger.error(
                "LLM JSON response was truncated. "
                "finish_reason=%s content=%r",
                choice.finish_reason,
                content,
            )
            raise ValueError("LLM JSON response was truncated")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON returned by LLM: %r",
                content,
            )
            raise ValueError("LLM returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise ValueError("LLM JSON response must be a JSON object")

        return data

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]:

        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=(
                settings.openrouter_temperature
                if temperature is None
                else temperature
            ),
            max_tokens=(
                settings.openrouter_max_tokens
                if max_tokens is None
                else max_tokens
            ),
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

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ):
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