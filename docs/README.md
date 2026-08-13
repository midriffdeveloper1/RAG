# AI Customer Support Agent (RAG) — Serenity Salon & Spa

A scaffold for an AI-powered customer support chat agent, built for a fictional
salon/spa business. Answers questions about services, pricing, hours, policies,
and FAQs using Retrieval-Augmented Generation.

**Stack:** React (Vite) · FastAPI · PostgreSQL · Qdrant

**Docs:** [`docs/RAG_PIPELINE.md`](docs/RAG_PIPELINE.md) (ingestion pipeline + Phase 2 plan) · [`docs/ADMIN_GUIDE.md`](docs/ADMIN_GUIDE.md) (admin panel usage)

---

## ⚠️ What's implemented vs. what's left for you

| Area | Status |
|---|---|
| Project structure (frontend + backend) | ✅ Done |
| `GET /api/v1/health` | ✅ Done |
| **Admin login** (JWT, seeded account, no signup) | ✅ Done — `POST /auth/login`, `GET /auth/me` |
| **Document upload** (PDF/DOCX) | ✅ Done — `POST /admin/documents/upload` |
| **Ingestion pipeline** (extract → chunk → embed → upsert to Qdrant) | ✅ Done, fully functional, local embeddings (no API key) |
| **Reindexing / re-upload dedup / delete** | ✅ Done — see `docs/RAG_PIPELINE.md` |
| **Admin dashboard UI** (login, upload, document table, reindex, delete) | ✅ Done |
| Vector search (`VectorStoreService.search`) | ✅ Done, fully functional |
| Postgres models (business data + admin + documents) | ✅ Done, tables auto-created on startup (dev only — see note below) |
| **Chat answer generation** (retrieval + relevance filtering + Groq) | ✅ Done — see `docs/RAG_PIPELINE.md` |
| **Out-of-domain / off-topic refusal** | ✅ Done — score-gated + prompt-enforced |
| `POST /chat` endpoint | ✅ Done, registered in `main.py` |
| Customer chat UI | ✅ Fully built and wired to the live backend |

Look for `# TODO` comments in the code for the few remaining
nice-to-haves (streaming, multi-turn memory, citation UI) — see
**`docs/RAG_PIPELINE.md`** "What's still open" for the full list.

---

## Project structure

```
ai-support-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint — health, auth, documents routers
│   │   ├── core/
│   │   │   ├── config.py              # env-based settings (DB, Qdrant, JWT, upload, chunking, embeddings)
│   │   │   ├── database.py            # SQLAlchemy engine/session (Postgres)
│   │   │   └── security.py            # password hashing + JWT create/decode
│   │   ├── db/
│   │   │   └── init_db.py             # dev-only: create_all() + seed the one admin account
│   │   ├── api/
│   │   │   ├── deps.py                # get_current_admin (JWT) dependency
│   │   │   └── routes/
│   │   │       ├── health.py          # ✅ implemented
│   │   │       ├── auth.py            # ✅ implemented — POST /auth/login, GET /auth/me
│   │   │       ├── documents.py       # ✅ implemented — upload/list/reindex/delete (admin-only)
│   │   │       └── chat.py            # ⚠️ retrieval works, generation stub — Phase 2
│   │   ├── models/
│   │   │   ├── admin.py               # Admin (seeded, login-only)
│   │   │   ├── document.py            # Document (status, content_hash, chunk_count, version)
│   │   │   └── knowledge_base.py      # Business, Service, OpeningHour, FAQ, Policy
│   │   ├── schemas/
│   │   │   ├── auth.py                # LoginRequest / TokenResponse / AdminOut
│   │   │   ├── document.py            # DocumentOut / DocumentListResponse / DocumentActionResponse
│   │   │   └── chat.py                # ChatRequest / ChatResponse
│   │   ├── services/
│   │   │   ├── document_processor.py  # ✅ PDF/DOCX text extraction + chunking
│   │   │   ├── embedding_service.py   # ✅ local sentence-transformers embeddings
│   │   │   ├── vector_store.py        # ✅ Qdrant: ensure_collection, upsert, delete-by-doc, search
│   │   │   ├── document_service.py    # ✅ orchestrates upload → process → reindex → delete
│   │   │   └── rag_service.py         # ⚠️ retrieve_context() done, generate_answer() Phase 2
│   │   ├── data/
│   │   │   └── sample_knowledge_base.json  # seed content for the salon (Postgres models)
│   │   └── uploads/                   # uploaded files land here (gitignored)
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/                # Header (with admin link), Footer
│   │   │   ├── Chat/                  # ChatWidget, ChatWindow, ChatMessage,
│   │   │   │                          # ChatInput, TypingIndicator, SuggestedQuestions
│   │   │   └── admin/                 # ProtectedRoute, AdminLoginForm, DocumentUpload,
│   │   │                              # DocumentList, StatusBadge
│   │   ├── pages/
│   │   │   ├── Home.jsx               # customer chat page
│   │   │   ├── AdminLogin.jsx
│   │   │   └── AdminDashboard.jsx     # upload + manage documents
│   │   ├── context/
│   │   │   └── AuthContext.jsx        # admin token storage, login/logout, session check
│   │   ├── hooks/useChat.js           # chat state management (message list, loading, error)
│   │   ├── services/
│   │   │   ├── api.js                 # axios client (+ JWT interceptor) — sendChatMessage() stub
│   │   │   └── adminApi.js            # ✅ fully wired — login, documents CRUD
│   │   ├── styles/index.css
│   │   └── utils/constants.js
│   ├── package.json
│   └── .env.example
│
├── docs/
│   ├── RAG_PIPELINE.md                # full ingestion pipeline diagram + Phase 2 roadmap
│   └── ADMIN_GUIDE.md                 # how to use the admin panel
│
├── docker-compose.yml                 # Postgres + Qdrant for local dev
├── .gitignore
└── README.md
```

