# Voice & Telephony Architecture

> ## ⚠️ Current status — read this first
>
> This document describes the **designed** architecture for both channels. As of this snapshot:
>
> - **Browser voice call — live**, with one caveat: the unclear-speech/clarification logic described in §1 below (`is_unclear_transcript`, `clarification_turn`, `escalate_for_unclear_speech`) is **not actually called from `app/api/routes/voice.py`**. The live WS handler sends every final transcript straight to `stream_turn()`. Those functions exist in `app/realtime/tool_bridge.py` and are fully implemented — they're just currently only wired into the phone path below, which itself isn't reachable. So today, a mumbled/low-confidence answer on a browser call is *not* caught and clarified; it goes straight to an agent like any other transcript.
> - **Phone call (Exotel) — built, but not reachable.** `app/api/routes/telephony.py` is a complete implementation of everything in §2, but:
>   1. `telephony.router` is **not registered** in `app/main.py` — the `/api/v1/telephony/*` routes simply don't exist on a running server.
>   2. The settings `telephony.py` reads (`telephony_enabled`, `telephony_sample_rate`, `exotel_stream_username`, `exotel_stream_password`, `public_websocket_host`, `voice_min_confidence`, `voice_unclear_max_attempts`) are **not defined** on the `Settings` class in `app/core/config.py`, and aren't in `.env.example` either. Even after mounting the router, the first request would raise `AttributeError` on `settings.telephony_enabled`.
>
> To make phone calls actually work: add the missing fields to `Settings`, register `telephony.router` in `main.py` (alongside the other routers), and add the corresponding variables to `.env`/`.env.example`. To bring the browser channel in line with the design below, call `is_unclear_transcript()`/`clarification_turn()`/`escalate_for_unclear_speech()` from `voice.py`'s WS loop the same way `telephony.py` already does. Neither of these has been done in this snapshot — treat the rest of this document as the target design, not a description of what a fresh `uvicorn app.main:app` currently does end-to-end.

There are two real-time voice channels in this app, and both end up driving **the same agent pipeline** (`ConversationService` → `OrchestratorService` → Knowledge/Booking/Support agents) that text chat uses:

1. **Browser voice call** — a customer clicks "call" in the web widget and talks to the AI through their mic/speakers.
2. **Phone call (Exotel)** — a customer dials a real phone number and talks to the exact same AI.

Both are built around **Deepgram** for STT (speech-to-text) and TTS (text-to-speech), and both share the unclear-speech/clarification/escalation logic in `app/realtime/tool_bridge.py`. The difference is *where* the audio streaming happens.

---

## 1. Browser voice call

```
 Browser                              Backend                         Deepgram
 ───────                              ───────                         ────────
 VoiceCallWidget
   │ POST /voice/session ──────────────▶ mint ephemeral Deepgram token,
   │                                     create/reuse ChatSession
   │ ◀──── ws_url, deepgram token, stt/tts config ──┘
   │
   │──── mic (AudioWorklet, 16-bit PCM) ───────────────────────────▶ STT WS
   │◀─── interim + final transcripts ───────────────────────────────┘
   │
   │── on final transcript: send over control WS ──▶ /voice/ws/{session_id}
   │                                                    │
   │                                                    ▼
   │                                     unclear? ──yes──▶ clarification_turn()
   │                                        │no                 or
   │                                        ▼            escalate_for_unclear_speech()
   │                                  stream_turn()
   │                                        │
   │                                  ConversationService.handle_turn()
   │                                        │
   │                                  OrchestratorService → agent → reply text
   │                                        │
   │◀── RealtimeEvents (text deltas) ───────┘
   │
   │── reply text (sentence by sentence) ──────────────────────────▶ TTS WS
   │◀── streaming PCM audio ─────────────────────────────────────────┘
   │
   │── plays audio via a PCM playback queue (Web Audio API)
```

**Why the browser talks to Deepgram directly:** `POST /voice/session` returns a short-lived **ephemeral token** (`app/realtime/deepgram_provider.py`), so the client can open its own WebSocket straight to Deepgram's STT/TTS endpoints. This means:
- Raw audio never round-trips through the backend (lower latency)
- The backend's real Deepgram API key is never exposed to the browser
- The backend only ever sees **text** — final transcripts in, reply text out — over a separate lightweight "control" WebSocket (`/voice/ws/{session_id}`)

**Key frontend pieces:**
- `src/realtime/deepgramClient.js` — mic capture via `getUserMedia`/`AudioWorklet`, encodes to 16-bit PCM, streams to Deepgram STT; also manages the TTS playback queue (`PCMPlaybackQueue`) with support for interrupting mid-playback.
- `src/hooks/useVoiceSession.js` — orchestrates the whole call: session bootstrap, wiring the STT/TTS clients together, sending transcripts to the backend, handling barge-in, and driving the call state machine (`idle → connecting → connected → listening → processing → speaking → ended`).
- `src/components/Chat/VoiceCallWidget.jsx` — the UI (mic button, call state indicator, waveform).

