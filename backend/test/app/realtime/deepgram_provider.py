import logging
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings
from app.realtime.base import RealtimeVoiceProvider

logger = logging.getLogger(__name__)
settings = get_settings()

_DEEPGRAM_API_BASE = "https://api.deepgram.com/v1"
_DEEPGRAM_STT_WS = "wss://api.deepgram.com/v1/listen"
_DEEPGRAM_TTS_WS = "wss://api.deepgram.com/v1/speak"

_BROWSER_TOKEN_SCOPES = ["usage:write"]


class DeepgramConfigError(RuntimeError):
    pass


class DeepgramVoiceProvider(RealtimeVoiceProvider):
    def __init__(self) -> None:
        if not settings.deepgram_api_key:
            raise DeepgramConfigError(
                "DEEPGRAM_API_KEY is not set. Add it to backend/.env to enable Voice mode."
            )
        if not settings.deepgram_project_id:
            raise DeepgramConfigError(
                "DEEPGRAM_PROJECT_ID is not set. Add it to backend/.env to enable Voice mode."
            )
        self._api_key = settings.deepgram_api_key
        self._project_id = settings.deepgram_project_id

    def create_ephemeral_token(self, ttl_seconds: int = 60) -> dict[str, Any]:
        """Mint a short-lived Deepgram key scoped to this browser session.

        The permanent DEEPGRAM_API_KEY never leaves the server — only this
        time-boxed token is returned to the client.
        """
        url = f"{_DEEPGRAM_API_BASE}/projects/{self._project_id}/keys"
        payload = {
            "comment": "voice-widget-ephemeral",
            "scopes": _BROWSER_TOKEN_SCOPES,
            "time_to_live_in_seconds": ttl_seconds,
        }
        headers = {"Authorization": f"Token {self._api_key}"}

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Failed to mint Deepgram ephemeral token")
            raise

        data = response.json()
        return {"token": data["key"], "expires_in_seconds": ttl_seconds}

    def stt_stream_config(self) -> dict[str, Any]:
        return {
            "url": _DEEPGRAM_STT_WS,
            "params": {
                "model": "nova-2",
                "language": "en-US",
                "smart_format": "true",
                "interim_results": "true",
                "endpointing": "300",
                "vad_events": "true",
                "encoding": "linear16",
                "sample_rate": "16000",
            },
        }

    def tts_stream_config(self, voice_name: str) -> dict[str, Any]:
        return {
            "url": _DEEPGRAM_TTS_WS,
            "params": {
                "model": voice_name,
                "encoding": "linear16",
                "sample_rate": "24000",
            },
        }


@lru_cache
def get_voice_provider() -> DeepgramVoiceProvider:
    return DeepgramVoiceProvider()