---

## Admin panel & document ingestion (new)

- **Login**: `/admin/login` — single seeded admin account, no signup route
  exists anywhere in the app. Credentials come from `ADMIN_EMAIL` /
  `ADMIN_PASSWORD` in `backend/.env` and are seeded on first startup.
- **Upload**: `/admin` — upload a `.pdf` or `.docx`. It's immediately
  extracted, chunked, embedded (locally, no API key needed), and upserted
  into Qdrant. Status updates live: `Pending → Processing → Completed`
  (or `Failed`, with the error shown).
- **Reindex**: deletes that document's existing vectors from Qdrant, then
  re-processes the file from disk and bumps its version.
- **Delete**: removes the document's vectors, DB row, and file — full
  cleanup, nothing orphaned.
- **Re-upload dedup**: uploading byte-identical content to an already
  `Completed` document reuses the existing record instead of re-embedding.

Full details, including why filtered-delete-by-`document_id` is used
instead of tracking point IDs: **`docs/RAG_PIPELINE.md`**. Day-to-day usage:
**`docs/ADMIN_GUIDE.md`**.

---

## Getting started

### 1. Infrastructure (Postgres + Qdrant)

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Before starting the server, set real admin credentials **and a Groq API
key** in `.env` (the defaults are placeholders and not secure/functional):

```
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD=a-real-password
GROQ_API_KEY=gsk_...          # free key: https://console.groq.com/keys
```

```bash
uvicorn app.main:app --reload --port 8000
```

On first startup, tables are created and the admin account above is
seeded automatically (`app/db/init_db.py`).

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

