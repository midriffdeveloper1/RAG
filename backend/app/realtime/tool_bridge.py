import logging
import re
from typing import Iterator

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.realtime.events import RealtimeEvent, RealtimeEventType
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORDS_PER_DELTA = 3

FRIENDLY_ERROR_MESSAGE = (
    "Sorry, something went wrong on my end. Could you say that again?"
)


def _chunk_for_delta(text: str) -> Iterator[str]:
    """Split finalized text into small pieces for progressive UI rendering.

    Note: the underlying LLM call in the tool-calling loop isn't itself
    token-streamed (the loop needs the complete tool_call payload before it
    can dispatch a tool), so this replays the *finished* answer in small
    pieces rather than true token-by-token generation. Sentence boundaries
    are preserved so the TTS layer (fed sentence-by-sentence by the
    frontend) can start speaking the first sentence while later ones are
    still "arriving" in the transcript — the actual latency win comes from
    that per-sentence TTS kickoff, not from this chunking itself.
    """
    for sentence in _SENTENCE_SPLIT.split(text.strip()):
        if not sentence:
            continue
        words = sentence.split(" ")
        for i in range(0, len(words), _WORDS_PER_DELTA):
            yield " ".join(words[i : i + _WORDS_PER_DELTA]) + " "


def stream_turn(
    db: Session,
    session: ChatSession,
    browser_id: str,
    transcript: str,
    customer_email: str | None = None,
) -> Iterator[RealtimeEvent]:
    """Run one voice turn through the exact same conversation layer as chat.

    Yields normalized events only — never raw provider payloads — so the
    frontend and any future speech provider stay decoupled from each other.
    """
    conversation = ConversationService(db)

    yield RealtimeEvent(type=RealtimeEventType.ASSISTANT_RESPONSE_STARTED)

    try:
        response = conversation.handle_turn(
            transcript,
            session,
            browser_id=browser_id,
            customer_email=customer_email,
            channel="voice",
        )
    except Exception:
        logger.exception("Voice turn failed for session_id=%s", session.id)
        yield RealtimeEvent(
            type=RealtimeEventType.ERROR,
            data={"message": FRIENDLY_ERROR_MESSAGE, "recoverable": True},
        )
        return

    if response.agent == "booking":
        # Coarse-grained: the booking agent may have run several tool calls
        # internally (list_services, check_available_slots, book_appointment,
        # ...). We surface that a tool ran without leaking which ones or
        # their arguments — that detail stays server-side.
        yield RealtimeEvent(type=RealtimeEventType.TOOL_CALL_STARTED, data={"agent": "booking"})
        yield RealtimeEvent(type=RealtimeEventType.TOOL_CALL_COMPLETED, data={"agent": "booking"})

    for delta in _chunk_for_delta(response.answer):
        yield RealtimeEvent(type=RealtimeEventType.ASSISTANT_TEXT_DELTA, data={"delta": delta})

    yield RealtimeEvent(
        type=RealtimeEventType.ASSISTANT_TEXT_COMPLETED,
        data={
            "text": response.answer,
            "needs_human": response.needs_human,
            "ticket_number": response.ticket_number,
            "agent": response.agent,
        },
    )
