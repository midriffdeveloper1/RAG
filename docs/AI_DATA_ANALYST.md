# AI SQL & Data Analyst Agent

An **admin-only** agent that answers natural-language questions about business
documents by writing and running SQL, then explaining the result.

> "How many invoices did we receive last month?"
> "Which product generated the most revenue in the last 6 months?"

It is reachable at **Admin → Data analyst** (`/admin/data-analyst`). There is no
customer-facing equivalent, and no plan for one — see "Why admin-only".

---

## Scope

The agent can only see and query the **seven business document types**:

| Invoices | Receipts | Purchase orders | Resumes | Expense reports | Application forms | Contracts |
|---|---|---|---|---|---|---|

Anything else — appointments, staff, customers, chat conversations, salon
services, general knowledge — is refused with `status: "out_of_scope"` and a
short explanation of what it *can* answer.

This scope is not enforced by prompt instructions alone. The schema the agent is
shown, and the allowlist the SQL guard validates against, are the same
hand-written list in `app/services/analyst/schema_catalog.py`. Tables outside it
are invisible to the agent *and* rejected at validation time.

---

## Pipeline

```
admin question
   │
   ├─ 1. understand + inspect schema ── sql_generator.generate_sql_plan()
   │       LLM gets the allowlisted schema + recent conversation turns,
   │       returns JSON: {in_scope, intent, sql, chart_type, ...}
   │
   ├─ 2. VALIDATE ─────────────────── sql_guard.validate_sql()      ← hard boundary
   │       rejects anything non-SELECT, out-of-allowlist, or stacked
   │
   ├─ 3. execute ──────────────────── executor.execute_readonly()   ← hard boundary
   │       dedicated connection, SET TRANSACTION READ ONLY, 10s timeout
   │       └─ on SQL error: feed the DB's own message back, retry once
   │
   ├─ 4. analyze + answer ─────────── sql_generator.generate_answer()
   │       LLM writes 1-3 plain sentences from the actual result rows
   │
   └─ 5. optional chart ──────────── analyst_service._build_chart()
           only if the named columns exist and are numeric
```

Each step degrades gracefully: out-of-scope, too-vague, blocked, SQL error, and
empty-result all produce a useful reply rather than an error page — see
"Conversational tone" below for how those replies are written and shown.

---

## Conversational tone

The agent is meant to feel like a colleague who pulled up the numbers, not a
report generator or a system throwing errors. This shapes both the prompts and
the UI:

- **The answer prompt** (`ANSWER_SYSTEM_PROMPT`) asks for plain spoken English
  with contractions, varied sentence openings, and no throat-clearing
  ("Based on the data shows that…"). If the model made a reasonable assumption
  to answer the question — which date field it used, that "top" meant by
  revenue — it mentions that in passing as part of the answer rather than
  stopping to ask.
- **Clarifying questions are rare, not routine, and never look like an error.**
  The prompt instructs the model to use a sensible default whenever one exists,
  and only fall back to `needs_clarification` when two readings of the question
  would give meaningfully different answers with no reasonable default — e.g.
  "top product" when it's genuinely unclear whether that means by revenue or by
  units sold. When it does ask, it's phrased as one warm, specific question
  ("Quick check — by 'top product' do you mean revenue or units sold?"), never
  as "insufficient information" or a demand for more detail in the abstract.
- **Refusals stay warm.** Both the LLM's own `refusal_reason` for out-of-scope
  questions and the hardcoded fallback strings in `analyst_service.py` (used
  when the LLM call itself fails, or when the SQL guard blocks a query) avoid
  words like "error", "denied", or "invalid" and say what the agent *can* help
  with instead of dwelling on what it can't.
- **The UI doesn't add alarm the copy didn't ask for.** `needs_clarification`
  and `out_of_scope` messages render with the exact same plain avatar and
  styling as a normal answer — no warning icon, no colour tint — because
  they're just the assistant talking, not a problem. Only `blocked` (a safety
  refusal) and `error` (something genuinely failed) get a distinguishing
  avatar/tint, and even those use the app's own soft clay accent rather than a
  red or amber "alert" colour.
