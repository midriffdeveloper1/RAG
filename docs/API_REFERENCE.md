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

> **⚠️ Not currently live.** `app/api/routes/telephony.py` implements both endpoints below, but the router is **not registered in `app/main.py`**, so neither path actually exists on a running server right now, and the `Settings` fields it depends on (`telephony_enabled`, `exotel_stream_username`/`password`, `public_websocket_host`, etc.) aren't defined yet either. Documented here as designed; see `VOICE_AND_TELEPHONY.md` for the full status note.

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
| POST | `/admin/documents/upload` | Upload a PDF/DOCX — enqueues a Celery task for extraction, chunking, embedding |
| GET | `/admin/documents` | List uploaded documents + processing status |
| POST | `/admin/documents/{document_id}/reindex` | Re-run extraction/embedding for a document |
| DELETE | `/admin/documents/{document_id}` | Delete a document and its chunks |

## Admin — Business Documents (invoices, receipts, contracts, etc.)

All under `/admin/business-documents`. See `BUSINESS_DOCUMENT_EXTRACTION.md` for the full pipeline design.

| Method | Path | Notes |
|---|---|---|
| POST | `/admin/business-documents/upload` | Multi-file upload (`files: list[UploadFile]`, ≤15/batch). Optional `?document_type=invoice` hint. Enqueues a Celery task per file; returns one result per file, including files that failed to even save. |
| GET | `/admin/business-documents` | Paginated list, filterable by `document_type` and `status` |
| GET | `/admin/business-documents/summary` | Per-type counts (total / needs review / failed) for a dashboard |
| GET | `/admin/business-documents/{id}` | Full record incl. extracted data, confidence, validation |
| PATCH | `/admin/business-documents/{id}` | `{ "fields": {...} }` — manual correction of one or more fields |
| POST | `/admin/business-documents/{id}/reprocess` | Re-run extraction against the stored file |
| DELETE | `/admin/business-documents/{id}` | Delete the record and its file |

## Admin — AI Data Analyst

Natural-language questions over the business document tables. All routes require
an authenticated admin and are scoped by `admin_id`. See `AI_DATA_ANALYST.md`.

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/analyst/scope` | Document types in scope + suggested starter questions |
| POST | `/admin/analyst/ask` | `{question, session_id?}`. Omit `session_id` to start a thread. Returns the answer plus `sql`, `result_columns`/`result_rows`, and an optional `chart`. `status` is `ok` \| `out_of_scope` \| `needs_clarification` \| `blocked` \| `error`. **503** if `OPENAI_API_KEY` isn't set. |
| GET | `/admin/analyst/sessions` | Paginated thread list |
| GET | `/admin/analyst/sessions/{session_id}` | Full thread, with each turn's stored result snapshot |
| DELETE | `/admin/analyst/sessions/{session_id}` | Delete a thread |

Only `SELECT` reaches the database: generated SQL is validated against a table
allowlist and executed on a dedicated `READ ONLY` connection.

## Admin — Notifications

All under `/admin/notifications`.

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/notifications` | Paginated list; `?unread_only=true` to filter |
| GET | `/admin/notifications/unread-count` | Unread count for the bell badge |
| POST | `/admin/notifications/{notification_id}/read` | Mark one notification read |
| POST | `/admin/notifications/read-all` | Mark all notifications read |
| DELETE | `/admin/notifications/{notification_id}` | Delete a notification |

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
