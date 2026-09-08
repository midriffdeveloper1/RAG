# API Reference

All routes are mounted under `API_V1_PREFIX` (default `/api/v1`). Interactive docs are always available at `/docs` (Swagger) and `/redoc` when the backend is running.

**Auth:** every `/admin/*` route requires a `Authorization: Bearer <token>` header, obtained from `POST /auth/login`. Customer-facing routes use `browser_id` (an anonymous per-browser id) + `customer_email` for identification instead of a password.

---

## Health

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check |

## Admin Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/login` | Returns a JWT for the admin dashboard |
| GET | `/auth/me` | Current admin profile (requires auth) |

## Public / Customer-facing

| Method | Path | Notes |
|---|---|---|
| GET | `/chatbot-config` | Public widget config (branding, persona hints, feature toggles) |
| POST | `/customers/identify` | Identify/create a customer by email (used by onboarding) |
| POST | `/chat` | Send one text chat turn; returns the assistant's reply, `session_id`, escalation info |
| GET | `/chat/sessions` | List a customer's past sessions (`browser_id` + `customer_email`) |
| GET | `/chat/sessions/{session_id}` | Full message history for one session |
| DELETE | `/chat/sessions/{session_id}` | Delete a session |
| POST | `/chat/sessions/{session_id}/discard` | Best-effort cleanup on tab close (`sendBeacon`) |
| GET | `/support/tickets/{ticket_number}` | Look up a support ticket's status by its public ticket number |

## Voice (browser real-time call)

| Method | Path | Notes |
|---|---|---|
| POST | `/voice/session` | Bootstraps a call: mints a Deepgram ephemeral token, returns STT/TTS stream config + a control WS URL. 403 if voice is disabled in Chatbot Config; 503 if Deepgram isn't configured |
| WS | `/voice/ws/{session_id}` | Control channel: client sends final transcripts (`user.transcript.final`, with `confidence`), server streams back `RealtimeEvent`s (`assistant.response.started`, `.text.delta`, `.text.completed`, `user.transcript.unclear`, `error`, etc.) |

See `VOICE_AND_TELEPHONY.md` for the full event flow.

## Telephony (Exotel phone calls)

| Method | Path | Notes |
|---|---|---|
| POST | `/telephony/exotel/stream-url` | Optional: returns the `wss://` URL to use, for Exotel's dynamic-URL applet option |
| WS | `/telephony/exotel/stream` | The call itself — implements Exotel's AgentStream Voicebot Applet protocol (`connected`/`start`/`media`/`dtmf`/`mark`/`stop` events) |

See `VOICE_AND_TELEPHONY.md` for the full protocol and call lifecycle.

## Admin — Business & Catalog

| Method | Path | Notes |
|---|---|---|
| GET / PUT | `/admin/business` | Business profile (name, description, address, contact, opening hours) |
| GET / POST | `/admin/business/faqs` | FAQ list / create |
| PATCH / DELETE | `/admin/business/faqs/{faq_id}` | Update / delete one FAQ |
| GET / POST | `/admin/business/policies` | Policy list / create |
| PATCH / DELETE | `/admin/business/policies/{policy_id}` | Update / delete one policy |
| GET / POST | `/admin/services` | Service list / create |
| PATCH / DELETE | `/admin/services/{service_id}` | Update / delete a service |
| GET / POST | `/admin/staff` | Staff list / create |
| PATCH / DELETE | `/admin/staff/{staff_id}` | Update / delete staff (incl. service assignments) |
| GET / POST | `/admin/holidays` | Holiday list / create |
| PATCH / DELETE | `/admin/holidays/{holiday_id}` | Update / delete a holiday |

## Admin — Knowledge Base

| Method | Path | Notes |
|---|---|---|
| POST | `/admin/documents/upload` | Upload a PDF/DOCX — triggers extraction, chunking, embedding |
| GET | `/admin/documents` | List uploaded documents + processing status |
| POST | `/admin/documents/{document_id}/reindex` | Re-run extraction/embedding for a document |
| DELETE | `/admin/documents/{document_id}` | Delete a document and its chunks |

## Admin — Chatbot Configuration

| Method | Path | Notes |
|---|---|---|
| GET / PUT | `/admin/chatbot-config` | Persona, branding, feature toggles, voice settings |
| GET | `/admin/chatbot-config/preview-prompt` | See the system prompt the config currently produces |

## Admin — Appointments

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/appointments` | Paginated list (filterable) |
| POST | `/admin/appointments` | Create an appointment manually |
| GET | `/admin/appointments/{appointment_id}` | Detail |
| PATCH | `/admin/appointments/{appointment_id}` | Update (e.g. status, notes) |
| DELETE | `/admin/appointments/{appointment_id}` | Delete |

## Admin — Customers

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/customers` | Paginated, searchable list |
| POST | `/admin/customers` | Create a customer record |
| PATCH | `/admin/customers/{customer_id}` | Update |
| DELETE | `/admin/customers/{customer_id}` | Delete |

## Admin — Conversations (chat / voice / phone)

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/conversations` | Paginated list, filterable to `needs_human` only |
| GET | `/admin/conversations/{session_id}` | Full transcript |
| POST | `/admin/conversations/{session_id}/resolve` | Mark resolved (and resolve the linked ticket, if any) |
| POST | `/admin/conversations/{session_id}/reopen` | Reopen |
| DELETE | `/admin/conversations/{session_id}` | Delete |

## Admin — Analytics

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/analytics/overview` | Dashboard summary numbers (documents, services, staff, customers, appointments by status, chat session counts, escalation count) |

---

## Realtime event types (voice/telephony)

Defined in `app/realtime/events.py`, sent as `{"type": "...", "data": {...}, "timestamp": "..."}` over the voice control WebSocket (phone calls don't expose these directly — they're consumed server-side and turned into spoken audio):

| Type | Meaning |
|---|---|
| `session.created`, `call.started`, `call.ended` | Call lifecycle |
| `user.speech.started` / `user.speech.stopped` | VAD events |
| `user.transcript.partial` / `user.transcript.final` | STT output |
| `user.transcript.unclear` | The final transcript was too low-confidence/unclear to act on — a clarification is about to be spoken instead |
| `assistant.response.started` / `.text.delta` / `.text.completed` | Streamed assistant reply |
| `assistant.audio.started` / `.audio.completed` | TTS playback lifecycle (browser only) |
| `tool.call.started` / `.completed` | A booking-agent tool call happened this turn |
| `confirmation.required` | Reserved for explicit confirmation prompts |
| `error` | Something failed; `data.recoverable` indicates whether the call can continue |
