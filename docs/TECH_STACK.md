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
| LLM provider | **Groq** (`llama-3.1-8b-instant` by default) via the `groq` SDK | Powers the agent orchestrator and all three agents' tool-calling loops |
| Alt. LLM provider | **OpenRouter** (`openai` SDK pointed at OpenRouter) | Configured but optional — `openrouter_*` settings in config.py |
| Embeddings | **sentence-transformers** (`multi-qa-MiniLM-L6-cos-v1`, 384-dim) | Runs locally (via `torch`/`transformers`) at document-ingestion and query time |
| Document parsing | `pypdf`, `python-docx` | Extracts text from uploaded PDF/DOCX knowledge-base files |
| Real-time voice/STT/TTS | **Deepgram** (`nova-2` STT, `aura-*` TTS voices) | Browser flow: ephemeral-token WS straight from the client. Phone flow: server-side WS via the `websockets` library |
| Telephony | **Exotel AgentStream** (Voicebot Applet) | Bidirectional WebSocket PSTN audio streaming — see `VOICE_AND_TELEPHONY.md` |
| Async WS client | `websockets` (17.x) | Used server-side only, for the telephony ↔ Deepgram bridge |
| Vector similarity | `pgvector` SQLAlchemy integration | Cosine-similarity search over `document_chunks.embedding` |
| Other notable deps | `qdrant-client` (present but pgvector is the active store), `tavily` (present, not wired into a route) | Listed in `requirements.txt`; not all are exercised by the current codepaths |

### Why Groq + local embeddings?
Groq gives fast, cheap Llama inference for the conversational/tool-calling loop, while embeddings run locally via `sentence-transformers` so there's no per-query embedding API cost or extra network hop for retrieval.

### Why pgvector instead of a dedicated vector DB?
The whole app already needs Postgres for relational data (appointments, customers, tickets, etc.); pgvector lets the RAG chunks live in the same database and transaction boundary as everything else, avoiding a second system to run/operate.

---

## Frontend

| Layer | Technology | Notes |
|---|---|---|
| Framework | **React 18** | |
| Build tool | **Vite 5** | Dev server + production bundling |
| Routing | **react-router-dom v6** | Public widget route + `/admin/*` nested routes |
| HTTP client | **axios** | Two clients: `services/api.js` (public/customer) and `services/adminApi.js` (authenticated admin) |
| Markdown rendering | **react-markdown** + **remark-gfm** | Renders assistant replies (which may include lists/links/tables) |
| Styling | Plain CSS (`styles/index.css`), no CSS framework | One global stylesheet |
| Real-time voice | Native **WebSocket** + **Web Audio API** (`AudioContext`, `AudioWorklet`, `getUserMedia`) | `realtime/deepgramClient.js` — mic capture, PCM encoding, and streaming playback, all without a dedicated media library |
| Linting | ESLint 8 + `eslint-plugin-react`/`react-hooks` | |

### Why connect the browser directly to Deepgram?
For the browser voice channel, the client gets a **short-lived ephemeral token** from the backend (`POST /voice/session`) and then talks to Deepgram's STT/TTS WebSockets *directly* — this avoids proxying raw audio through the backend twice (mic → backend → Deepgram → backend → speaker), cutting latency, which matters a lot for a natural-feeling voice conversation. The backend only ever sees **transcribed text**, never raw audio, on this path.

Phone calls can't do this (there's no browser to hand a token to), so for telephony the **backend itself** holds a normal (non-ephemeral) Deepgram connection and bridges audio between Exotel and Deepgram — see `VOICE_AND_TELEPHONY.md`.

---

## Third-party services required to run everything

| Service | Used for | Required? |
|---|---|---|
| PostgreSQL (with `pgvector`) | All persistent data + RAG | Yes |
| Groq API key | Agent orchestration / all LLM calls | Yes (or swap in OpenRouter) |
| Deepgram API key | STT + TTS for both browser voice and phone calls | Yes, for any voice feature |
| Exotel account + ExoPhone (Voicebot Applet enabled) | Real phone-call support | Only if `TELEPHONY_ENABLED=true` |
