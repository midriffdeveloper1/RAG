# Celery Setup & Run Book

This project uses **Celery** (task queue) + **Redis** (broker/result backend)
to run everything slow or LLM-backed in the background instead of blocking
an API request:

- Business document extraction (invoice/receipt/.../contract — the LLM call)
- Knowledge-base document chunking + embedding + vector upsert
- Outbound email (booking confirmations, cancellations, reschedules)

None of this is optional infrastructure bolted on the side — the upload and
appointment endpoints now enqueue these as tasks rather than doing the work
inline, so **a worker needs to be running** for uploads/emails to actually
finish (see "What breaks without a worker" below).

---

## 1. Install Redis

Celery needs a running Redis instance as the broker (and, here, the result
backend too).

**Windows** — easiest is Docker:
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```
(No Docker? Use the Memurai or WSL2 Redis builds — anything speaking the
Redis protocol on `localhost:6379` works.)

**macOS**:
```bash
brew install redis
brew services start redis
```

**Linux**:
```bash
sudo apt install redis-server
sudo systemctl enable --now redis-server
```

Verify it's up:
```bash
redis-cli ping   # -> PONG
```

## 2. Configure

In `backend/.env`:
```
REDIS_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=false
```

`CELERY_TASK_ALWAYS_EAGER=true` runs tasks synchronously in-process with no
worker/Redis needed at all — handy for a quick local check, but defeats the
point (everything blocks again). Leave it `false` except for that.

If Redis lives somewhere other than `localhost:6379`, or you want separate
broker/result-backend URLs, set `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`
explicitly — both default to `REDIS_URL` if unset.

## 3. Install the Python packages

> ⚠️ **Not actually in `requirements.txt` yet**, despite this section previously saying so — `celery` and `redis` are used throughout `app/core/celery_app.py`, `app/tasks/*`, and are imported wherever `.delay(...)` is called, but neither package is listed in `backend/requirements.txt` in this snapshot. Install them explicitly until that's fixed:

```bash
cd backend
pip install -r requirements.txt
pip install celery redis
```

## 4. Run a worker

From the `backend/` directory, with your virtualenv active:

**macOS / Linux:**
```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

**Windows** — the default "prefork" pool isn't supported. Use the solo pool:
```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
```
(`--pool=solo` runs one task at a time in the worker process — fine for
local dev; for real concurrency on Windows use `--pool=threads` instead, or
just run the worker inside WSL2.)

Leave this running in its own terminal alongside `uvicorn`. You should see
the three task modules register on startup:
```
[tasks]
  . business_documents.process
  . knowledge_base.process_document
  . knowledge_base.reindex_document
  . mail.send
```

## 5. (Optional) Run the FastAPI app and worker together

Two terminals, both from `backend/`:
```bash
# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo   # Windows
celery -A app.core.celery_app.celery_app worker --loglevel=info               # macOS/Linux
```

## 6. (Optional) Flower — a web UI for watching tasks

```bash
pip install flower
celery -A app.core.celery_app.celery_app flower --port=5555
```
Then open `http://localhost:5555` to see queued/running/failed tasks live —
useful while testing uploads and appointment emails.

---

## What breaks without a worker running

| Action | What happens with no worker | What happens once a worker is up |
|---|---|---|
| Upload a business document | Row is created and stays `pending` forever | Row moves `pending → processing → completed/needs_review/failed` within seconds |
| Upload a KB document | Same — stays `pending`, chatbot can't answer from it | Chunked + embedded, ready for RAG |
| Book/cancel/reschedule an appointment | The booking itself still works (that part isn't queued) — but no confirmation/cancellation email goes out and no admin notification fires for it, since those are dispatched via `send_email_task.delay(...)` | Email sends, admin notification appears in the bell |

The API never blocks waiting on a worker — `.delay(...)` just drops the task
onto the Redis queue and returns immediately. If Redis itself isn't
reachable, `.delay()` will raise a connection error at the call site (visible
in the FastAPI logs) rather than hanging.

---

## Task reference

| Task name | Module | Triggered by |
|---|---|---|
| `business_documents.process` | `app.tasks.business_document_tasks` | `POST /admin/business-documents/upload`, `POST /{id}/reprocess` |
| `knowledge_base.process_document` | `app.tasks.knowledge_base_tasks` | `POST /admin/documents/upload` |
| `knowledge_base.reindex_document` | `app.tasks.knowledge_base_tasks` | `POST /admin/documents/{id}/reindex` |
| `mail.send` | `app.tasks.mail_tasks` | `AppointmentService` on book/cancel/reschedule/admin edits — sends the customer email via `mail_service.py`/`mail_templates.py` and, separately, creates the matching admin `Notification` row |

All document-processing tasks retry up to twice (15s backoff) on unexpected
exceptions (e.g. a transient LLM timeout); `mail.send` retries up to 3 times
(20s backoff). Retries are visible in Flower or the worker's log output.

## Task routing / queues

Two logical queues are configured in `app/core/celery_app.py`:
- `documents` — business-document + KB tasks (the slow, LLM/embedding work)
- `mail` — outbound email

A single worker with no `-Q` flag consumes both by default. If you want to
scale document processing and mail separately later, run dedicated workers:
```bash
celery -A app.core.celery_app.celery_app worker -Q documents --loglevel=info
celery -A app.core.celery_app.celery_app worker -Q mail --loglevel=info
```