**Key backend pieces:**
- `app/api/routes/voice.py` — `POST /voice/session` (bootstrap) and `WS /voice/ws/{session_id}` (control channel for transcripts ↔ reply text).
- `app/realtime/session.py` — `VoiceSessionService`, maps a browser call to a `ChatSession` (`channel="voice"`).
- `app/realtime/tool_bridge.py` — turns one agent turn into a stream of `RealtimeEvent`s (`assistant.response.started`, `.text.delta`, `.text.completed`, etc.) that the control WS relays to the client.

### End-of-speech detection
Deepgram's `endpointing=300` + `vad_events=true` params (see `stt_stream_config()`) mean Deepgram itself decides when the caller has stopped talking (`speech_final: true` on the final `Results` message) — the client doesn't need its own silence-detection heuristic.

### Barge-in (interrupting the AI)
When Deepgram emits a `SpeechStarted` VAD event while the assistant is speaking, and the *next* interim transcript has real content (not just noise — see `MIN_BARGE_IN_CHARS` in `useVoiceSession.js`), the client:
1. Stops/clears its local audio playback queue immediately
2. Ignores any further audio that was already in flight for the interrupted reply

### Unclear speech & confirmation safety (designed; not yet wired into the browser WS handler — see status note at the top of this doc)
- Every final transcript from Deepgram carries a **confidence score**. `tool_bridge.is_unclear_transcript()` checks that score (default threshold `0.55`, `VOICE_MIN_CONFIDENCE`) and also filters out filler-only "transcripts" (um/uh/hmm).
- An unclear transcript **never reaches an agent**. Instead `clarification_turn()` asks the caller to repeat themselves (varying the phrasing across attempts) and the attempt is *not* held against them once they get through clearly.
- After `VOICE_UNCLEAR_MAX_ATTEMPTS` (default `2`) consecutive unclear attempts, `escalate_for_unclear_speech()` hands the call off to a human via the normal ticketing system instead of continuing to guess.
- Separately, the **Booking Agent** itself (`app/services/agents/booking_agent.py`) never books/reschedules/cancels anything without restating the details and getting an explicit "yes" — this holds regardless of channel, so even a *clear but wrong* transcript can't silently trigger an irreversible action.

---

## 2. Phone calls via Exotel

There's no browser in a phone call, so the shape changes: **the backend itself** bridges audio between the phone network (via Exotel) and Deepgram.

```
 Caller's phone          Exotel (PSTN)              Backend                    Deepgram
 ─────────────           ─────────────               ───────                    ────────
      │  dials ExoPhone ──▶
      │                       WS "start" event ────────▶ /telephony/exotel/stream
      │                       (from, call_sid, sample_rate)
      │                                                     │
      │                                             look up/create ChatSession
      │                                             by caller phone number
      │                                             (auto-identify if a
      │                                              Customer.phone matches)
      │                                                     │
      │                                             open STT + TTS connections ──▶ (server-side, real API key)
      │                       WS "media" (base64 PCM) ──▶ forward raw PCM ───────▶ STT WS
      │                                                                          ◀── interim/final transcripts
      │                                                     │
      │                                          same is_unclear_transcript() /
      │                                          clarification / stream_turn()
      │                                          pipeline as browser voice
      │                                                     │
      │                                          reply text, sentence by sentence ──▶ TTS WS
      │                                                                          ◀── PCM audio
      │                       WS "media" (base64 PCM) ◀── re-chunk to Exotel's ───────┘
      │◀── hears reply ──────  frame-size rules (exotel_codec.py)
      │
      │  (barge-in: WS "clear" event) ◀── caller starts talking while assistant is speaking
      │  (press 0)  ──▶  WS "dtmf" event ──▶ immediate human handoff
```

