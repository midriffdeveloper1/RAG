# How to Run

## Prerequisites

- **Python 3.11+** (3.12 recommended — matches `requirements.txt`/dev environment)
- **Node.js 18+** and npm
- **PostgreSQL 14+** with the **`pgvector`** extension available
- API keys: **Groq** (required), **Deepgram** (required for any voice feature), **Exotel** (only for real phone calls)

---

## 1. Database setup

Create a database and enable pgvector:

```bash
psql -U postgres -c "CREATE DATABASE support_agent_db;"
psql -U postgres -d support_agent_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 2. Backend setup

```bash
cd backend/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
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

GROQ_API_KEY=...

# Only needed if you want voice (browser call or phone call):
DEEPGRAM_API_KEY=...

# Only needed for real phone calls:
TELEPHONY_ENABLED=true
EXOTEL_STREAM_USERNAME=...
EXOTEL_STREAM_PASSWORD=...
PUBLIC_WEBSOCKET_HOST=your-public-domain.example
```

Run migrations, then start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

On first startup, an admin account is auto-seeded from `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env` (see `app/db/init_db.py`). Log in to the admin dashboard with those credentials.

The API is now at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`.

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

Once both apps are running:

1. Log in to `/admin` with the seeded admin credentials.
2. **Business** page — fill in business name, description, address, opening hours.
3. **Services** page — add the services your business offers (name, price, duration).
4. **Staff** page — add staff and link them to the services they perform.
5. **Knowledge Base** page — upload FAQ/policy documents (PDF/DOCX) to power the RAG-backed Knowledge Agent.
6. **Chatbot Config** page — set the assistant's persona/tone, and (if you have a Deepgram key) enable voice and pick a voice.
7. Open the public widget (`Home.jsx` route) and try a chat — then try a voice call if enabled.

## 5. Enabling real phone calls (optional)

See `VOICE_AND_TELEPHONY.md` for the full explanation. Short version:

1. Get an Exotel account and an ExoPhone number with the **Voicebot Applet** enabled (Exotel needs to turn this on for your account).
2. Deploy the backend somewhere publicly reachable over `wss://`.
3. In Exotel's App Bazaar, point the Voicebot Applet at:
   ```
   wss://<your-domain>/api/v1/telephony/exotel/stream
   ```
   (or use the dynamic-URL option pointing at `POST /api/v1/telephony/exotel/stream-url`).
4. Set `TELEPHONY_ENABLED=true`, `DEEPGRAM_API_KEY`, and (recommended) `EXOTEL_STREAM_USERNAME`/`EXOTEL_STREAM_PASSWORD` in `.env`.
5. Call the ExoPhone number and talk to the assistant.

## Running both apps together (quick reference)

```bash
# Terminal 1
cd backend/backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

## Common issues

| Symptom | Likely cause |
|---|---|
| `relation "..." does not exist` | Migrations haven't been run — `alembic upgrade head` |
| `type "vector" does not exist` | pgvector extension not enabled on the database |
| Chat says "assistant isn't configured yet" (HTTP 503) | `GROQ_API_KEY` missing/invalid |
| Voice call button does nothing / 503 | `DEEPGRAM_API_KEY` missing, or `voice_enabled` off in Chatbot Config |
| CORS errors in the browser console | Frontend origin not in `CORS_ORIGINS` |
| Phone calls don't connect | `TELEPHONY_ENABLED=false`, Exotel Voicebot Applet not pointed at the right URL, or the backend isn't reachable over `wss://` from Exotel |
