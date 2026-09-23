# AI Support Agent

A full-stack, multi-tenant-style **AI customer support platform** for a service business (generic enough for any appointment-based business). It combines a **RAG knowledge base**, a **multi-agent LLM orchestrator**, **appointment booking**, a **real-time voice agent**, a **business-document intelligence pipeline** (invoices, receipts, contracts, resumes, etc.), and an **admin notifications system** — reachable from a browser, and (currently mid-migration back to working order — see Status) from a real phone call.

This README is the entry point. See the other docs in this folder for details:

| Doc | Covers |
|---|---|
| [`PROJECT_STRUCTURE.md`](./docs/PROJECT_STRUCTURE.md) | Folder-by-folder tour of both the backend and frontend |
| [`TECH_STACK.md`](./TECH_STACK.md) | Every major library/service used and why |
| [`DATABASE_ARCHITECTURE.md`](./DATABASE_ARCHITECTURE.md) | Tables, relationships, migrations |
| [`HOW_TO_RUN.md`](./HOW_TO_RUN.md) | Local setup, env vars, running the API, worker, and frontend |
| [`VOICE_AND_TELEPHONY.md`](./VOICE_AND_TELEPHONY.md) | The real-time voice agent (browser) and phone-call (Exotel) integration in depth — **includes a current-status caveat, read it before assuming phone calls work** |
| [`BUSINESS_DOCUMENT_EXTRACTION.md`](./BUSINESS_DOCUMENT_EXTRACTION.md) | The invoice/receipt/PO/resume/expense-report/application-form/contract extraction pipeline |
| [`AI_DATA_ANALYST.md`](./AI_DATA_ANALYST.md) | The admin-only natural-language SQL & data analyst agent, and how destructive SQL is prevented |
| [`CELERY_SETUP.md`](./CELERY_SETUP.md) | Background job processing (Celery + Redis) — required for uploads and emails to actually complete |
| [`API_REFERENCE.md`](./API_REFERENCE.md) | Every REST/WebSocket endpoint, grouped by area |

---

## What this project does

A business admin configures their services, staff, opening hours, and knowledge base (uploaded documents + FAQs/policies) through an admin dashboard. Customers then interact with an AI assistant through:

- **A text chat widget** embedded on the business's site
- **A real-time voice call** from the browser (talk to the AI like a phone call, no push-to-talk)
- **A real phone call** to a business phone number (via Exotel) — the code for this exists and reuses the same agent pipeline, but it is **not currently wired up to run** (see Status)

Separately, the admin can also feed the platform's own paperwork — invoices, receipts, purchase orders, resumes, expense reports, application forms, contracts — through a document-intelligence pipeline that turns scans/PDFs into structured, editable records. This is independent of the customer-facing chatbot.

Under the hood, every customer-facing channel (chat / browser voice / phone) is driven by the same **multi-agent orchestrator**, which:

1. Identifies the customer (by email for chat/browser voice, automatically by Caller ID for phone when possible)
2. Routes each message to one of three specialist agents:
   - **Knowledge Agent** — answers questions using RAG over uploaded documents + FAQs/policies/business info
   - **Booking Agent** — books, reschedules, or cancels appointments, always restating details and getting explicit confirmation before doing anything destructive
   - **Support Agent** — hands off to a human when the AI can't help, creating a ticket the admin can see and resolve
3. Persists the whole conversation so an admin can review it, regardless of which channel it came from

## Key capabilities

