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

Notification — flat table, admin notification bell (no FK; related_id is a
               loose reference to whatever triggered it)

BusinessDocumentUpload (one row per uploaded business document — file
                        metadata, classification, confidence, validation)
 ├── invoice          → Invoice ──┬── invoice_line_items
 ├── receipt          → Receipt ──┴── receipt_items
 ├── purchase_order   → PurchaseOrder ── purchase_order_line_items
 ├── resume           → Resume ──┬── resume_education
 │                                └── resume_experience
 ├── expense_report   → ExpenseReport ── expense_report_items
 ├── application_form → ApplicationForm
 └── contract         → Contract ── contract_signatories
   (each is a 1:1 relationship, keyed on upload_id; only the row matching
    the upload's classified document_type actually gets created)

BusinessDocument (legacy) — the original single-table design
               (business_documents, with a JSON extracted_data column).
               Superseded by BusinessDocumentUpload + the per-type tables
               above. Still defined as a model/table but not part of the
               live code path — see the note in "Tables" below.

AnalystSession ──< AnalystMessage
   (admin-only AI SQL analyst threads; AnalystSession.admin_id -> Admin.id)

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

### `notifications`
Flat table backing the admin notification bell (`app/models/notification.py`). `type` is an enum (`business_document_completed`, `business_document_needs_review`, `business_document_low_confidence`, `business_document_failed`, `kb_document_completed`, `kb_document_failed`, `appointment_booked`, `appointment_cancelled`, `appointment_rescheduled`, `generic`); `severity` is `info`/`success`/`warning`/`error`. `link` and `related_id` are loose, unenforced references back to whatever triggered the notification (no FK). `is_read`/`created_at` drive the bell's unread count and ordering.

### `analyst_sessions` / `analyst_messages`
Persistence for the admin-only AI SQL & Data Analyst agent (see
`AI_DATA_ANALYST.md`).

- **`analyst_sessions`** — one conversation thread, owned by an admin
  (`admin_id`, FK to `admins.id`, `ondelete="CASCADE"`). `title` is the first
  question asked.
- **`analyst_messages`** — one row per turn. User turns store just `content`.
  Assistant turns additionally store `status`, the generated `sql` and `intent`,
  and a **snapshot of the result** (`result_columns`, `result_rows`, `row_count`,
  `truncated`, `duration_ms`, `chart`). The snapshot means reopening a thread
  shows what the admin originally saw rather than re-running the query against
  data that may have changed; storing the `sql` also lets follow-up questions
  ("break that down by month") extend the real previous query.

These are deliberately separate from `chat_sessions`/`chat_messages`: that pair
models a *customer* support conversation (`browser_id`, `customer_id`,
escalation, `ticket_number`) and is surfaced in the admin Conversations page.

### `business_document_uploads` and the per-type tables
The business-document-intelligence pipeline (see `BUSINESS_DOCUMENT_EXTRACTION.md`) uses a **normalized, per-document-type schema**, not one generic table:

- **`business_document_uploads`** (`BusinessDocumentUpload`) — one row per uploaded file: file metadata (`original_filename`, `stored_filename`, `file_path`, `file_type`, `file_size_bytes`, `content_hash` for dedup), classification (`document_type`, `type_confidence`, `requested_document_type`), processing `status` (`pending → processing → completed/needs_review/failed`), and extraction/validation metadata that isn't business data itself (`field_confidence`, `confidence_score`, `is_valid`, `validation_errors`, `missing_fields`, `reviewed`).
- One child table per document type, each with a 1:1 relationship back to its `BusinessDocumentUpload` via `upload_id` (`ondelete="CASCADE"`), holding the actual extracted business fields:
  | Document type | Parent table | Line-item child table(s) |
  |---|---|---|
  | Invoice | `invoices` | `invoice_line_items` |
  | Receipt | `receipts` | `receipt_items` |
  | Purchase order | `purchase_orders` | `purchase_order_line_items` |
  | Resume | `resumes` | `resume_education`, `resume_experience` |
  | Expense report | `expense_reports` | `expense_report_items` |
  | Application form | `application_forms` | — (flat + a JSON `additional_fields` catch-all) |
  | Contract | `contracts` | `contract_signatories` |

  Only the child row matching the upload's classified `document_type` is ever created for a given upload. `app/services/business_documents/persistence.py` reads/writes these tables generically, driven by the field schema in `app/services/business_documents/field_schemas.py`.

> **⚠️ Superseded model, still in the tree:** `app/models/business_document.py` defines an earlier, single-table design (`business_documents`, with `extracted_data`/`field_confidence`/etc. stored as JSON blobs) that the code has since moved away from. `alembic/env.py` and the current `service.py`/`extraction.py`/routes all use `BusinessDocumentUpload` (the normalized design above) — the old `business_documents` table isn't written to by any live code path. A few lower-level helper modules (`scoring.py`, `validation.py`, `field_schemas.py`) still import their `BusinessDocumentType` enum from the old `business_document.py` file rather than from `business_documents/upload.py`; the two enums currently have identical values, so this works, but it's a latent trap if they ever drift apart.

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
| `5266269807d3` | `staff_modal.py` | Staff-related schema adjustments (supports the staff admin modal) |
| `65c81363ab75` | `staff_modal.py` | Further staff-related schema adjustments |
| `62d8b09cd61e` | `business_doc.py` | Business-document schema (part 1) |
| `5b541868256e` | `business_doc.py` | Business-document schema (part 2) |
| `c3f7a91b4de2` | `analyst_sessions.py` | Creates `analyst_sessions` + `analyst_messages` for the AI data analyst — current head |

To apply migrations:
```bash
cd backend
alembic upgrade head
```

To create a new migration after changing a model:
```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Note that `alembic/env.py` imports models explicitly (not via `app/models/__init__.py`, which itself does **not** import `Notification`, `BusinessDocument`, or anything under `business_documents/`) — if you add a new model, make sure it's imported in `alembic/env.py` (or added to `app/models/__init__.py` and re-exported there) or `--autogenerate` won't see it.
