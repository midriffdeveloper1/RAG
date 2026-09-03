import logging
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings
from app.realtime.base import RealtimeVoiceProvider

logger = logging.getLogger(__name__)
settings = get_settings()

_DEEPGRAM_API_BASE = "https://api.deepgram.com/v1"
_DEEPGRAM_GRANT_URL = f"{_DEEPGRAM_API_BASE}/auth/grant"
_DEEPGRAM_STT_WS = "wss://api.deepgram.com/v1/listen"
_DEEPGRAM_TTS_WS = "wss://api.deepgram.com/v1/speak"

_MAX_TTL_SECONDS = 3600
_MIN_TTL_SECONDS = 1


class DeepgramConfigError(RuntimeError):
    pass


class DeepgramVoiceProvider(RealtimeVoiceProvider):
    def __init__(self) -> None:
        if not settings.deepgram_api_key:
            raise DeepgramConfigError(
                "DEEPGRAM_API_KEY is not set. Add it to backend/.env to enable Voice mode."
            )
        self._api_key = settings.deepgram_api_key

    def create_ephemeral_token(self, ttl_seconds: int = 60) -> dict[str, Any]:
        ttl = max(_MIN_TTL_SECONDS, min(ttl_seconds, _MAX_TTL_SECONDS))
        headers = {"Authorization": f"Token {self._api_key}"}

        try:
            response = httpx.post(
                _DEEPGRAM_GRANT_URL, json={"ttl_seconds": ttl}, headers=headers, timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                logger.error(
                    "Deepgram rejected the token grant (403). The DEEPGRAM_API_KEY needs at "
                    "least 'Member' permission on the project — check the key's role in the "
                    "Deepgram Console."
                )
            else:
                logger.exception("Failed to mint Deepgram ephemeral token")
            raise
        except httpx.HTTPError:
            logger.exception("Failed to mint Deepgram ephemeral token")
            raise

        data = response.json()
        return {"token": data["access_token"], "expires_in_seconds": data.get("expires_in", ttl)}

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