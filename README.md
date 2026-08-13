# AI Customer Support Agent (RAG) — AI Support Agent

A scaffold for an AI-powered customer support chat agent, built for a fictional
salon/spa business. Answers questions about services, pricing, hours, policies,
and FAQs using Retrieval-Augmented Generation.

**Stack:** React (Vite) · FastAPI · PostgreSQL · Qdrant

---

## ⚠️ What's implemented vs. what's left for you

This is a **structural scaffold**, not a finished app. Deliberately left as
`TODO`s / stubs:

| Area | Status |
|---|---|
| Project structure (frontend + backend) | ✅ Done |
| `GET /api/v1/health` | ✅ Done |
| Postgres models + DB session setup | ✅ Structure done, no migrations run |
| Qdrant client wiring | ✅ Structure done, `NotImplementedError` in methods |
| RAG pipeline (`RAGService`) | ❌ Stub only |
| `POST /chat` endpoint | ❌ Stub only, returns `501`, not registered in `main.py` |
| React chat UI (components, state, styling) | ✅ Fully built |
| Frontend → backend API integration | ❌ `sendChatMessage()` throws — wire it up |

Look for `# TODO` / `"""STRUCTURE ONLY, NOT IMPLEMENTED"""` comments in the
code for exact next steps.

---

## Getting started

### 1. Infrastructure (Postgres + Qdrant)
### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then edit values if needed

uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- App: http://localhost:5173

---

## Suggested next steps (in order)

1. **Run Postgres migrations.** Set up Alembic (`alembic init alembic`),
   point it at `app.core.database.Base.metadata`, and create the initial
   migration for the models in `app/models/knowledge_base.py`.
2. **Seed the knowledge base.** Load `app/data/sample_knowledge_base.json`
   into Postgres.
3. **Implement `VectorStoreService`** (`app/services/vector_store.py`):
   collection creation, embedding, upsert, similarity search.
4. **Implement `RAGService`** (`app/services/rag_service.py`): retrieve
   relevant chunks, build a prompt, call an LLM, return a grounded answer.
5. **Implement and register `POST /chat`** (`app/api/routes/chat.py` →
   uncomment the router include in `app/main.py`).
6. **Wire up the frontend** — implement `sendChatMessage()` in
   `frontend/src/services/api.js` to call the real endpoint.

---

## Coding guidelines

### Backend (FastAPI / Python)
- **Layered structure**: routes stay thin (parse request → call service →
  return response). Business logic lives in `services/`, not in route
  handlers.
- **Settings via `app.core.config.get_settings()`** only — never read
  `os.environ` directly in route/service code, and never commit real
  secrets (`.env` is gitignored; `.env.example` documents required vars).
- **Pydantic schemas** (`schemas/`) define the request/response contract at
  the API boundary; **SQLAlchemy models** (`models/`) define the persistence
  layer. Don't return ORM models directly from routes.
- **Type hints everywhere**; prefer explicit `Optional[...]` / `X | None`
  over implicit `Any`.
- **One responsibility per module.** `vector_store.py` only talks to
  Qdrant; `rag_service.py` orchestrates retrieval + generation; it shouldn't
  know about HTTP at all.
- **Docstrings on every public class/function**, especially where logic is
  intentionally left as a stub — say what it should do, not just `pass`.

### Frontend (React)
- **Presentational vs. container split**: `components/Chat/*` render UI and
  take props/callbacks; `hooks/useChat.js` owns state and side effects.
  Components should stay dumb and reusable.
- **One component per file**, named after the file, default-exported.
- **All network calls go through `services/api.js`** — components and hooks
  never call `fetch`/`axios` directly. This keeps the integration surface
  in one place (currently stubbed intentionally).
- **CSS is token-driven**: colors, spacing units, radii are CSS variables
  in `styles/index.css` — don't hardcode hex values in components.
- **No business copy hardcoded deep in components** where avoidable — pull
  shared strings (business name, suggested questions) from
  `utils/constants.js`.

### General
- Keep `.env.example` in sync whenever you add a new environment variable.
- Don't commit `.env`, `node_modules/`, `__pycache__/`, or DB/vector volumes
  (already covered in `.gitignore`).
- Write commit messages and TODOs that state *what's missing and where*,
  the way this scaffold does — it makes picking the project back up (or
  handing it to someone else) much faster.
