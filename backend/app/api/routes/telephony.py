"""Inbound PSTN voice calls via Exotel's AgentStream (Voicebot Applet).

Exotel is configured (in the Exotel App Bazaar) to connect an incoming call
to `wss://<host>/api/v1/telephony/exotel/stream` — either as a static URL,
or dynamically via POST /telephony/exotel/stream-url. From then on it's a
bidirectional WebSocket carrying JSON control events plus base64-encoded
raw PCM audio (see exotel_codec.py for the wire format).

This mirrors app/api/routes/voice.py's browser flow as closely as possible:
the same ConversationService -> OrchestratorService -> agents pipeline, the
same unclear-speech/clarification/escalation handling from tool_bridge.py,
and the same barge-in semantics — just with the backend itself driving
Deepgram STT/TTS (via telephony_bridge.py) instead of the browser, and
Exotel's "clear" event instead of a local audio queue for interrupts.
"""

import asyncio
import base64
import binascii
import json
import logging

import websockets
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.realtime.exotel_codec import (
    ExotelAudioChunker,
    build_clear_message,
    build_media_message,
    decode_media_payload,
)
from app.realtime.telephony_bridge import TelephonyVoiceConfigError, open_stt_stream, open_tts_stream
from app.realtime.telephony_session import PhoneCallSessionService
from app.realtime.tool_bridge import (
    clarification_turn,
    escalate_for_unclear_speech,
    escalate_voice_call,
    is_unclear_transcript,
    stream_turn,
)
from app.realtime.events import RealtimeEvent, RealtimeEventType
from app.services.chatbot_config_service import ChatbotConfigService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telephony", tags=["Telephony"])
settings = get_settings()

# Mirrors MIN_BARGE_IN_CHARS in the frontend's useVoiceSession.js — a VAD
# "speech started" blip alone isn't enough to cut the assistant off; wait
# for real transcribed content first.
_MIN_BARGE_IN_CHARS = 2
_SENTENCE_SPLIT_CHARS = (".", "!", "?")


def _split_sentences(text: str) -> list[str]:
    sentences, buf = [], ""
    for ch in text:
        buf += ch
        if ch in _SENTENCE_SPLIT_CHARS:
            sentences.append(buf.strip())
            buf = ""
    if buf.strip():
        sentences.append(buf.strip())
    return sentences or [text]


@router.post("/exotel/stream-url")
def exotel_stream_url(request: Request):
    """Optional dynamic-URL target for the Voicebot Applet (Exotel supports
    either a static wss:// URL configured in App Bazaar, or an HTTPS
    endpoint like this one that returns the URL to use for that call)."""
    host = settings.public_websocket_host or request.url.hostname
    scheme = "wss" if request.url.scheme == "https" else "ws"
    return {"url": f"{scheme}://{host}{settings.api_v1_prefix}/telephony/exotel/stream"}


