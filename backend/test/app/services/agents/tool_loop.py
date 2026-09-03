import json
import logging
from dataclasses import dataclass, field
from typing import Callable

from app.core.config import get_settings
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AgentReply:
    answer: str
    agent: str
    sources: list[dict] = field(default_factory=list)
    resolved: bool = True  


class ToolCallingAgent:

    agent_name: str = "agent"

    def __init__(self) -> None:
        self.llm = get_llm_service()

    def system_prompt(self) -> str:  
        raise NotImplementedError

    def tool_schemas(self) -> list[dict]:  
        raise NotImplementedError

    def dispatch(self, name: str, args: dict) -> dict:  
        raise NotImplementedError

    def fallback_message(self) -> str:
        return "I couldn't quite complete that — could you tell me more about what you need?"

    def run(self, question: str, history: list[dict]) -> AgentReply:
        messages = [{"role": "system", "content": self.system_prompt()}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        for _ in range(settings.max_tool_iterations):
            message = self.llm.chat(messages, tools=self.tool_schemas())

            if not message.tool_calls:
                return AgentReply(answer=message.content, agent=self.agent_name)

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
                try:
                    result = self.dispatch(call.function.name, args)
                except (KeyError, ValueError, TypeError) as exc:
                    logger.warning("Tool '%s' failed with args %s: %s", call.function.name, args, exc)
                    result = {"error": f"Couldn't complete that — {exc}"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return AgentReply(
            answer=self._final_fallback_reply(messages),
            agent=self.agent_name,
            resolved=False,
        )

    def _final_fallback_reply(self, messages: list[dict]) -> str:
        prompt = (
            "You couldn't complete the requested action after several attempts. Based on the "
            "conversation so far, tell the customer plainly what's missing or unclear and ask "
            "one direct question to move forward. Don't apologize more than once."
        )
        try:
            final = self.llm.chat(messages + [{"role": "user", "content": prompt}], tools=None)
            if final.content:
                return final.content
        except Exception:  # noqa: BLE001 - best-effort fallback, never raise here
            logger.exception("Fallback reply generation failed for agent '%s'", self.agent_name)
        return self.fallback_message()