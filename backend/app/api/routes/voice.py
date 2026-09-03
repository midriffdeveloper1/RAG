import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.realtime.deepgram_provider import DeepgramConfigError, get_voice_provider
from app.realtime.events import RealtimeEvent, RealtimeEventType
from app.realtime.session import VoiceSessionService
from app.realtime.tool_bridge import stream_turn
from app.schemas.voice import DeepgramStreamConfig, VoiceSessionRequest, VoiceSessionResponse
from app.services.chatbot_config_service import ChatbotConfigService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])
settings = get_settings()


@router.post("/session", response_model=VoiceSessionResponse)
def create_voice_session(payload: VoiceSessionRequest, db: Session = Depends(get_db)):
    config = ChatbotConfigService(db).get_or_create()
    if not config.voice_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Voice calling is disabled for this business."
        )

    try:
        provider = get_voice_provider()
        token = provider.create_ephemeral_token(settings.voice_token_ttl_seconds)
    except DeepgramConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception:
        logger.exception("Failed to create voice session")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't start a voice session right now. Please try again.",
        )

    voice_sessions = VoiceSessionService(db)
    session, voice_session_id = voice_sessions.start_call(payload.browser_id, payload.session_id)

    stt = provider.stt_stream_config()
    tts = provider.tts_stream_config(config.voice_name)

    return VoiceSessionResponse(
        conversation_id=session.id,
        voice_session_id=voice_session_id,
        ws_url=f"{settings.api_v1_prefix}/voice/ws/{session.id}",
        deepgram_token=token["token"],
        deepgram_token_expires_in_seconds=token["expires_in_seconds"],
        stt=DeepgramStreamConfig(**stt),
        tts=DeepgramStreamConfig(**tts),
    )


@router.websocket("/ws/{session_id}")
async def voice_events_ws(
    websocket: WebSocket,
    session_id: str,
    voice_session_id: str,
    browser_id: str,
    db: Session = Depends(get_db),
):

    voice_sessions = VoiceSessionService(db)
    session = voice_sessions.get_active_call(session_id, voice_session_id)
    if session is None or session.browser_id != browser_id:
        await websocket.close(code=4404, reason="Voice session not found")
        return

    await websocket.accept()
    await websocket.send_json(
        RealtimeEvent(
            type=RealtimeEventType.SESSION_CREATED, data={"conversation_id": session.id}
        ).to_wire()
    )
    await websocket.send_json(RealtimeEvent(type=RealtimeEventType.CALL_STARTED).to_wire())

    try:
        while True:
            raw = await websocket.receive_json()
            event_type = raw.get("type")

            if event_type == RealtimeEventType.USER_TRANSCRIPT_FINAL.value:
                transcript = (raw.get("data") or {}).get("text", "").strip()
                if not transcript:
                    continue
                customer_email = (raw.get("data") or {}).get("customer_email")
                for event in stream_turn(db, session, browser_id, transcript, customer_email):
                    await websocket.send_json(event.to_wire())

            elif event_type == "call.end":
                break

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected for session_id=%s", session_id)
    except (ValidationError, ValueError):
        logger.exception("Malformed voice event for session_id=%s", session_id)
        await websocket.send_json(
            RealtimeEvent(
                type=RealtimeEventType.ERROR,
                data={"message": "That didn't come through right — please try again.", "recoverable": True},
            ).to_wire()
        )
    finally:
        voice_sessions.end_call(session)
        try:
            await websocket.send_json(RealtimeEvent(type=RealtimeEventType.CALL_ENDED).to_wire())
        except Exception:
            pass