### Why Exotel, and what it provides
[Exotel's AgentStream (Voicebot Applet)](https://developer.exotel.com/docs/agentstream/stream-voicebot-applet) gives a bidirectional WebSocket per call: Exotel sends caller audio as base64-encoded raw 16-bit PCM inside JSON `media` events, and expects the same format back. It also sends `dtmf` (keypad presses), `mark` (playback-finished notifications), and `stop` (call ended) events. It was chosen over Plivo/Twilio for this project mainly because it's India-first (matching this app's business context) and has a clearly documented, bidirectional streaming protocol well-suited to a conversational agent.

### New backend modules for this
| File | Role |
|---|---|
| `app/realtime/exotel_codec.py` | Wire-format helpers: base64 encode/decode, `build_media_message`/`build_clear_message`/`build_mark_message`, and `ExotelAudioChunker` — buffers outgoing TTS audio into frames that satisfy Exotel's size rule (multiple of 320 bytes, 3.2–100 KB) |
| `app/realtime/telephony_bridge.py` | Opens **server-side** Deepgram STT/TTS WebSocket connections using the real API key (no ephemeral token needed — Exotel never talks to Deepgram directly) |
| `app/realtime/telephony_session.py` | `PhoneCallSessionService` — maps a caller's phone number to a `ChatSession` (synthetic `browser_id` like `phone:919876543210`), and auto-identifies a returning caller by matching Caller ID against `Customer.phone` (skipping the "please say your email" onboarding a phone caller would otherwise have to do) |
| `app/api/routes/telephony.py` | The actual call handler — implements the Exotel event protocol and drives everything else |

### Call lifecycle (`app/api/routes/telephony.py`)
1. **`start`** — extract `from`/`call_sid`/`media_format.sample_rate`; look up/create the `ChatSession`; open Deepgram STT + TTS connections at the call's sample rate (default 8kHz — matches Exotel's PSTN-quality default, so **no audio resampling is needed on either leg**); spawn two background tasks:
   - `_stt_receiver_loop` — reads Deepgram STT messages, detects `SpeechStarted` (for barge-in) and final transcripts (which get run through the exact same `is_unclear_transcript`/`clarification_turn`/`stream_turn` functions the browser flow uses)
   - `_tts_receiver_loop` — reads audio back from Deepgram TTS, re-chunks it via `ExotelAudioChunker`, and forwards it to Exotel as `media` events
2. **`media`** — forward the caller's raw PCM straight into the Deepgram STT socket.
3. **`dtmf`** — pressing `0` triggers an immediate human handoff (`escalate_voice_call()`), mirroring the universal "press 0 for an operator" convention.
4. **`stop`** (or the caller hanging up) — close both Deepgram connections, cancel the background tasks, clear `ChatSession.voice_session_id`.

### Barge-in over the phone
There's no local audio queue to interrupt (unlike the browser). Instead, on a confirmed barge-in the handler:
1. Sends `{"event": "clear", "stream_sid": ...}` to Exotel — this tells Exotel to drop whatever's queued/playing right now.
2. Sets a `drop_until_flushed` flag so any audio Deepgram TTS was still generating for the interrupted reply is discarded instead of sent, until Deepgram signals that utterance is fully flushed.

### Unclear speech, confirmation, and human handoff on phone calls
Exactly the same rules as browser voice apply, because it's the same `tool_bridge.py` functions — a phone caller who mumbles gets asked to repeat themselves, not guessed at; repeated failures escalate; and the Booking Agent still requires an explicit "yes" before booking/rescheduling/cancelling anything. Phone calls additionally get the DTMF `0`-for-human shortcut.

### Configuration
```dotenv
TELEPHONY_ENABLED=true
TELEPHONY_SAMPLE_RATE=8000
EXOTEL_STREAM_USERNAME=...      # optional Basic Auth for the inbound WS
EXOTEL_STREAM_PASSWORD=...
PUBLIC_WEBSOCKET_HOST=your-domain.example
```
Point Exotel's Voicebot Applet at `wss://<host>/api/v1/telephony/exotel/stream` (static), or use the dynamic-URL option against `POST /api/v1/telephony/exotel/stream-url`.

> None of the five variables above currently have a matching field on `Settings` (`app/core/config.py`) or an entry in `.env.example` — `telephony.py` reads `settings.telephony_enabled`, `settings.telephony_sample_rate`, `settings.exotel_stream_username`, `settings.exotel_stream_password`, and `settings.public_websocket_host`, none of which exist yet. Add them to the `Settings` class (with sensible defaults, e.g. `telephony_enabled: bool = False`) before setting these in `.env` — otherwise they're silently ignored by `pydantic-settings` (`extra="ignore"`) and the route will fail with `AttributeError` the moment it's hit.

### Known limitations / things to verify against a live account
- **The router isn't registered yet.** `app/main.py` includes every other router (`health`, `auth`, `documents`, `business_documents`, `voice`, etc.) but not `telephony` — add `app.include_router(telephony.router, prefix=settings.api_v1_prefix)` before any of this is reachable.
- This integration was built directly against Exotel's published AgentStream protocol docs but has **not been tested against a live Exotel account** in this environment (no network access) — verify chunk-size tolerances and auth behavior against a real call before going to production.
- Spoken email addresses ("john at gmail dot com") rely on Deepgram's `smart_format` normalization to become `john@gmail.com` for onboarding — this is a shared limitation with the browser voice channel, not something new to telephony.
- Outbound calling (the AI calling a customer) is not implemented — only inbound calls to the business's ExoPhone.
