# RAG Pipeline — Phase 1 (done) & Phase 2 (roadmap)

This document explains how ingestion works today, and exactly what's left
to build a working chat assistant on top of it.

---

## Phase 1 — Ingestion pipeline (COMPLETE)

Everything below is implemented and runnable today.

```
Admin uploads PDF/DOCX
        │
        ▼
POST /api/v1/admin/documents/upload   (JWT-protected)
        │
        ▼
DocumentService.save_upload()
  - streams file to disk in 1MB chunks (app/uploads/)
  - computes SHA-256 content hash
  - rejects disallowed extensions / oversized files
        │
        ▼
Duplicate check: DocumentService.find_completed_duplicate()
  - if this exact file content was already processed → return the
    existing record, skip re-embedding
        │
        ▼
Document row created (status=PENDING) in Postgres
        │
        ▼
DocumentService.process_document()
  - status → PROCESSING
  - document_processor.extract_text()   (pypdf for .pdf, python-docx for .docx)
  - document_processor.chunk_text()     (overlapping character chunks,
                                          breaks on paragraph/sentence bounds)
  - vector_store.upsert_document_chunks()
        │
        ▼
embedding_service.embed_batch()
  - sentence-transformers, local model (all-MiniLM-L6-v2, 384-dim)
  - no external API key needed
  - batched (EMBEDDING_BATCH_SIZE) to bound memory on large documents
        │
        ▼
Qdrant: points upserted with payload
  { document_id, chunk_index, text, source, version }
        │
        ▼
Document row updated: status=COMPLETED, chunk_count, processed_at
```

### Reindexing & memory management

| Scenario | What happens |
|---|---|
| Re-upload of **identical** file content | Detected via SHA-256 `content_hash`; the existing `COMPLETED` document is returned, nothing is re-embedded, no duplicate file is kept on disk. |
| Admin clicks **Reindex** | `VectorStoreService.delete_by_document_id()` removes every Qdrant point with that `document_id` (filtered delete, not point-ID guessing) → `version` is bumped → the file is reprocessed from disk. |
| Admin clicks **Delete** | Vectors deleted from Qdrant, DB row deleted, file removed from disk. Nothing orphaned. |
| Changed chunking/embedding config | No automatic migration — click **Reindex** on each document to re-chunk/re-embed it under the new settings. |

Why filtered delete instead of tracking point IDs? Qdrant point IDs are
random UUIDs generated at upsert time; the `document_id` payload field
(with a payload index for speed) is the stable handle across re-processing,
so delete-then-upsert is safe and idempotent no matter how many chunks a
document produces on each run.

### What you can do right now

- Log in as the seeded admin (`/admin/login`)
- Upload a PDF or DOCX
- Watch it move `PENDING → PROCESSING → COMPLETED` with a real chunk count
- Call `VectorStoreService.search("your question")` directly (e.g. from a
  Python shell) and get back real, relevant chunks — retrieval genuinely
  works today, it's just not exposed as a chat answer yet.

---

## Phase 2 — Retrieval-augmented answer generation (COMPLETE)

Chat is now fully wired end to end: question → retrieval → relevance
filtering → Groq generation → answer.

```
User asks a question (React chat widget)
        │
        ▼
POST /api/v1/chat   { question, session_id }
        │
        ▼
RAGService.retrieve_context()
  - embeds the question (same local model as ingestion)
  - VectorStoreService.search() → top RETRIEVAL_TOP_K chunks + similarity scores
        │
        ▼
RAGService._is_out_of_domain()
  - no chunks, OR best score < RELEVANCE_SCORE_THRESHOLD
        │                                   │
        │ no (in-domain)                    │ yes (out-of-domain)
        ▼                                   ▼
RAGService.generate_answer()        Polite refusal returned directly —
  - builds a grounded system         no LLM call made. See
    prompt from the retrieved        OUT_OF_DOMAIN_MESSAGE in
    chunks + business identity       rag_service.py.
  - calls Groq (llm_service.py)
        │
        ▼
ChatResponse { answer, sources, session_id }
        │
        ▼
Frontend renders the answer in the chat widget
```

### Out-of-domain / off-topic handling

This is enforced in **two layers**, not just prompt instructions:

1. **Retrieval-score gate** (`RAGService._is_out_of_domain`) — if nothing
   relevant enough was retrieved (cosine similarity below
   `RELEVANCE_SCORE_THRESHOLD`, default `0.35`), the backend returns a
   fixed polite message *without calling the LLM at all*. This is
   deterministic, costs nothing, and can't be talked out of by a cleverly
   phrased question.
2. **System-prompt instructions** (`SYSTEM_PROMPT_TEMPLATE` in
   `rag_service.py`) — as a second line of defense, even when *some*
   context is retrieved, the model is explicitly instructed to answer only
   from that context and to decline anything unrelated to the business.

Both layers use the business name from `BUSINESS_NAME` in `.env`, so the
refusal message and prompt stay consistent with whichever business this
scaffold is configured for.

### Tuning the relevance threshold

`RELEVANCE_SCORE_THRESHOLD` (default `0.35`) is the main knob:

- **Too low** → off-topic or barely-related questions get answered from
  weak matches, sometimes with a shaky or misleading answer.
- **Too high** → legitimate questions get refused because their best
  matching chunk didn't score quite high enough.

There's no universally correct value — it depends on your embedding model
and how your documents are chunked. Recommended process: collect a set of
real questions (in-domain and out-of-domain), log the retrieval scores for
each (`RAGService.retrieve_context()` returns them), and pick a threshold
that separates the two groups well. Re-check it whenever you change
`CHUNK_SIZE`/`CHUNK_OVERLAP` or the embedding model, since scores shift
with both.

### Groq configuration

Set in `backend/.env`:

```
GROQ_API_KEY=       # required — get one free at https://console.groq.com/keys
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TEMPERATURE=0.3
GROQ_MAX_TOKENS=600
```

If `GROQ_API_KEY` is missing, `POST /chat` returns `503` with a clear
error message rather than a generic `500` — see `llm_service.py`.

### What's still open (Phase 3 ideas, not required)

- **Streaming** — Groq supports streaming responses; the current
  implementation waits for the full answer before returning. Worth adding
  for a snappier UX on longer answers.
- **Real multi-turn memory** — `session_id` is threaded through the whole
  stack already, but each question is currently answered independently.
  To add memory: store prior turns (Postgres or in-memory cache) keyed by
  `session_id`, and include recent history in the prompt.
- **Citations in the UI** — `ChatResponse.sources` already carries the
  source filename + score for every chunk used; the frontend doesn't
  surface it yet. Easy addition to `ChatMessage.jsx`.
- **Evaluation** — keep a fixed set of test questions (the ones from the
  original project brief are a good start) and re-run them after any
  prompt, threshold, or chunking change to catch regressions.