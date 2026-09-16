# Tech Stack

## Backend

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Web framework | **FastAPI** (`0.115`) + **Uvicorn** | REST + native WebSocket support, used heavily for real-time voice/telephony |
| ORM | **SQLAlchemy 2.0** (typed `Mapped`/`mapped_column` style) | |
| Migrations | **Alembic** | |
| Database | **PostgreSQL** + **pgvector** extension | pgvector stores/queries the RAG embeddings directly in Postgres — no separate vector DB needed |
| DB driver | `psycopg2-binary` | |
| Validation / settings | **Pydantic v2** + `pydantic-settings` | `app/core/config.py` reads all config from `.env` |
| Auth | `python-jose` (JWT) + `passlib`/`bcrypt` | Admin dashboard login only — customers are identified by email, not password auth |
| LLM provider | **OpenAI** (`openai` SDK, default model `gpt-5.4-mini` via `OPENAI_MODEL`) | Powers the agent orchestrator, all three agents' tool-calling loops, and business-document classification/extraction. `generate_json_with_image` (vision) also goes through OpenAI, using `openai_vision_model`. |
| Background jobs | **Celery** + **Redis** (broker + result backend) | Business-document extraction, KB document chunking/embedding, and outbound email all run as background tasks — see `CELERY_SETUP.md`. **Not currently listed in `requirements.txt`** despite being used throughout the code — install manually (`pip install celery redis`) until that's fixed. |
| Embeddings | **sentence-transformers** (`multi-qa-MiniLM-L6-cos-v1`, 384-dim) | Runs locally (via `torch`/`transformers`) at document-ingestion and query time |
| Document parsing | `pypdf`, `python-docx` | Extracts text from uploaded PDF/DOCX files, for both the RAG knowledge base and business-document extraction |
| Real-time voice/STT/TTS | **Deepgram** (`nova-2` STT, `aura-*` TTS voices) | Browser flow: ephemeral-token WS straight from the client, live and working. Phone flow: server-side WS via the `websockets` library — implemented but currently disconnected, see below |
| Telephony | **Exotel AgentStream** (Voicebot Applet) | Bidirectional WebSocket PSTN audio streaming — fully implemented in `app/api/routes/telephony.py`, but **that router isn't registered in `app/main.py`**, and the settings it needs (`telephony_enabled`, `exotel_*`, `public_websocket_host`, etc.) aren't defined on `Settings` yet. See `VOICE_AND_TELEPHONY.md` for the full caveat before relying on this. |
| Async WS client | `websockets` (17.x) | Used server-side only, for the (currently disconnected) telephony ↔ Deepgram bridge |
| Vector similarity | `pgvector` SQLAlchemy integration | Cosine-similarity search over `document_chunks.embedding` |
| Other notable deps | `qdrant-client` (present but pgvector is the active store), `tavily` (present, not wired into a route), `groq` (present, the Groq-backed `LLMService` implementation is commented out in `llm_service.py`, no longer used) | Listed in `requirements.txt`; not all are exercised by the current codepaths |

### Why OpenAI now, instead of Groq?
`app/services/llm_service.py` contains three implementations of `LLMService` stacked in the same file: a Groq version, an OpenRouter version, and an OpenAI version. Only the **OpenAI** one is active (imported/instantiated); the other two are fully commented out but left in place, presumably as a reference for how to switch back or between providers. If you're configuring a fresh `.env`, `OPENAI_API_KEY` is the one that matters — `GROQ_API_KEY`/`OPENROUTER_API_KEY` can be left blank.

### Why no charting library?
The AI data analyst renders bar, line and pie charts as hand-rolled inline SVG
(`components/Analyst/AnalystChart.jsx`). The project had no chart dependency, and
three simple shapes on a single admin-only page didn't justify adding one to the
bundle. Charts use the admin theme's own sage/clay palette rather than a generic
chart palette.

### Why local embeddings?
Embeddings run locally via `sentence-transformers` so there's no per-query embedding API cost or extra network hop for retrieval, independent of whichever chat-completion provider is wired up.

### Why pgvector instead of a dedicated vector DB?
The whole app already needs Postgres for relational data (appointments, customers, tickets, business documents, etc.); pgvector lets the RAG chunks live in the same database and transaction boundary as everything else, avoiding a second system to run/operate.

### Why Celery + Redis?
Document extraction (both RAG ingestion and business-document extraction) involves an LLM call and can take several seconds; outbound email involves an SMTP round-trip. Both are moved off the request/response path so the API stays fast and a slow LLM/SMTP call can't time out a user-facing request. See `CELERY_SETUP.md` for what breaks if the worker isn't running (short version: uploads sit in `pending` forever, and appointment emails/notifications silently don't fire — the booking itself still succeeds).

---

## Frontend

| Layer | Technology | Notes |
|---|---|---|
| Framework | **React 18** | |
| Build tool | **Vite 5** | Dev server + production bundling |
| Routing | **react-router-dom v6** | Public widget route + `/admin/*` nested routes, including `/admin/business-management/:docPath` for the business-document type tables and `/admin/data-analyst` for the AI SQL analyst |
| HTTP client | **axios** | Two clients: `services/api.js` (public/customer) and `services/adminApi.js` (authenticated admin) |
| Markdown rendering | **react-markdown** + **remark-gfm** | Renders assistant replies (which may include lists/links/tables) |
| Styling | Plain CSS (`styles/index.css`), no CSS framework | One global stylesheet; business-document UI reuses the same design tokens/classes rather than introducing new ones |
| Real-time voice | Native **WebSocket** + **Web Audio API** (`AudioContext`, `AudioWorklet`, `getUserMedia`) | `realtime/deepgramClient.js` — mic capture, PCM encoding, and streaming playback, all without a dedicated media library |
| Linting | ESLint 8 + `eslint-plugin-react`/`react-hooks` | |

### Why connect the browser directly to Deepgram?
For the browser voice channel, the client gets a **short-lived ephemeral token** from the backend (`POST /voice/session`) and then talks to Deepgram's STT/TTS WebSockets *directly* — this avoids proxying raw audio through the backend twice (mic → backend → Deepgram → backend → speaker), cutting latency, which matters a lot for a natural-feeling voice conversation. The backend only ever sees **transcribed text**, never raw audio, on this path.

Phone calls are designed to work the same way in spirit but can't do the direct-connection trick (there's no browser to hand a token to) — for telephony the **backend itself** would hold a normal (non-ephemeral) Deepgram connection and bridge audio between Exotel and Deepgram. That code exists (see `VOICE_AND_TELEPHONY.md`) but isn't currently reachable — see the Status note in the README.

---

## Third-party services required to run everything

| Service | Used for | Required? |
|---|---|---|
| PostgreSQL (with `pgvector`) | All persistent data + RAG | Yes |
| Redis | Celery broker/result backend | Yes, for background processing (document uploads, KB indexing, email) to actually complete |
| OpenAI API key | Agent orchestration, all LLM calls, business-document classification/extraction (incl. vision) | Yes |
| Deepgram API key | STT + TTS for browser voice (phone calls not currently reachable — see Status) | Yes, for the browser voice feature |
| Exotel account + ExoPhone (Voicebot Applet enabled) | Real phone-call support | Code is written for this, but it isn't wired into the running app yet — see `VOICE_AND_TELEPHONY.md` |
| SMTP credentials | Outbound booking/cancellation/reschedule emails | Only if `MAIL_ENABLED=true` |