- **The "thinking" state doesn't narrate internals.** While a query runs, the
  UI shows a short natural phrase ("Let me pull that up…") rather than
  describing the pipeline ("inspecting the schema, writing a query…") — an
  admin doesn't need the mechanics, just a sign that something's happening.

---

## Safety — "no destructive SQL"

This is the task's hard requirement, so it is enforced at **two independent
layers**, either of which alone would be sufficient. Both would have to fail to
lose data.

### Layer 1 — `sql_guard.py` (validation)

- **Allowlist for tables.** Every `FROM`/`JOIN`/`INTO`/`UPDATE` target must be in
  `ALLOWED_TABLES`. An allowlist fails closed — blocklisting table names would be
  defeated by `pg_catalog`, `information_schema`, or any table added later.
- **Blocklist for keywords.** `INSERT UPDATE DELETE DROP TRUNCATE ALTER CREATE
  GRANT REVOKE COPY VACUUM CALL EXECUTE pg_sleep pg_read_file dblink` and ~30
  more are rejected as whole words *anywhere* in the statement, so they can't
  hide in a CTE or subquery.
- **Comments stripped before scanning**, so `SELECT 1 -- ; DROP TABLE x` and
  `/* */` obfuscation are normalised away instead of hiding keywords.
- **String literals masked before scanning**, so `WHERE category = 'delete'` is
  not a false positive while a real `DELETE` token is still caught.
- **Exactly one statement.** Content after the first `;` is rejected outright,
  killing stacked-query injection.
- Also rejects `SELECT ... INTO`, `FOR UPDATE`/`FOR SHARE` locking clauses, and
  schema-qualified names (`public.invoices`).
- **Table functions are allowlisted separately.** A relation in a `FROM`/`JOIN`
  position followed by `(` is a function call, not a table, and is checked
  against `ALLOWED_TABLE_FUNCTIONS` (`jsonb_array_elements_text`, `unnest`,
  `generate_series`, ...). This is needed to aggregate the JSON array columns
  (`resumes.skills`, `contracts.key_terms`), which can't be counted without
  expanding them into rows. `dblink(...)`, `pg_ls_dir(...)` and any unlisted
  function are rejected. `LATERAL` and `ONLY` are recognised as prefix keywords
  rather than mistaken for table names.
- **Row cap.** Every query gets a `LIMIT` (≤500); an existing larger `LIMIT` is
  clamped, and a non-trailing `LIMIT` causes the query to be wrapped.

CTE names defined by `WITH x AS (...)` are collected first and exempted from the
table allowlist, since they're query-local and not real tables.

### Layer 2 — `executor.py` (execution)

- **A dedicated connection.** Agent SQL never runs on the request's session.
  `execute_readonly()` deliberately takes no `Session` argument and opens its own
  from `SessionLocal()`.
- **`SET TRANSACTION READ ONLY`.** Postgres itself refuses any write. This was
  verified empirically by bypassing the guard entirely and sending
  `DELETE FROM invoices` — the database refused it (`cannot execute DELETE in a
  read-only transaction`) and the row count was unchanged.
- **`statement_timeout = 10s`**, so a pathological join can't pin a connection.
- **Always rolled back, never committed**, and the connection is always closed.

### What the admin sees

A blocked query never surfaces the raw SQL or the guard's internal reason. The
admin gets a plain message that the request is outside what the assistant may do;
the detail (including the offending SQL) goes to the server log at WARNING.

---

## Query quality

The prompt in `sql_generator.py` pushes for efficient, readable SQL:

- **Aggregate in SQL** (`SUM`/`COUNT`/`GROUP BY`) — never return raw rows for the
  app to add up.
- **Readable snake_case aliases** on every output column, because those aliases
  become the table headers the admin reads.
- Round money, `COALESCE` nullable amounts, explicit `JOIN ... ON`, no
  `SELECT *` in a final answer, `ORDER BY ... DESC LIMIT N` for "top N".
- Filter out failed extractions (`status IN ('completed','needs_review')`)
  unless the question is about failures.

### The enum trap (important)