- **RAG knowledge base** — PDFs/DOCX are chunked, embedded (`sentence-transformers`, running locally), and stored in Postgres via `pgvector`; answers are grounded in retrieved chunks plus structured business data (services, hours, FAQs, policies).
- **Multi-agent architecture** — a lightweight orchestrator classifies intent and delegates to Knowledge / Booking / Support agents, each with their own tool-calling loop (`tool_loop.py`) against **OpenAI** models (see Status — this replaced Groq).
- **Appointment booking** — real slot availability against staff schedules, opening hours, and holidays; book/reschedule/cancel, all requiring explicit confirmation. Booking/cancelling/rescheduling also enqueues a confirmation email and an admin notification via Celery.
- **Real-time voice (browser)** — the browser streams the mic directly to Deepgram STT, gets live transcripts, and plays back streaming Deepgram TTS audio — with barge-in (interrupt the AI while it's talking) and end-of-speech detection.
- **Business document intelligence** — a separate admin pipeline: upload an invoice/receipt/PO/resume/expense report/application form/contract (PDF, DOCX, or a photo), and an LLM classifies + extracts it into structured, per-type database tables an admin can review, correct, and audit. Runs in the background via Celery. See `BUSINESS_DOCUMENT_EXTRACTION.md`.
- **AI SQL & data analyst (admin-only)** — an admin asks "how many invoices did we receive last month?" or "which product generated the most revenue in the last 6 months?" in plain English; the agent inspects an allowlisted schema, writes PostgreSQL, validates it, runs it read-only, and replies with a sentence, a formatted table, and a chart where one helps. Destructive SQL is blocked at two independent layers. See `AI_DATA_ANALYST.md`.
- **Admin notification bell** — in-app notifications for completed/failed document processing, low-confidence extractions, and appointment activity.
- **Background job processing (Celery + Redis)** — document extraction, KB indexing, and outbound email all run as background tasks rather than blocking API requests. **A worker must be running** for these to complete — see `CELERY_SETUP.md`.
- **Human handoff** — chat/voice can escalate to a support ticket (keyword/LLM-detected frustration, repeated failures, or unclear speech on the phone channel). Booking/reschedule/cancel actions always require an explicit "yes."
- **Full admin dashboard** — manage services, staff, business info, holidays, chatbot persona/voice config, knowledge base documents, business documents, customers, appointments, conversations (with the ability to resolve/reopen), notifications, basic analytics, and the natural-language data analyst.
- **Real phone calls (Exotel)** — the code (`app/api/routes/telephony.py`, `app/realtime/telephony_*.py`) is written to bridge a live phone call's audio to Deepgram STT/TTS through the exact same agent pipeline, but it is **currently disconnected from the running app** — see Status below and the caveat at the top of `VOICE_AND_TELEPHONY.md`.

## Status — please read before assuming everything below is live

This documents the project as of the most recent work session available in this snapshot. Two earlier phases of work are layered on top of each other here, and the most recent one left a few things in a partially-wired state that are worth knowing about **before** you go looking for a bug:

1. **The LLM provider was switched from Groq to OpenAI.** The active `LLMService` (`app/services/llm_service.py`) now talks to OpenAI (`OPENAI_API_KEY`, `openai_model`, default `gpt-5.4-mini`). The Groq and OpenRouter client implementations are still in that file but fully commented out. `GROQ_API_KEY` is effectively unused now, even though it's still a config field and still in `.env.example`.
2. **Phone-call support (Exotel) is built but not mounted.** `app/api/routes/telephony.py` is a complete implementation, but it is **not included in `app/main.py`**, so none of the `/api/v1/telephony/*` routes exist on a running server right now. On top of that, the settings it reads (`telephony_enabled`, `telephony_sample_rate`, `exotel_stream_username`/`password`, `public_websocket_host`, `voice_min_confidence`, `voice_unclear_max_attempts`) are **not defined** on the `Settings` class in `app/core/config.py`, so even mounting the router as-is would raise `AttributeError` on the first call. Treat "real phone calls" as a documented-but-currently-disabled feature until both of these are fixed.
3. **Unclear-speech handling only exists on the (disconnected) phone path.** `app/realtime/tool_bridge.py` has `is_unclear_transcript()` / `clarification_turn()` / `escalate_for_unclear_speech()`, and `telephony.py` calls them — but the browser voice router (`app/api/routes/voice.py`, which *is* live) sends every final transcript straight to `stream_turn()` without a confidence check. So today, a mumbled answer on a browser voice call is *not* caught and clarified the way the design intends.
4. **A new business-document-intelligence phase landed after `BUSINESS_DOCUMENT_EXTRACTION.md` was written**, and that doc is now stale in a few places (it describes a single generic table; the code has since moved to a normalized per-document-type schema). See the "⚠️ Doc vs. code" note at the top of that file for specifics.
5. **`celery` and `redis` are not actually in `requirements.txt`**, despite `CELERY_SETUP.md` saying they're "already added" — install them manually for now (`pip install celery redis`). Without a worker running, business-document uploads, KB uploads, and appointment emails will sit in `pending` forever (the API itself won't error).

None of this is called out to be alarmist — the *code* for all of it is real and reasonably complete, it's just not all switched on at the same time in this snapshot. Once you've looked at this project with me, we can go through fixing these one at a time.
