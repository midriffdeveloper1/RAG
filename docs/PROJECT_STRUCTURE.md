# Project Structure

Two independent apps, deployed separately: a FastAPI backend and a React (Vite) frontend.

```
project/
├── backend/          # FastAPI application (see below) — package root is backend/app
└── frontend/         # React + Vite application (see below)
```

> Note: some earlier docs referred to `backend/backend/`. In this codebase the backend package lives directly at `backend/app/` — `cd backend` (not `cd backend/backend`) before running `pip install`, `alembic`, or `uvicorn`.

## Backend — `backend/`

```
backend/
├── app/
│   ├── main.py                    # FastAPI app factory, CORS, router registration, startup hook (init_db + embedding warm-up)
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings, reads .env)
│   │   ├── database.py             # SQLAlchemy engine/session, get_db() dependency
│   │   ├── security.py             # Password hashing, JWT for admin auth
│   │   ├── ids.py                  # Short random ID generator used as PK default
│   │   ├── celery_app.py           # Celery app instance, queue routing (`documents`, `mail`)
│   │   └── reset_database.py       # Dev helper to drop/recreate all tables
│   │
│   ├── db/
│   │   ├── init_db.py               # seed_admin() — auto-seeds the admin account on startup (create-tables/seed-chatbot-config/seed-business calls are present but commented out; schema comes from Alembic)
│   │   └── seed_business.py         # Optional: seed a sample business catalog (services/staff/hours) — not called by default
│   │
│   ├── models/                     # SQLAlchemy ORM models (one file per table/domain)
│   │   ├── admin.py                  # Admin (dashboard login)
│   │   ├── customer.py               # Customer (identified by email)
│   │   ├── chat_session.py           # ChatSession + ChatMessage (chat/voice/phone history)
│   │   ├── chatbot_config.py         # Singleton config: persona, voice, feature toggles
│   │   ├── knowledge_base.py         # Business, Service, OpeningHour, FAQ, Policy, Holiday
│   │   ├── staff.py                  # Staff + staff_services join table
│   │   ├── appointment.py            # Appointment (+ AppointmentStatus enum)
│   │   ├── document.py               # Uploaded knowledge-base document metadata (RAG)
│   │   ├── document_chunk.py         # RAG chunks + pgvector embedding column
│   │   ├── support_ticket.py         # Human-handoff tickets
│   │   ├── notification.py           # Notification (admin notification-bell items)
│   │   ├── business_document.py      # LEGACY — original single-table `BusinessDocument`/`business_documents`. Superseded by `business_documents/upload.py`; not imported by `alembic/env.py` or by the current service/extraction/routes code, but a few helper modules (`scoring.py`, `validation.py`, `field_schemas.py`) still import its `BusinessDocumentType` enum. See `BUSINESS_DOCUMENT_EXTRACTION.md`.
│   │   └── business_documents/       # Current business-document schema (normalized, one table set per document type)
│   │       ├── upload.py               # BusinessDocumentUpload — the parent row per uploaded file (status, confidence, file metadata)
│   │       ├── invoice.py              # Invoice + InvoiceLineItem
│   │       ├── receipt.py              # Receipt + ReceiptItem
│   │       ├── purchase_order.py       # PurchaseOrder + PurchaseOrderLineItem
│   │       ├── resume.py               # Resume + ResumeEducation + ResumeExperience
│   │       ├── expense_report.py       # ExpenseReport + ExpenseReportItem
│   │       ├── application_form.py     # ApplicationForm
│   │       └── contract.py             # Contract + ContractSignatory
│   │
│   ├── schemas/                    # Pydantic request/response models, one per domain
│   │   ├── ...                       # (business.py, appointment.py, chat.py, etc. — one per resource)
│   │   ├── business_document.py      # Request/response schemas for the business-document endpoints
│   │   ├── document_extraction.py    # Shared extraction-result shapes
│   │   └── notification.py           # Notification list/response schemas
│   │
│   ├── api/
│   │   ├── deps.py                  # Shared FastAPI dependencies (e.g. get_current_admin, get_page_params)
│   │   └── routes/                  # One router per resource
│   │       ├── auth.py               # Admin login
│   │       ├── business.py           # Business profile, opening hours, FAQs/policies
│   │       ├── services.py           # Service CRUD
│   │       ├── staff.py              # Staff CRUD
│   │       ├── holiday.py            # Holiday CRUD
│   │       ├── documents.py          # Upload/list/delete knowledge-base documents
│   │       ├── business_documents.py # Upload/list/get/correct/reprocess/delete business documents
│   │       ├── notifications.py      # Admin notification bell: list/unread-count/mark-read/delete
│   │       ├── chatbot_config.py     # Admin: edit chatbot persona/voice/toggles
│   │       ├── public_config.py      # Public: widget config for the embedded chat
│   │       ├── chat.py               # POST /chat — text chat turn
│   │       ├── chat_sessions.py      # Customer-facing session history (list/get/delete)
│   │       ├── admin_chat_sessions.py# Admin: list/resolve/reopen conversations
│   │       ├── customers.py          # Customer profile CRUD (self-service + admin)
│   │       ├── appointments.py       # Admin: appointment list/detail
│   │       ├── support_tickets.py    # Admin: ticket list/detail
│   │       ├── analytics.py          # Admin: dashboard overview numbers
│   │       ├── voice.py              # Browser real-time voice: session bootstrap + WS — mounted and live
│   │       └── telephony.py          # Phone calls: Exotel AgentStream WS handler — fully written, but NOT registered in main.py (see VOICE_AND_TELEPHONY.md)
│   │
│   ├── services/                   # Business logic — one service class per concern
│   │   ├── conversation_service.py   # Onboarding vs. agent-turn routing, entry point for all channels
│   │   ├── agents/
│   │   │   ├── orchestrator.py        # Classifies intent, delegates, handles escalation
│   │   │   ├── knowledge_agent.py     # RAG-backed Q&A
│   │   │   ├── booking_agent.py       # Book/reschedule/cancel with confirmation rules
│   │   │   ├── support_agent.py       # Human handoff / ticket messaging
│   │   │   ├── tool_loop.py           # Generic "LLM + tool calling" loop shared by agents (via LLMService → OpenAI)
│   │   │   └── shared_context.py      # Common context (business info, services, etc.) built once per turn
│   │   ├── business_documents/       # Business-document pipeline (see BUSINESS_DOCUMENT_EXTRACTION.md)
│   │   │   ├── field_schemas.py        # Per-document-type field schema — drives the extraction prompt, validation, and persistence
│   │   │   ├── extraction.py           # LLM classification + extraction (text and image/vision paths)
│   │   │   ├── validation.py           # Required/shape validation against the schema
│   │   │   ├── scoring.py              # Combines per-field confidence into an overall confidence_score
│   │   │   ├── persistence.py          # Reads/writes the normalized per-type tables via BusinessDocumentUpload relationships
│   │   │   └── service.py              # BusinessDocumentService — upload → extract → validate → score → persist orchestration
│   │   ├── onboarding_service.py     # Ask-for-email flow before a session is identified
│   │   ├── customer_service.py       # Customer identify/update/lookup (incl. by-phone)
│   │   ├── chat_session_service.py   # ChatSession/ChatMessage persistence, escalation
│   │   ├── chatbot_config_service.py # ChatbotConfig get-or-create + system-prompt building
│   │   ├── appointment_service.py    # Availability, booking, reschedule, cancellation (enqueues mail/notification tasks)
│   │   ├── catalog_service.py        # Services/staff lookups used by booking
│   │   ├── holiday_service.py        # Holiday-aware availability checks
│   │   ├── business_service.py / business_lookup_service.py  # Business profile CRUD/lookup
│   │   ├── faq_policy_service.py     # FAQ/Policy CRUD
│   │   ├── document_service.py       # KB document upload/list/delete orchestration
│   │   ├── document_processor.py     # Shared PDF/DOCX text-extraction helper — reused by both the RAG pipeline and business-document extraction
│   │   ├── document_extraction_service.py  # Business-onboarding extractor (distinct from the business-documents feature)
│   │   ├── embedding_service.py      # sentence-transformers embedding generation
│   │   ├── vector_store.py           # pgvector similarity search
│   │   ├── rag_service.py            # Ties retrieval + generation together
│   │   ├── llm_service.py            # LLMService — currently OpenAI-backed; Groq/OpenRouter implementations present but commented out
│   │   ├── notification_service.py   # Create/list/mark-read notifications shown in the admin bell
│   │   ├── mail_service.py           # SMTP send wrapper
│   │   ├── mail_templates.py         # Email bodies (booking confirmation, cancellation, reschedule)
│   │   ├── support_ticket_service.py # Ticket create/append/resolve/reopen
│   │   ├── time_utils.py             # Email/phone validation, date/time helpers
│   │   └── agent_service.py          # LEGACY — entirely commented out, not imported anywhere; superseded by services/agents/*. Kept in the tree but dead.
│   │
│   ├── tasks/                       # Celery task definitions (see CELERY_SETUP.md)
│   │   ├── business_document_tasks.py # process_business_document_task — runs BusinessDocumentService.process_document in the background
│   │   ├── knowledge_base_tasks.py    # process_document / reindex_document for the RAG pipeline
│   │   └── mail_tasks.py              # send_email_task — outbound booking/cancellation/reschedule email
│   │
│   └── realtime/                   # Real-time voice & telephony subsystem
│       ├── base.py                   # RealtimeVoiceProvider abstract interface
│       ├── deepgram_provider.py      # Deepgram implementation: ephemeral tokens, stream config (browser)
│       ├── events.py                 # RealtimeEvent / RealtimeEventType — the WS event protocol
│       ├── session.py                # VoiceSessionService — browser call ↔ ChatSession mapping
│       ├── tool_bridge.py            # Turns an agent reply into a stream of RealtimeEvents; unclear-speech detection, clarification, escalation helpers (currently only invoked from the disconnected telephony.py — see Status)
│       ├── exotel_codec.py           # Exotel AgentStream wire format (chunking, media/clear/mark)
│       ├── telephony_bridge.py       # Server-side Deepgram STT/TTS connections (phone calls)
│       └── telephony_session.py      # PhoneCallSessionService — phone number ↔ ChatSession mapping
│
├── alembic/                        # DB migrations (see DATABASE_ARCHITECTURE.md)
├── requirements.txt                 # Missing `celery`/`redis` despite both being required — see TECH_STACK.md
├── .env / .env.example
└── app/uploads/                    # Uploaded knowledge-base documents land here; business documents land in app/uploads/business_documents/
```