`business_document_uploads.status` and `.document_type` are declared in
SQLAlchemy as `Enum(BusinessDocumentStatus)` / `Enum(BusinessDocumentType)`.
SQLAlchemy stores the enum **member names**, not their values, so the labels
actually in Postgres are **UPPERCASE**:

```
status:        PENDING, PROCESSING, COMPLETED, NEEDS_REVIEW, FAILED
document_type: INVOICE, RECEIPT, PURCHASE_ORDER, RESUME,
               EXPENSE_REPORT, APPLICATION_FORM, CONTRACT, UNKNOWN
```

The Python enum *values* are lowercase (`"completed"`), which makes this an easy
trap: `WHERE status IN ('completed')` raises
`invalid input value for enum businessdocumentstatus`. The schema catalog and
prompt both document the uppercase labels and mandate a text cast:

```sql
WHERE bdu.status::text IN ('COMPLETED', 'NEEDS_REVIEW')
WHERE bdu.document_type::text = 'INVOICE'
```

The prompt also notes that a `document_type` filter is usually redundant — the
`invoices` table only contains invoices — so the join to
`business_document_uploads` is only needed for `uploaded_at` or `status`.

### The date trap (important)

Document date columns (`invoice_date`, `transaction_date`, `po_date`,
`expiration_date`, ...) are **`TEXT`, not `DATE`** — see
`DATABASE_ARCHITECTURE.md`. Real extractions contain nulls, empty strings, and
OCR junk like `"N/A"`. A bare `invoice_date::date` throws
`invalid input syntax for type date` and **fails the entire query on one bad
row** — this was reproduced against seeded data, not theorised.

So the prompt mandates a format guard before every cast:

```sql
WHERE invoice_date ~ '^\d{4}-\d{2}-\d{2}$'
  AND invoice_date::date >= date_trunc('month', CURRENT_DATE - interval '1 month')
```

`business_document_uploads.uploaded_at` *is* a real timestamp and needs no guard,
so the prompt prefers it for "when did we receive/process" questions and uses the
document's own date field for "what date is printed on it" questions.

**Self-repair.** If a query still fails, the PostgreSQL error is fed back to the
model with the broken SQL for one retry (`MAX_SQL_REPAIR_ATTEMPTS = 1`).

Postgres error messages say what's *invalid* but not what's *valid*, so a blind
retry tends to repeat the same class of mistake — observed in practice, where a
lowercase-enum failure retried into another lowercase-enum failure.
`AnalystService._repair_hint()` therefore supplies the missing half, attaching a
targeted correction for enum-label, TEXT-date-cast, and unknown-column errors.

---

## Conversation understanding

Follow-ups work because each turn's prompt includes the last 8 turns **and the
actual SQL from previous assistant turns**. That means "break that down by month"
extends the real previous query rather than re-deriving filters from prose.

```
Admin: Which vendor invoiced us the most last quarter?
Admin: break that down by month        ← reuses the previous quarter filter
Admin: what about receipts?            ← carries the time range to a new table
```

Threads are persisted, listed in a left rail, and can be reopened or deleted.

---

## Charts

Charts are the exception, not the default, enforced at **two layers**:

1. **The prompt** tells the model to default to `chart_type: "none"` and only
   ask for a chart when comparing 3+ categories or a 3+ point trend — explicitly
   listing what NOT to chart: single totals, one ranked answer, a list of
   records to read (e.g. "which contracts expire soon"), yes/no questions.
2. **`_build_chart()` verifies the choice against the real result** regardless
   of what the model asked for: the named columns must exist in the result, at
   least 3 rows are required (2 categories don't need a picture — that's the
   case people complain about most), most values must be numeric, and the
   values must actually vary — a chart where every bar is the same height has
   no shape worth showing, so it's dropped. A `pie` with more than 6 rows is
   downgraded to `bar`.

This means a model asking for a chart on a 2-row or flat result — or
hallucinating a column name — quietly degrades to "table only" instead of a
chart nobody needed or a broken one.

Charts are hand-rolled inline SVG (`AnalystChart.jsx`) in the admin theme's
sage/clay palette. No charting library was added — the project had no chart
dependency, and three simple shapes on one admin page didn't justify the bundle.

