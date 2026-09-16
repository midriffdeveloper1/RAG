# How to Run

## Prerequisites

- **Python 3.11+** (3.12 recommended — matches `requirements.txt`/dev environment)
- **Node.js 18+** and npm
- **PostgreSQL 14+** with the **`pgvector`** extension available
- **Redis** (for Celery) — uploads and appointment emails will silently sit unprocessed without it; see step 2b and `CELERY_SETUP.md`
- API keys: **OpenAI** (required — this is the active LLM provider; see `TECH_STACK.md`), **Deepgram** (required for browser voice), **Exotel** (only relevant once phone-call support is wired up — see Status note below)

---

## 1. Database setup

Create a database and enable pgvector:

```bash
psql -U postgres -c "CREATE DATABASE support_agent_db;"
psql -U postgres -d support_agent_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install celery redis        # not currently listed in requirements.txt but required — see CELERY_SETUP.md
```

Copy the example env file and fill in real values:

```bash
cp .env.example .env
```

Key variables to set in `.env` (see `TECH_STACK.md`/`.env.example` for the full list):

```dotenv
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=support_agent_db

SECRET_KEY=some-long-random-string
ADMIN_EMAIL=admin@yourbusiness.example
ADMIN_PASSWORD=choose-a-strong-password

# Required — this is the active LLM provider (agents, RAG answers, and
# business-document extraction all go through this). GROQ_API_KEY/
# OPENROUTER_API_KEY exist as config fields too, but the code that used
# them is currently commented out in app/services/llm_service.py.
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini

# Required for Celery (background document processing + email) to work at all:
REDIS_URL=redis://localhost:6379/0

# Only needed if you want browser voice calls:
DEEPGRAM_API_KEY=...
```

Run migrations, then start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

On first startup, an admin account is auto-seeded from `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env` (see `app/db/init_db.py`). Log in to the admin dashboard with those credentials.

The API is now at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`.

## 2b. Start a Celery worker

Business-document uploads, knowledge-base document processing, and outbound booking/cancellation/reschedule emails are all handled by background Celery tasks, not inline in the request. **Without a worker running, uploads will stay `pending` forever and emails/notifications for appointments won't fire** — the API itself won't error, so this is easy to miss. See `CELERY_SETUP.md` for the full run book; short version:

```bash
# make sure Redis is running (redis-cli ping -> PONG), then, from backend/:
celery -A app.core.celery_app.celery_app worker --loglevel=info            # macOS/Linux
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo # Windows
```

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

By default Vite serves at `http://localhost:5173`. In development you don't need to configure an API URL — `vite.config.js` proxies any `/api/*` request straight to `http://localhost:8000`. For a production build (or a different backend host), set `VITE_API_BASE_URL` in a `frontend/.env` file before running `npm run build`.

Make sure `CORS_ORIGINS` in the backend `.env` includes `http://localhost:5173` (it does by default).

```bash
npm run build      # production build
npm run preview    # preview the production build locally
npm run lint        # ESLint
```

## 4. First-time admin setup checklist

Once the API, Celery worker, and frontend are all running:

1. Log in to `/admin` with the seeded admin credentials.
2. **Business** page — fill in business name, description, address, opening hours.
3. **Services** page — add the services your business offers (name, price, duration).
4. **Staff** page — add staff and link them to the services they perform.
5. **Knowledge Base** page — upload FAQ/policy documents (PDF/DOCX) to power the RAG-backed Knowledge Agent. Confirm the worker picked it up (status moves past `pending`).
6. **Business management → Upload documents** page — optionally try the business-document pipeline (invoice/receipt/etc.) with a sample file.
7. **Chatbot Config** page — set the assistant's persona/tone, and (if you have a Deepgram key) enable voice and pick a voice.
8. Open the public widget (`Home.jsx` route) and try a chat — then try a voice call if enabled.

## 5. Real phone calls — currently not wired up

`VOICE_AND_TELEPHONY.md` documents the full design of Exotel phone-call support, and the code for it (`app/api/routes/telephony.py`, `app/realtime/telephony_*.py`) is complete. However, in this snapshot:

- `telephony.router` is **not included** in `app/main.py`, so the `/api/v1/telephony/*` endpoints don't exist on a running server.
- `Settings` in `app/core/config.py` doesn't define `telephony_enabled`, `telephony_sample_rate`, `exotel_stream_username`/`password`, `public_websocket_host`, `voice_min_confidence`, or `voice_unclear_max_attempts` — all of which `telephony.py` reads. Setting them in `.env` alone won't fix this; they need to be added as fields on `Settings` first.

Until both of those are addressed, skip this section — there's nothing to point Exotel at yet.

## Running both apps together (quick reference)

```bash
# Terminal 1
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd backend && source venv/bin/activate && celery -A app.core.celery_app.celery_app worker --loglevel=info

# Terminal 3
cd frontend && npm run dev
```

## Common issues

| Symptom | Likely cause |
|---|---|
| `relation "..." does not exist` | Migrations haven't been run — `alembic upgrade head` |
| `type "vector" does not exist` | pgvector extension not enabled on the database |
| Chat says "assistant isn't configured yet" (HTTP 503) | `OPENAI_API_KEY` missing/invalid (this replaced `GROQ_API_KEY` as the required key — see Status in the README) |
| Business-document/KB uploads stay stuck on "pending" | No Celery worker running, or Redis isn't reachable — see `CELERY_SETUP.md` |
| Appointment booked but no confirmation email / no admin notification | Same as above — email/notifications are dispatched via a Celery task, not inline |
| Voice call button does nothing / 503 | `DEEPGRAM_API_KEY` missing, or `voice_enabled` off in Chatbot Config |
| CORS errors in the browser console | Frontend origin not in `CORS_ORIGINS` |
| Phone calls don't connect / route not found | Expected in this snapshot — the telephony router isn't mounted yet. See "Real phone calls" above and `VOICE_AND_TELEPHONY.md`. |