def _authorized(websocket: WebSocket) -> bool:
    if not settings.exotel_stream_username or not settings.exotel_stream_password:
        # No credentials configured — rely on IP allowlisting instead
        # (Exotel's other supported auth method). Not recommended for
        # production without one or the other.
        return True
    auth = websocket.headers.get("authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
    except (binascii.Error, ValueError):
        return False
    expected = f"{settings.exotel_stream_username}:{settings.exotel_stream_password}"
    return decoded == expected


class _CallState:
    def __init__(self, db: Session, browser_id: str, session, sample_rate: int, barge_in_enabled: bool):
        self.db = db
        self.browser_id = browser_id
        self.session = session
        self.sample_rate = sample_rate
        self.barge_in_enabled = barge_in_enabled

        self.stream_sid: str | None = None
        self.stt_ws = None
        self.tts_ws = None
        self.chunker = ExotelAudioChunker()

        self.unclear_streak = 0
        self.assistant_speaking = False
        self.pending_barge_in = False
        self.drop_until_flushed = False
        self.closed = False
        self.send_lock = asyncio.Lock()
        # The STT receiver task and the main loop (e.g. DTMF "press 0")
        # both touch `db` — guard against them ever doing so concurrently,
        # since a SQLAlchemy Session isn't safe to share across tasks.
        self.db_lock = asyncio.Lock()


async def _speak_text(call: "_CallState", text: str) -> None:
    call.assistant_speaking = True
    for sentence in _split_sentences(text):
        if not call.assistant_speaking:
            break  # a barge-in landed mid-utterance; stop feeding more sentences to TTS
        try:
            await call.tts_ws.send(json.dumps({"type": "Speak", "text": sentence}))
            await call.tts_ws.send(json.dumps({"type": "Flush"}))
        except websockets.ConnectionClosed:
            break


async def _speak_events(call: "_CallState", events: list[RealtimeEvent]) -> None:
    final_text = ""
    for event in events:
        if event.type == RealtimeEventType.ASSISTANT_TEXT_COMPLETED:
            final_text = event.data.get("text", "")
    if final_text.strip():
        await _speak_text(call, final_text)


async def _process_transcript(call: "_CallState", transcript: str, confidence: float | None) -> bool:
    """Returns False if the call was escalated to a human and should stop
    listening for further turns from the assistant side."""
    if is_unclear_transcript(transcript, confidence, settings.voice_min_confidence):
        call.unclear_streak += 1
        if call.unclear_streak > settings.voice_unclear_max_attempts:
            async with call.db_lock:
                events = await asyncio.to_thread(
                    lambda: list(escalate_for_unclear_speech(call.db, call.session, "voice"))
                )
            await _speak_events(call, events)
            return False
        async with call.db_lock:
            events = await asyncio.to_thread(
                lambda: list(clarification_turn(call.db, call.session, "voice", call.unclear_streak - 1))
            )
        await _speak_events(call, events)
        return True

    call.unclear_streak = 0
    async with call.db_lock:
        events = await asyncio.to_thread(
            lambda: list(stream_turn(call.db, call.session, call.browser_id, transcript, None))
        )
    needs_human = any(
        e.type == RealtimeEventType.ASSISTANT_TEXT_COMPLETED and e.data.get("needs_human") for e in events
    )
    await _speak_events(call, events)
    return not needs_human


async def _handle_barge_in(call: "_CallState", websocket: WebSocket) -> None:
    if not call.barge_in_enabled or not call.assistant_speaking:
        return
    call.assistant_speaking = False
    call.drop_until_flushed = True
    call.chunker.reset()
    try:
        async with call.send_lock:
            await websocket.send_json(build_clear_message(call.stream_sid))
    except Exception:
        pass


async def _send_media_frame(call: "_CallState", websocket: WebSocket, frame: bytes) -> None:
    try:
        async with call.send_lock:
            await websocket.send_json(build_media_message(call.stream_sid, frame))
    except Exception:
        pass


async def _stt_receiver_loop(call: "_CallState", websocket: WebSocket) -> None:
    try:
        async for message in call.stt_ws:
            if call.closed:
                break
            try:
                data = json.loads(message)
            except (TypeError, ValueError):
                continue

            msg_type = data.get("type")
            if msg_type == "SpeechStarted":
                call.pending_barge_in = True
                continue
            if msg_type != "Results":
                continue

            alternatives = (data.get("channel") or {}).get("alternatives") or [{}]
            transcript = (alternatives[0].get("transcript") or "").strip()
            confidence = alternatives[0].get("confidence")
            if not transcript:
                continue

            if call.pending_barge_in and call.assistant_speaking and len(transcript) >= _MIN_BARGE_IN_CHARS:
                call.pending_barge_in = False
                await _handle_barge_in(call, websocket)

            if data.get("is_final") and data.get("speech_final"):
                call.pending_barge_in = False
                keep_going = await _process_transcript(call, transcript, confidence)
                if not keep_going:
                    break
    except websockets.ConnectionClosed:
        pass
    except Exception:
        logger.exception("Telephony STT receiver loop failed for stream_sid=%s", call.stream_sid)


async def _tts_receiver_loop(call: "_CallState", websocket: WebSocket) -> None:
    try:
        async for message in call.tts_ws:
            if call.closed:
                break
            if isinstance(message, (bytes, bytearray)):
                if call.drop_until_flushed:
                    continue
                for frame in call.chunker.push(bytes(message)):
                    await _send_media_frame(call, websocket, frame)
                continue

            try:
                control = json.loads(message)
            except (TypeError, ValueError):
                continue
            if control.get("type") != "Flushed":
                continue

            if call.drop_until_flushed:
                call.drop_until_flushed = False
                call.chunker.reset()
            else:
                trailing = call.chunker.flush()
                if trailing:
                    await _send_media_frame(call, websocket, trailing)
            call.assistant_speaking = False
    except websockets.ConnectionClosed:
        pass
    except Exception:
        logger.exception("Telephony TTS receiver loop failed for stream_sid=%s", call.stream_sid)


@router.websocket("/exotel/stream")
async def exotel_stream(websocket: WebSocket, db: Session = Depends(get_db)):
    if not _authorized(websocket):
        await websocket.close(code=4401, reason="Unauthorized")
        return
    if not settings.telephony_enabled:
        await websocket.close(code=4403, reason="Telephony is disabled for this business.")
        return

    await websocket.accept()

    call: _CallState | None = None
    stt_task: asyncio.Task | None = None
    tts_task: asyncio.Task | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (TypeError, ValueError):
                continue
            event = msg.get("event")

            if event == "connected":
                continue

            if event == "start":
                start = msg.get("start") or {}
                stream_sid = msg.get("stream_sid") or start.get("stream_sid")
                call_sid = start.get("call_sid") or stream_sid
                caller_phone = start.get("from") or "unknown"
                media_format = start.get("media_format") or {}
                sample_rate = int(media_format.get("sample_rate") or settings.telephony_sample_rate)

                cfg = ChatbotConfigService(db).get_or_create()
                if not cfg.voice_enabled:
                    await websocket.close(code=4403, reason="Voice calling is disabled for this business.")
                    return

                phone_sessions = PhoneCallSessionService(db)
                session, browser_id = phone_sessions.start_call(caller_phone, call_sid)

                try:
                    stt_ws = await open_stt_stream(sample_rate)
                    tts_ws = await open_tts_stream(cfg.voice_name, sample_rate)
                except TelephonyVoiceConfigError:
                    logger.exception("Telephony voice provider not configured")
                    await websocket.close(code=4503, reason="Voice provider not configured.")
                    return
                except Exception:
                    logger.exception("Failed to open Deepgram streams for stream_sid=%s", stream_sid)
                    await websocket.close(code=4502, reason="Couldn't start the voice provider.")
                    return

                call = _CallState(db, browser_id, session, sample_rate, cfg.barge_in_enabled)
                call.stream_sid = stream_sid
                call.stt_ws = stt_ws
                call.tts_ws = tts_ws

                stt_task = asyncio.create_task(_stt_receiver_loop(call, websocket))
                tts_task = asyncio.create_task(_tts_receiver_loop(call, websocket))
                continue

            if call is None:
                continue  # ignore anything before "start" — shouldn't happen per spec

            if event == "media":
                payload = (msg.get("media") or {}).get("payload")
                if payload and call.stt_ws is not None:
                    try:
                        await call.stt_ws.send(decode_media_payload(payload))
                    except websockets.ConnectionClosed:
                        pass

            elif event == "dtmf":
                digit = (msg.get("dtmf") or {}).get("digit")
                if digit == "0":
                    # Universal "press 0 for a human" convention.
                    async with call.db_lock:
                        events = await asyncio.to_thread(
                            lambda: list(
                                escalate_voice_call(
                                    call.db,
                                    call.session,
                                    "voice",
                                    "Customer pressed 0 to request a human during a phone call.",
                                )
                            )
                        )
                    await _speak_events(call, events)
                    break

            elif event == "mark":
                pass

            elif event == "stop":
                break

    except WebSocketDisconnect:
        logger.info("Exotel WebSocket disconnected")
    except Exception:
        logger.exception("Telephony call handling failed")
    finally:
        if call is not None:
            call.closed = True
            for ws in (call.stt_ws, call.tts_ws):
                if ws is not None:
                    try:
                        await ws.close()
                    except Exception:
                        pass
            for task in (stt_task, tts_task):
                if task is not None:
                    task.cancel()
            try:
                PhoneCallSessionService(db).end_call(call.session)
            except Exception:
                pass