"""Provider abstraction for realtime speech (STT + TTS).

Only app/realtime/deepgram_provider.py implements this today. If the
business ever swaps speech vendors, only a new provider module needs to be
written — nothing in app/api/routes/voice.py or the orchestrator integration
should need to change.
"""
from abc import ABC, abstractmethod
from typing import Any


class RealtimeVoiceProvider(ABC):
    """Issues short-lived, browser-safe credentials for direct STT/TTS access.

    The provider is deliberately *not* responsible for conversation logic —
    it only ever hands out scoped, time-limited tokens so the browser can
    talk to the speech vendor directly. Business logic, tool execution, and
    the LLM conversation loop always stay server-side, reached through the
    existing Orchestrator via the voice WebSocket, never through the
    provider.
    """

    @abstractmethod
    def create_ephemeral_token(self, ttl_seconds: int = 60) -> dict[str, Any]:
        """Return a short-lived credential the browser can use directly.

        Must never return the permanent server-side API key.
        """
        raise NotImplementedError

    @abstractmethod
    def stt_stream_config(self) -> dict[str, Any]:
        """Connection config (URL + query params) for streaming speech-to-text."""
        raise NotImplementedError

    @abstractmethod
    def tts_stream_config(self, voice_name: str) -> dict[str, Any]:
        """Connection config (URL + query params) for streaming text-to-speech."""
        raise NotImplementedError