---

## Result formatting

Results adapt to their shape rather than always rendering a grid:

| Result shape | Rendering |
|---|---|
| 1 row × 1 column | Large headline **metric** card — the answer isn't buried in a 1×1 table |
| 1 row × N columns | **Definition list**, so the admin reads down instead of scrolling sideways |
| N rows × N columns | **Sortable table** |

Column presentation is inferred from both the column name and a sample of its
values (`utils/analystFormat.js`):

- `total_revenue` → `1,234.56`, right-aligned, `font-variant-numeric: tabular-nums`
  so decimal points line up down the column
- `invoice_count` → `1,234` (no decimals)
- `confidence_score` (0..1) → `92%`
- `2026-03-01` → `Mar 2026` (month buckets), `16 Sep 2026` (real dates)
- JSON arrays (`skills`, `key_terms`) → comma-joined
- `null` → a dimmed `—`, never the string "null"
- Headers: `total_revenue` → `Total revenue`

Tables show 8 rows with a "show more" toggle, are sortable by any column (nulls
always sort last, since absence isn't a low value), and export to **CSV**.

The generated SQL is available behind a "View SQL" toggle with execution timing
and a copy button, so the admin can always audit exactly what ran.

---

## API

All routes require an authenticated admin (`get_current_admin`) and are scoped by
`admin_id`, so one admin cannot read another's threads by guessing an ID.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/admin/analyst/scope` | Document types in scope + starter questions |
| POST | `/api/v1/admin/analyst/ask` | `{question, session_id?}` — omit `session_id` to start a thread |
| GET | `/api/v1/admin/analyst/sessions` | Paginated thread list |
| GET | `/api/v1/admin/analyst/sessions/{id}` | Full thread with results |
| DELETE | `/api/v1/admin/analyst/sessions/{id}` | Delete a thread |

`POST /ask` returns `status`: `ok` | `out_of_scope` | `needs_clarification` |
`blocked` | `error`. Returns **503** if `OPENAI_API_KEY` isn't configured,
matching the existing `/chat` behaviour.

### Why admin-only

The agent composes SQL over the whole document corpus. A customer-facing version
would let an untrusted party steer query generation across every business's
invoices, resumes, and contracts — the allowlist limits *which tables* are
reachable, not *whose rows*. Keeping it behind admin auth avoids that entirely.

---

## Files

**Backend**
```
app/services/analyst/
├── schema_catalog.py    # hand-written table/column allowlist + prompt rendering
├── sql_guard.py         # validation — the hard safety boundary
├── executor.py          # read-only execution on a dedicated connection
├── sql_generator.py     # prompts: question -> SQL plan, result -> answer
└── analyst_service.py   # orchestration, repair loop, chart verification

app/models/analyst_session.py     # AnalystSession + AnalystMessage
app/schemas/analyst.py
app/api/routes/analyst.py
alembic/versions/c3f7a91b4de2_analyst_sessions.py
```

**Frontend**
```
src/pages/admin/AdminDataAnalystPage.jsx
src/components/Analyst/
├── AnalystMessage.jsx       # answer + chart + table + SQL inspector
├── AnalystResultTable.jsx   # metric / record / sortable table + CSV
└── AnalystChart.jsx         # inline SVG bar, line, pie
src/utils/analystFormat.js   # column type inference + value formatting
```

### Storage

`analyst_sessions` / `analyst_messages` are separate from `chat_sessions`
deliberately. That table models a *customer* support conversation
(`browser_id`, `customer_id`, escalation, `ticket_number`) and is surfaced in the
admin Conversations page; mixing internal SQL threads into it would put queries
into the customer conversation review UI. Assistant messages store a snapshot of
the result (columns, rows, chart) so reopening a thread shows what the admin
originally saw, rather than re-running against data that may since have changed.

---

## Setup

No new dependencies and no new environment variables. It uses the existing
`OPENAI_API_KEY` and database connection. Just run the migration:

```bash
cd backend
alembic upgrade head
```

Then open **Admin → Data analyst**.