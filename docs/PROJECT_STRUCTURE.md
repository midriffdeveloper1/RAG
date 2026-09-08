# Project Structure

Two independent apps, deployed separately: a FastAPI backend and a React (Vite) frontend.

```
project/
├── backend/backend/          # FastAPI application (see below)
└── frontend/                 # React + Vite application (see below)
```

## Backend — `backend/backend/`

```
backend/backend/
├── app/
│   ├── main.py                    # FastAPI app factory, CORS, router registration
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings, reads .env)
│   │   ├── database.py             # SQLAlchemy engine/session, get_db() dependency
│   │   ├── security.py             # Password hashing, JWT for admin auth
│   │   ├── ids.py                  # Short random ID generator used as PK default
│   │   └── reset_database.py       # Dev helper to drop/recreate all tables
│   │
│   ├── models/                     # SQLAlchemy ORM models (one file per table/domain)
│   │   ├── admin.py                 # Admin (dashboard login)
│   │   ├── customer.py              # Customer (identified by email)
│   │   ├── chat_session.py          # ChatSession + ChatMessage (chat/voice/phone history)
│   │   ├── chatbot_config.py        # Singleton config: persona, voice, feature toggles
│   │   ├── knowledge_base.py        # Business, Service, OpeningHour, FAQ, Policy, Holiday
│   │   ├── staff.py                 # Staff + staff_services join table
│   │   ├── appointment.py           # Appointment (+ AppointmentStatus enum)
│   │   ├── document.py              # Uploaded document metadata
│   │   ├── document_chunk.py        # RAG chunks + pgvector embedding column
│   │   └── support_ticket.py        # Human-handoff tickets
│   │
│   ├── schemas/                    # Pydantic request/response models, one per domain
│   │
│   ├── api/
│   │   ├── deps.py                  # Shared FastAPI dependencies (e.g. get_current_admin)
│   │   └── routes/                  # One router per resource
│   │       ├── auth.py               # Admin login
│   │       ├── business.py           # Business profile, opening hours, FAQs/policies
│   │       ├── services.py           # Service CRUD
│   │       ├── staff.py              # Staff CRUD
│   │       ├── holiday.py            # Holiday CRUD
│   │       ├── documents.py          # Upload/list/delete knowledge-base documents
│   │       ├── chatbot_config.py     # Admin: edit chatbot persona/voice/toggles
│   │       ├── public_config.py      # Public: widget config for the embedded chat
│   │       ├── chat.py               # POST /chat — text chat turn
│   │       ├── chat_sessions.py      # Customer-facing session history (list/get/delete)
│   │       ├── admin_chat_sessions.py# Admin: list/resolve/reopen conversations
│   │       ├── customers.py          # Customer profile CRUD (self-service + admin)
│   │       ├── appointments.py       # Admin: appointment list/detail
│   │       ├── support_tickets.py    # Admin: ticket list/detail
│   │       ├── analytics.py          # Admin: dashboard overview numbers
│   │       ├── voice.py              # Browser real-time voice: session bootstrap + WS
│   │       └── telephony.py          # Phone calls: Exotel AgentStream WS handler
│   │
│   ├── services/                   # Business logic — one service class per concern
│   │   ├── conversation_service.py   # Onboarding vs. agent-turn routing, entry point for all channels
│   │   ├── agents/
│   │   │   ├── orchestrator.py        # Classifies intent, delegates, handles escalation
│   │   │   ├── knowledge_agent.py     # RAG-backed Q&A
│   │   │   ├── booking_agent.py       # Book/reschedule/cancel with confirmation rules
│   │   │   ├── support_agent.py       # Human handoff / ticket messaging
│   │   │   ├── tool_loop.py           # Generic "LLM + tool calling" loop shared by agents
│   │   │   └── shared_context.py      # Common context (business info, services, etc.) built once per turn
│   │   ├── onboarding_service.py     # Ask-for-email flow before a session is identified
│   │   ├── customer_service.py       # Customer identify/update/lookup (incl. by-phone)
│   │   ├── chat_session_service.py   # ChatSession/ChatMessage persistence, escalation
│   │   ├── appointment_service.py    # Availability, booking, reschedule, cancellation
│   │   ├── catalog_service.py        # Services/staff lookups used by booking
│   │   ├── holiday_service.py        # Holiday-aware availability checks
│   │   ├── business_service.py / business_lookup_service.py  # Business profile CRUD/lookup
│   │   ├── faq_policy_service.py     # FAQ/Policy CRUD
│   │   ├── document_service.py       # Document upload/list/delete orchestration
│   │   ├── document_processor.py / document_extraction_service.py  # Parse PDFs/DOCX into text
│   │   ├── embedding_service.py      # sentence-transformers embedding generation
│   │   ├── vector_store.py           # pgvector similarity search
│   │   ├── rag_service.py            # Ties retrieval + generation together
│   │   ├── llm_service.py            # Groq/OpenRouter chat completion wrapper
│   │   ├── support_ticket_service.py # Ticket create/append/resolve/reopen
│   │   └── time_utils.py             # Email/phone validation, date/time helpers
│   │
│   └── realtime/                   # Real-time voice & telephony subsystem
│       ├── base.py                   # RealtimeVoiceProvider abstract interface
│       ├── deepgram_provider.py      # Deepgram implementation: ephemeral tokens, stream config (browser)
│       ├── events.py                 # RealtimeEvent / RealtimeEventType — the WS event protocol
│       ├── session.py                # VoiceSessionService — browser call ↔ ChatSession mapping
│       ├── tool_bridge.py            # Turns an agent reply into a stream of RealtimeEvents;
│       │                             #   unclear-speech detection, clarification, escalation
│       ├── exotel_codec.py           # Exotel AgentStream wire format (chunking, media/clear/mark)
│       ├── telephony_bridge.py       # Server-side Deepgram STT/TTS connections (phone calls)
│       └── telephony_session.py      # PhoneCallSessionService — phone number ↔ ChatSession mapping
│
├── alembic/                        # DB migrations (see DATABASE_ARCHITECTURE.md)
├── requirements.txt
├── .env / .env.example
└── app/uploads/                    # Uploaded knowledge-base documents land here
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

Voice (browser) and phone calls reuse **the exact same `ConversationService`/`OrchestratorService`/agents** — see `VOICE_AND_TELEPHONY.md` for how audio gets turned into that same `handle_turn()` call.

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
    ├── pages/
    │   ├── Home.jsx                  # Public page hosting the chat widget
    │   ├── Adminlogin.jsx             # Admin login page
    │   ├── Admindashboard.jsx         # Admin shell (sidebar + routed sub-pages)
    │   └── admin/                     # One page per admin resource
    │       ├── AdminOverview.jsx         # Analytics dashboard
    │       ├── AdminBusinessPage.jsx     # Business profile, hours, FAQs/policies
    │       ├── AdminServicesPage.jsx     # Services CRUD
    │       ├── AdminStaffPage.jsx        # Staff CRUD
    │       ├── AdminAppointmentsPage.jsx # Appointment list/detail
    │       ├── AdminCustomersPage.jsx    # Customer list/detail
    │       ├── AdminKnowledgeBasePage.jsx# Document upload/list
    │       ├── AdminChatbotConfigPage.jsx# Persona/voice/feature toggle editor
    │       └── AdminConversationsPage.jsx# Conversation review + resolve/reopen
    │
    ├── components/
    │   ├── Chat/                     # Customer-facing chat + voice widget
    │   │   ├── ChatWidget.jsx           # Floating launcher + container
    │   │   ├── ChatWindow.jsx           # Message list + input area
    │   │   ├── ChatMessage.jsx          # Single message bubble (markdown-rendered)
    │   │   ├── ChatInput.jsx            # Text input
    │   │   ├── ChatSidebar.jsx          # Past-session list
    │   │   ├── EmailGateModal.jsx       # "What's your email?" modal
    │   │   ├── SuggestedQuestions.jsx   # Quick-reply chips
    │   │   ├── TicketStatusPanel.jsx    # Shows escalation/ticket status
    │   │   ├── TypingIndicator.jsx
    │   │   ├── WelcomeToast.jsx
    │   │   └── VoiceCallWidget.jsx      # The real-time voice call UI (mic, waveform, call state)
    │   ├── Admin/                    # One component set per admin resource (lists, modals, forms)
    │   ├── common/                    # Reusable primitives (Modal, Pagination, Spinner, Icons, ...)
    │   └── layout/                    # AdminLayout, AdminSidebar, Header, Footer
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
    │   └── adminApi.js                # Admin API client (adds auth header)
    │
    ├── utils/
    │   ├── browserId.js                # Generates/persists a per-browser anonymous ID
    │   └── constants.js
    │
    └── styles/
        └── index.css                   # Single global stylesheet
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

Phone calls follow the same shape, but entirely server-side — see `VOICE_AND_TELEPHONY.md`.
