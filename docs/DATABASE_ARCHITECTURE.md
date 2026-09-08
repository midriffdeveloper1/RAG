# Database Architecture

**Engine:** PostgreSQL, accessed via SQLAlchemy 2.0 (`declarative_base`, `Mapped`/`mapped_column` typed models). Migrations are managed with **Alembic**.

**Extension required:** [`pgvector`](https://github.com/pgvector/pgvector) — used for the knowledge-base embedding column. Enable it once per database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Primary keys:** almost every table uses a short random string ID (`app/core/ids.py::generate_id()`, `String(16)`) instead of an auto-increment integer or UUID — chosen for compact, URL-safe, non-guessable IDs.

---

## Entity overview

```
Business (singleton-per-tenant profile)
 ├── Service ──┬── staff_services (join) ──┬── Staff
 │             │                            └── Appointment.staff_id
 ├── OpeningHour
 ├── FAQ
 ├── Policy
 └── Holiday

Customer (identified by email)
 └── ChatSession.customer_id (nullable — anonymous until identified)
       └── ChatMessage (one row per turn, any channel)

Appointment (denormalized customer_name/email/phone — no FK to Customer)
 ├── service_id → Service
 └── staff_id   → Staff

Document
 └── DocumentChunk (RAG unit: text + pgvector embedding)

SupportTicket (human handoff; session_id references ChatSession.id but is NOT
               an FK — the session's messages are deleted/archived into the
               ticket's transcript_json when escalation happens)

ChatbotConfig — singleton row (one config for the whole business)
Admin — dashboard login
```

## Tables

### `admins`
Dashboard login. `email` (unique), `hashed_password` (bcrypt via `passlib`), `is_active`.

### `customers`
The identity anchor for the *customer-facing* side of the app. `email` is `NOT NULL` and unique — this is the primary identifier across chat, browser voice, and (best-effort, via Caller ID) phone calls. `name` and `phone` are optional and filled in during onboarding/profile updates.

### `chatbot_config`
**Singleton** (one row, created lazily by `ChatbotConfigService.get_or_create()`). Holds:
- Widget branding (`widget_title`, `tagline`, `avatar_emoji`, colors)
- Persona (`tone`, `persona_instructions`, `greeting_message`, `fallback_message`, `max_reply_words`, `temperature`)
- Feature toggles (`enable_appointment_booking`, `enable_knowledge_base`, `enable_email_gate`, `show_suggested_questions`)
- Voice settings (`voice_enabled`, `voice_name` — a Deepgram Aura voice id, `voice_greeting_message`, `barge_in_enabled`)
- `suggested_questions` — stored as a single `|`-delimited string, exposed as a list via a Python property

### `chat_sessions` / `chat_messages`
The universal conversation log — **used identically by text chat, browser voice, and phone calls.**

`chat_sessions`:
| Column | Notes |
|---|---|
| `browser_id` | Anonymous per-browser ID for chat/browser-voice, or a synthetic `phone:<digits>` id for phone calls (see `telephony_session.py`) |
| `customer_id` | Nullable — `NULL` until onboarding identifies the customer |
| `needs_human`, `escalation_reason`, `escalated_at`, `resolved_at`, `ticket_number` | Human-handoff state |
| `hidden_from_customer` | Set `true` once escalated — the session's messages move into the ticket transcript and the session itself is hidden from the customer's own history view |
| `awaiting_contact_info`, `unresolved_streak` | Support-agent bookkeeping (used to decide when to escalate) |
| `channel` | `"chat"` or `"voice"` (browser voice and phone calls both use `"voice"`) |
| `voice_session_id` | The active Deepgram voice session id (browser) or Exotel call/stream SID (phone), cleared when the call ends |

`chat_messages`:
| Column | Notes |
|---|---|
| `role` | `"user"` \| `"assistant"` |
| `agent` | Which agent produced an assistant reply: `"knowledge"` \| `"booking"` \| `"support"` \| `NULL` |
| `channel` | `"chat"` \| `"voice"` — which channel *this specific turn* came in on (a session can mix channels) |
| `message_type` | `"text"` \| `"voice_transcript"` \| `"assistant_text"` \| `"system"` \| `"tool"` |

### `support_tickets`
Created when a session escalates (`ChatSessionService.escalate()`). The session's message history at that point is copied into `transcript_json` (a JSON array) and the original `chat_messages` rows are deleted — the ticket becomes the source of truth going forward, with further turns appended via `SupportTicketService.append_message()`. `status` is `"open"` or `"resolved"`.

### `business`, `services`, `opening_hours`, `faqs`, `policies`, `holidays`
The structured knowledge the Knowledge Agent and Booking Agent draw on:
- **`business`** — name, description, address, phone, email (one row expected)
- **`services`** — name, description, price, duration; many-to-many with `staff` via `staff_services`
- **`opening_hours`** — one row per day of week, with `open_time`/`close_time`/`is_closed`
- **`faqs`** — question/answer/category, surfaced by the Knowledge Agent
- **`policies`** — title/content (cancellation policy, etc.)
- **`holidays`** — either a specific `date` or a recurring `day_of_week`, optionally a partial-day closure (`is_full_day`, `start_time`/`end_time`)

### `staff` / `staff_services`
`staff` — name, email, phone, `is_active`. `staff_services` is a plain many-to-many join table (`staff_id`, `service_id`) with no extra columns.

### `appointments`
Deliberately **denormalized** — `customer_name`/`customer_email`/`customer_phone` are stored directly on the appointment rather than via a `Customer` FK, so an appointment record is self-contained even if the customer profile is later edited or deleted. `service_id` and `staff_id` are real FKs. `status` is an enum: `booked` \| `cancelled` \| `completed`. `reference_code` is a short human-shareable booking reference.

### `documents` / `document_chunks`
RAG pipeline storage:
- **`documents`** — one row per uploaded file, with `status` (`pending` → `processing` → `completed`/`failed`), `content_hash` (dedup), `chunk_count`, `version`.
- **`document_chunks`** — one row per chunk: `text`, `source`, `chunk_index`, `version`, and an **`embedding` column of type `Vector(EMBEDDING_DIMENSION)`** (pgvector), used for cosine-similarity search at query time. `EMBEDDING_DIMENSION` defaults to `384` (matching `sentence-transformers/multi-qa-MiniLM-L6-cos-v1`). Deleting a `Document` cascades to its chunks (`ondelete="CASCADE"`).

---

## Migration history (Alembic, in order)

| Revision | File | What it does |
|---|---|---|
| `7875852c6d79` | `initial_migrate.py` | Base schema: admins, business, chatbot_config, customers, documents, staff, chat_sessions, faqs, holidays, etc. |
| `a66cbc205651` | `ticket.py` | Adds `resolved_at`, `ticket_number`, `hidden_from_customer` to `chat_sessions` |
| `981604cb394b` | `ticket_model.py` | Creates `support_tickets`; adds `awaiting_contact_info` to `chat_sessions` |
| `701843f3cf0e` | `document_chunk.py` | Creates `document_chunks` (pgvector column) |
| `ea36d4ff536e` | `voice_model.py` | Adds voice/channel columns: `chat_messages.channel`/`message_type`, `chat_sessions.channel`/`voice_session_id`, `chatbot_config.voice_enabled`/`voice_name`/`voice_greeting_message` |
| `e877e8567ad6` | `bargein.py` | Adds `chatbot_config.barge_in_enabled` |

**No new migration was needed for the latest work** (unclear-speech handling and Exotel telephony) — both reuse existing columns (`chat_sessions.voice_session_id` now also holds an Exotel call/stream SID for phone calls; `unresolved_streak`/`needs_human` drive escalation the same way for phone as for chat).

To apply migrations:
```bash
cd backend/backend
alembic upgrade head
```

To create a new migration after changing a model:
```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```
