"""Helpers for Exotel's AgentStream Voicebot Applet WebSocket protocol.

Audio is raw PCM, 16-bit little-endian, mono, base64-encoded inside JSON
"media" events (not raw binary WS frames like Deepgram uses). Outgoing
audio chunks must be a multiple of 320 bytes and between 3.2 KB and 100 KB —
non-compliant sizes create gaps/distortion in playback on Exotel's side.
See: https://developer.exotel.com/docs/agentstream/stream-voicebot-applet
"""

import base64

EXOTEL_FRAME_MULTIPLE = 320
EXOTEL_MIN_FRAME_BYTES = 3200
EXOTEL_MAX_FRAME_BYTES = 100_000
# A safe, comfortably mid-range frame size — a multiple of 320 and well
# within [min, max] regardless of which sample rate (8k/16k/24k) is used.
DEFAULT_OUTBOUND_FRAME_BYTES = 3200


def decode_media_payload(payload_b64: str) -> bytes:
    return base64.b64decode(payload_b64)


def encode_media_payload(pcm_bytes: bytes) -> str:
    return base64.b64encode(pcm_bytes).decode("ascii")


def build_media_message(stream_sid: str, pcm_bytes: bytes) -> dict:
    return {
        "event": "media",
        "stream_sid": stream_sid,
        "media": {"payload": encode_media_payload(pcm_bytes)},
    }


def build_mark_message(stream_sid: str, name: str) -> dict:
    return {"event": "mark", "stream_sid": stream_sid, "mark": {"name": name}}


def build_clear_message(stream_sid: str) -> dict:
    """Tells Exotel to drop whatever queued/unplayed audio it has — this is
    how barge-in is implemented for phone calls (the phone-side analogue of
    the browser's local PCMPlaybackQueue.interrupt())."""
    return {"event": "clear", "stream_sid": stream_sid}


class ExotelAudioChunker:
    """Buffers raw PCM16LE audio from Deepgram TTS and yields Exotel-
    compliant frames as soon as enough has accumulated."""

    def __init__(self, frame_bytes: int = DEFAULT_OUTBOUND_FRAME_BYTES) -> None:
        if frame_bytes % EXOTEL_FRAME_MULTIPLE != 0:
            raise ValueError("frame_bytes must be a multiple of 320")
        if not (EXOTEL_MIN_FRAME_BYTES <= frame_bytes <= EXOTEL_MAX_FRAME_BYTES):
            raise ValueError("frame_bytes must be within Exotel's [3200, 100000] range")
        self.frame_bytes = frame_bytes
        self._buffer = bytearray()

    def push(self, pcm_bytes: bytes) -> list[bytes]:
        self._buffer.extend(pcm_bytes)
        frames = []
        while len(self._buffer) >= self.frame_bytes:
            frames.append(bytes(self._buffer[: self.frame_bytes]))
            del self._buffer[: self.frame_bytes]
        return frames

    def flush(self) -> bytes | None:
        """Call at the end of an utterance — pads any leftover partial
        frame up to a 320-byte multiple with silence, so the last few
        words of a reply aren't dropped just because they didn't fill a
        full frame."""
        if not self._buffer:
            return None
        remainder = len(self._buffer) % EXOTEL_FRAME_MULTIPLE
        if remainder:
            self._buffer.extend(b"\x00" * (EXOTEL_FRAME_MULTIPLE - remainder))
        frame = bytes(self._buffer)
        self._buffer.clear()
        return frame

    def reset(self) -> None:
        """Discard whatever's buffered without sending it — used on
        barge-in, mirroring the browser's playback.interrupt()."""
        self._buffer.clear()