**Note:** `init_db.py` uses `Base.metadata.create_all()` for convenience —
fine for local dev, but it only handles initial table creation, not schema
changes. Set up Alembic before you need real migrations (see "Suggested
next steps" below).

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- Customer chat: http://localhost:5173
- Admin login: http://localhost:5173/admin/login

---

## Suggested next steps (in order)

Ingestion (upload → chunk → embed → Qdrant) is done. What's left is
entirely on the **answer generation** side — see `docs/RAG_PIPELINE.md`
"Phase 2" for the full write-up. In short:

1. **Pick and wire up an LLM provider** (Anthropic/OpenAI/etc.) — add the
   API key to `.env`, uncomment the SDK in `requirements.txt`.
2. **Implement `RAGService.generate_answer()`** in
   `app/services/rag_service.py` — build a context-grounded prompt from
   `retrieve_context()`'s output (already implemented) and call the LLM.
3. **Register the chat router** — uncomment the `chat` router include in
   `app/main.py` once generation is implemented.
4. **Wire up the frontend** — implement `sendChatMessage()` in
   `frontend/src/services/api.js` to call the real `POST /chat` endpoint;
   `useChat.js` already handles the rest.
5. **Set up real migrations.** Replace the dev-only `create_all()` in
   `app/db/init_db.py` with Alembic (`alembic init alembic`) once the
   schema is stabilizing.
6. **Seed the structured knowledge base** (optional). Load
   `app/data/sample_knowledge_base.json` into the `Business`/`Service`/
   `OpeningHour`/`FAQ`/`Policy` tables if you want structured data
   alongside the document-based RAG content — useful for exact-match
   lookups (e.g. "what's your phone number") that don't need retrieval.

---

## Coding guidelines

### Backend (FastAPI / Python)
- **Layered structure**: routes stay thin (parse request → call service →
  return response). Business logic lives in `services/`, not in route
  handlers. `documents.py` follows this strictly — all the real work is in
  `DocumentService`.
- **Settings via `app.core.config.get_settings()`** only — never read
  `os.environ` directly in route/service code, and never commit real
  secrets (`.env` is gitignored; `.env.example` documents required vars).
- **Pydantic schemas** (`schemas/`) define the request/response contract at
  the API boundary; **SQLAlchemy models** (`models/`) define the persistence
  layer. Don't return ORM models directly from routes (`response_model=`
  handles the conversion via `from_attributes`).
- **Type hints everywhere**; prefer explicit `Optional[...]` / `X | None`
  over implicit `Any`.
- **One responsibility per module.** `vector_store.py` only talks to
  Qdrant; `document_processor.py` only extracts/chunks text; `rag_service.py`
  orchestrates retrieval + generation and shouldn't know about HTTP at all.
- **Auth is a dependency, not a decorator.** Protected routes take
  `admin: Admin = Depends(get_current_admin)` as a parameter — this keeps
  auth explicit in the function signature and lets FastAPI document it in
  `/docs` automatically.
- **Docstrings on every public class/function**, especially where logic is
  intentionally left as a stub — say what it should do, not just `pass`.

### Frontend (React)
- **Presentational vs. container split**: components render UI and take
  props/callbacks; `hooks/useChat.js` and `context/AuthContext.jsx` own
  state and side effects. Components should stay dumb and reusable.
- **One component per file**, named after the file, default-exported.
- **All network calls go through `services/api.js` / `services/adminApi.js`**
  — components and hooks never call `fetch`/`axios` directly. This keeps
  the integration surface in one place, and is why swapping the chat stub
  for a real call only touches one function.
- **Auth state lives in `AuthContext`, not component state.** Any
  component that needs to know if an admin is logged in calls `useAuth()`
  rather than re-deriving it from `localStorage` itself.
- **CSS is token-driven**: colors, spacing units, radii are CSS variables
  in `styles/index.css` — don't hardcode hex values in components.
- **No business copy hardcoded deep in components** where avoidable — pull
  shared strings (business name, suggested questions) from
  `utils/constants.js`.

### Security notes (dev defaults — change before deploying)
- `SECRET_KEY` in `.env.example` is a placeholder. Generate a real one with
  `openssl rand -hex 32` and never commit it.
- `ADMIN_PASSWORD` defaults to a placeholder — set a real one before first
  startup (see "Getting started" above).
- The JWT has no refresh flow — it simply expires after
  `ACCESS_TOKEN_EXPIRE_MINUTES` and the admin has to log in again.
- Uploaded files are stored on local disk (`UPLOAD_DIR`) with a random
  filename; consider object storage (S3/GCS) instead of local disk for
  anything beyond local dev.

### General
- Keep `.env.example` in sync whenever you add a new environment variable.
- Don't commit `.env`, `node_modules/`, `__pycache__/`, or DB/vector volumes
  (already covered in `.gitignore`).
- Write commit messages and TODOs that state *what's missing and where*,
  the way this scaffold does — it makes picking the project back up (or
  handing it to someone else) much faster.