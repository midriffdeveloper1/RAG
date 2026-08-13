# Phase 2 Update — Chat Answer Generation (Groq)

This package contains only the **new and modified** files for Phase 2.
Drop them into your existing project at the same relative paths (they'll
overwrite the Phase-1 stub versions).

## New files
- `backend/app/services/llm_service.py` — Groq client wrapper
- `docs/RAG_PIPELINE.md` — Phase 2 section rewritten to document what was
  actually built (was a plan, now a reference)

## Modified files
- `backend/app/core/config.py` — added Groq, retrieval, and business
  identity settings
- `backend/app/services/rag_service.py` — `generate_answer()` implemented;
  added relevance-score-based out-of-domain detection
- `backend/app/api/routes/chat.py` — no longer a stub; handles missing
  `GROQ_API_KEY` with a clear `503` instead of a generic error
- `backend/app/main.py` — chat router now registered
- `backend/requirements.txt` — added `groq`
- `backend/.env.example` — added `GROQ_API_KEY`, `GROQ_MODEL`,
  `RETRIEVAL_TOP_K`, `RELEVANCE_SCORE_THRESHOLD`, `BUSINESS_NAME`,
  `BUSINESS_DESCRIPTION`
- `frontend/src/services/api.js` — `sendChatMessage()` now calls the real
  `POST /chat` endpoint
- `frontend/src/hooks/useChat.js` — passes a per-session id, handles the
  `503` (missing API key) case with a clearer error message
- `README.md` — status table updated to reflect Phase 2 completion

## What you need to do

1. **Copy the files** into your project at matching paths.
2. **Add to `backend/.env`** (not committed — copy from `.env.example`):
   ```
   GROQ_API_KEY=gsk_...          # https://console.groq.com/keys
   GROQ_MODEL=llama-3.1-8b-instant
   GROQ_TEMPERATURE=0.3
   GROQ_MAX_TOKENS=600
   RETRIEVAL_TOP_K=5
   RELEVANCE_SCORE_THRESHOLD=0.35
   BUSINESS_NAME=Serenity Salon & Spa
   BUSINESS_DESCRIPTION=boutique hair, beauty, and wellness salon
   ```
3. **Install the new dependency**:
   ```
   pip install groq
   ```
4. **Restart the backend.** `POST /chat` is now live and registered.
5. **No frontend install needed** — `sendChatMessage()` was already called
   by the existing chat widget; only its implementation changed.

## How the out-of-domain refusal works (quick version)

Every question is retrieved against Qdrant first. If nothing relevant
enough comes back (best similarity score below `RELEVANCE_SCORE_THRESHOLD`,
default `0.35`), the backend returns a polite fixed refusal **without
calling Groq at all** — deterministic and free. If relevant context *is*
found, it's passed to Groq inside a system prompt that also instructs the
model to decline anything unrelated to the business as a second line of
defense. Full details, including how to tune the threshold, are in
`docs/RAG_PIPELINE.md` under "Phase 2".