### Request flow (text chat, as the simplest example)

```
POST /api/v1/chat
  → ConversationService.handle_turn()
      → not identified yet? → OnboardingService (ask for email)
      → identified?        → OrchestratorService.answer()
                                 → classify intent
                                 → KnowledgeAgent | BookingAgent | SupportAgent
                                 → ChatSessionService persists both turns
  → response returned to the widget
```

Browser voice reuses **the exact same `ConversationService`/`OrchestratorService`/agents** — see `VOICE_AND_TELEPHONY.md` for how audio gets turned into that same `handle_turn()` call, and for the current status of the (built but not mounted) phone-call path.

### Request flow (business document upload)

```
POST /api/v1/admin/business-documents/upload
  → BusinessDocumentService.save_upload()      (streams file to disk, sha256 hash, size/type validation)
  → BusinessDocumentService.create_document_record()  (BusinessDocumentUpload row, status=pending)
  → process_business_document_task.delay(...)  (Celery — see CELERY_SETUP.md; without a worker this stays "pending")
      → extraction.extract_from_text() / extract_from_image()   (LLM classify + extract, OpenAI)
      → validation.validate_fields()
      → scoring.compute_confidence()
      → persistence.apply_fields()             (writes the normalized per-type table, e.g. Invoice + InvoiceLineItem)
      → status → completed | needs_review | failed, notification created
```

