"""Server-side Deepgram STT/TTS connections for phone calls.

The browser voice flow (deepgram_provider.py) mints a short-lived ephemeral
token so the *client* can connect to Deepgram directly. For phone calls
there's no client to hand a token to — Exotel streams caller audio to our
backend, so the backend itself holds a normal Deepgram connection using the
real API key. That key never leaves the server.
"""

from app.core.config import get_settings

settings = get_settings()

_STT_WS = "wss://api.deepgram.com/v1/listen"
_TTS_WS = "wss://api.deepgram.com/v1/speak"


class TelephonyVoiceConfigError(RuntimeError):
    pass


def _require_api_key() -> str:
    if not settings.deepgram_api_key:
        raise TelephonyVoiceConfigError(
            "DEEPGRAM_API_KEY is not set. Add it to backend/.env to enable phone-call voice."
        )
    return settings.deepgram_api_key


async def open_stt_stream(sample_rate: int):
    """Opens a live Deepgram STT connection for one call leg. Same tuning
    (nova-2, smart_format, endpointing, VAD events) as the browser flow, but
    at the telephony sample rate (8kHz by default) so no resampling of the
    caller's audio is needed on either side."""
    import websockets

    params = (
        "model=nova-2&language=en-US&smart_format=true&interim_results=true"
        f"&endpointing=300&vad_events=true&encoding=linear16&sample_rate={sample_rate}"
    )
    url = f"{_STT_WS}?{params}"
    return await websockets.connect(
        url, additional_headers={"Authorization": f"Token {_require_api_key()}"}
    )


async def open_tts_stream(voice_name: str, sample_rate: int):
    """Opens a live Deepgram TTS connection for one call leg, generating
    audio directly at the telephony sample rate so it can be forwarded to
    Exotel without resampling."""
    import websockets

    params = f"model={voice_name}&encoding=linear16&sample_rate={sample_rate}"
    url = f"{_TTS_WS}?{params}"
    return await websockets.connect(
        url, additional_headers={"Authorization": f"Token {_require_api_key()}"}
    )