## Frontend — `frontend/`

```
frontend/
├── index.html
├── vite.config.js
├── package.json
└── src/
    ├── main.jsx                    # App entry point
    ├── App.jsx                     # Top-level routes (customer widget vs. /admin/*)
    │
    ├── config/
    │   └── businessDocumentTypes.js  # Shared config driving the 7 business-document type pages (labels, routes, headline fields)
    │
    ├── pages/
    │   ├── Home.jsx                  # Public page hosting the chat widget
    │   ├── AdminLogin.jsx             # Admin login page
    │   ├── Admindashboard.jsx         # Admin shell (sidebar + routed sub-pages)
    │   └── admin/                     # One page per admin resource
    │       ├── AdminOverview.jsx         # Analytics dashboard
    │       ├── AdminBusinessPage.jsx     # Business profile, hours, FAQs/policies
    │       ├── AdminServicesPage.jsx     # Services CRUD
    │       ├── AdminStaffPage.jsx        # Staff CRUD
    │       ├── AdminAppointmentsPage.jsx # Appointment list/detail
    │       ├── AdminCustomersPage.jsx    # Customer list/detail
    │       ├── AdminKnowledgeBasePage.jsx# Document upload/list (RAG)
    │       ├── AdminChatbotConfigPage.jsx# Persona/voice/feature toggle editor
    │       ├── AdminConversationsPage.jsx# Conversation review + resolve/reopen
    │       └── BusinessManagement/
    │           ├── BusinessDocumentUploadPage.jsx  # The one place to upload business documents (drag/drop, batch results)
    │           └── BusinessDocumentTypePage.jsx    # Reused for all 7 types via businessDocumentTypes.js — record table + "Upload" deep link
    │
    ├── components/
    │   ├── Chat/                     # Customer-facing chat + voice widget
    │   │   ├── ChatWidget.jsx           # Floating launcher + container
    │   │   ├── ChatModal.jsx            # Modal wrapper around chat/voice
    │   │   ├── ModeChoice.jsx           # Chat-vs-voice entry choice
    │   │   ├── ChatWindow.jsx           # Message list + input area
    │   │   ├── ChatMessage.jsx          # Single message bubble (markdown-rendered)
    │   │   ├── ChatInput.jsx            # Text input
    │   │   ├── ChatSidebar.jsx          # Past-session list
    │   │   ├── EmailGateModal.jsx       # "What's your email?" modal
    │   │   ├── SuggestedQuestions.jsx   # Quick-reply chips
    │   │   ├── TicketStatusPanel.jsx    # Shows escalation/ticket status
    │   │   ├── TypingIndicator.jsx
    │   │   ├── WelcomeToast.jsx
    │   │   ├── VoiceCallModal.jsx       # Modal wrapper around the voice call UI
    │   │   └── VoiceCallWidget.jsx      # The real-time voice call UI (mic, waveform, call state)
    │   ├── Admin/                    # One component set per admin resource (lists, modals, forms)
    │   ├── BusinessDocuments/        # Business-document admin UI
    │   │   ├── BusinessDocumentUploadZone.jsx  # Drag/drop + click uploader with live batch results
    │   │   ├── BusinessDocumentTable.jsx       # Paginated per-type record table
    │   │   ├── BusinessDocumentDetailModal.jsx # Full extracted-field view, inline correction, reprocess/delete
    │   │   ├── FieldValue.jsx                  # Generic renderer for any field shape (scalar/list/nested object)
    │   │   ├── BusinessDocumentStatusBadge.jsx
    │   │   └── ConfidenceMeter.jsx
    │   ├── common/                    # Reusable primitives (Modal, Pagination, Spinner, Icons, EmptyState, MultiSelectDropdown, ...)
    │   └── layout/                    # AdminLayout, AdminSidebar, Header, Footer, NotificationBell
    │
    ├── hooks/
    │   ├── useChat.js                 # Chat state + REST calls to /chat, /chat_sessions
    │   ├── useChatSessions.js         # Session list management
    │   ├── useVoiceSession.js         # Orchestrates the browser real-time voice call (see below)
    │   ├── usePagination.js / useServerPagination.js
    │
    ├── realtime/
    │   └── deepgramClient.js          # Low-level mic capture → Deepgram STT WS,
    │                                  #   and Deepgram TTS WS → speaker playback
    │
    ├── context/
    │   ├── AuthContext.jsx            # Admin auth/session state
    │   └── CustomerContext.jsx        # Customer identity (email) state
    │
    ├── services/
    │   ├── api.js                     # Public/customer-facing API client (axios)
    │   └── adminApi.js                # Admin API client (adds auth header; includes the business-document + notification functions)
    │
    ├── utils/
    │   ├── browserId.js                # Generates/persists a per-browser anonymous ID
    │   ├── businessDocuments.js        # Headline-field extraction, per-type display helpers
    │   ├── time.js                     # Date/time formatting helpers
    │   └── constants.js
    │
    └── styles/
        └── index.css                   # Single global stylesheet (business-document rules appended at the end)
```

### Voice call flow (browser)

```
VoiceCallWidget → useVoiceSession()
   → POST /api/v1/voice/session         (bootstrap: get a Deepgram ephemeral token + WS URLs)
   → deepgramClient: mic → Deepgram STT WS (direct from browser)
   → useVoiceSession: on final transcript → send over control WS to backend
   → backend: /api/v1/voice/ws/{session_id}  → same OrchestratorService pipeline → text reply
   → deepgramClient: reply text → Deepgram TTS WS (direct from browser) → speaker
```

Phone calls are designed to follow the same shape, but entirely server-side, and currently **cannot be exercised** because the router isn't registered and required settings are missing — see `VOICE_AND_TELEPHONY.md`.
