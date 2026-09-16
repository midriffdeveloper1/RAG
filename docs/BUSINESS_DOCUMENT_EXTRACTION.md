# Phase: Business Document Intelligence

> ## ⚠️ Doc vs. code — read this first
>
> This document was written while the feature used a single generic `BusinessDocument` table (`business_documents`, with `extracted_data` stored as a JSON blob — see §2.1 below). **The code has since moved on to a normalized, per-document-type schema** and this doc wasn't fully updated to match. Specifically:
>
> - The live models are `app/models/business_documents/upload.py` (`BusinessDocumentUpload`, table `business_document_uploads`) plus one child table per type (`invoices`, `receipts`, `purchase_orders`, `resumes`, `expense_reports`, `application_forms`, `contracts`, plus their line-item tables) — see `DATABASE_ARCHITECTURE.md` for the full list. `app/services/business_documents/persistence.py` reads/writes these.
> - `app/models/business_document.py` (singular, described in §2.1) is the **old** design. It's still in the tree and still has a live migration history, but current code (`service.py`, `extraction.py`, `routes/business_documents.py`, and `alembic/env.py`) doesn't use it as the source of truth anymore. A few lower-level helpers (`scoring.py`, `validation.py`, `field_schemas.py`) still import the `BusinessDocumentType` enum *from that old file* rather than from `business_documents/upload.py` — harmless today because the two enums have identical values, but worth reconciling.
> - The migration referenced in §2.1 (`b1a1e6c9f3d2_business_documents.py`, chained on `65c81363ab75`) **does not match the actual migration files in this repo** — the real business-document migrations are `62d8b09cd61e_business_doc.py` and `5b541868256e_business_doc.py` (see `DATABASE_ARCHITECTURE.md` for the real chain).
> - §2.3 describes the vision path as going through **OpenRouter** (`OPENROUTER_VISION_MODEL`, a vision-capable OpenRouter model). The live `LLMService` (`app/services/llm_service.py`) is OpenAI-only — `generate_json_with_image` uses `settings.openai_vision_model` (default `gpt-5.4-mini`) via the OpenAI SDK, not OpenRouter. Set `OPENAI_API_KEY`/`OPENAI_VISION_MODEL`, not `OPENROUTER_*`.
> - §6 says `app/models/business_document.py` and one migration are the only new backend model files — in the current tree there are also the eight files under `app/models/business_documents/` and a second migration, as noted above.
>
> Everything else in this document — the field-schema-driven design in §2.2, the extraction/validation/scoring/orchestration flow in §2.3–§2.6, the API surface in §2.7, and the whole of §3 (frontend) — still accurately describes how the feature behaves; only the underlying storage shape and LLM provider have moved on from what's written below.

**What this phase adds:** an AI pipeline that takes uploaded business documents
(invoices, receipts, purchase orders, resumes, expense reports, application
forms, contracts) and turns them into structured, validated, database-backed
records — completely separate from the chatbot's RAG knowledge base.

---

## 1. Why a separate module (not another RAG upload)

The existing `/admin/documents` flow (`Document` / `DocumentChunk` /
`DocumentService`) exists to feed the chatbot's retrieval pipeline: text gets
chunked, embedded, and stored as vectors so the support agent can answer
questions from it.

That's the wrong shape for this phase. An invoice isn't a paragraph the
chatbot should quote — it's a record with a number, a vendor, a total, and
line items that a human (or another system) needs to query, audit, and
correct. So this phase introduces a **parallel, independent pipeline**:

| | Knowledge base (existing) | Business documents (this phase) |
|---|---|---|
| Model | `Document`, `DocumentChunk` | `BusinessDocument` |
| Output | Embedded text chunks in pgvector | Structured JSON fields in Postgres |
| Consumed by | RAG retrieval → chatbot answers | Admin table views, exports, corrections |
| Service | `DocumentService` | `BusinessDocumentService` |
| Route prefix | `/admin/documents` | `/admin/business-documents` |
| Storage folder | `app/uploads/` | `app/uploads/business_documents/` |

Nothing in this phase calls `vector_store`, `embedding_service`, or
`document_extraction_service` (the business-onboarding extractor). The two
pipelines share only the low-level PDF/DOCX text-extraction helper
(`document_processor.extract_text`), reused as-is.

---

## 2. Backend

### 2.1 Data model — `app/models/business_document.py`

`BusinessDocument` stores, per uploaded file:

- File metadata: `original_filename`, `stored_filename`, `file_path`,
  `file_type`, `file_size_bytes`, `content_hash` (dedupe, same pattern as the
  KB `Document` model).
- Classification: `document_type` (enum: `invoice | receipt | purchase_order
  | resume | expense_report | application_form | contract | unknown`),
  `type_confidence`, `requested_document_type` (what the uploader expected,
  if uploaded from a specific type's page — kept for audit, not blindly
  trusted).
- Processing: `status` (`pending | processing | completed | needs_review |
  failed`), `error_message`.
- Extraction results: `extracted_data` (JSON — the structured fields),
  `field_confidence` (JSON — 0–1 per field), `confidence_score` (overall
  0–1).
- Validation results: `is_valid`, `validation_errors` (JSON list of
  `{field, message}`), `missing_fields` (JSON list of field names).
- `reviewed` — flips to `true` once an admin manually edits a field.

Migration: `alembic/versions/b1a1e6c9f3d2_business_documents.py`, chained
onto your current head (`65c81363ab75`). Run `alembic upgrade head` before
using this phase.

### 2.2 Field schemas — `app/services/business_documents/field_schemas.py`

Single source of truth for what each of the 7 document types looks like:
field name, type (`string | date | number | email | phone | list |
object_list | object`), whether it's required, and its display label.
`object_list` fields (e.g. an invoice's `line_items`, a resume's
`experience`) carry their own sub-schema.

This schema dict drives three things at once, so they can't drift apart:
1. The LLM extraction prompt (built from the schema, so the model only ever
   extracts fields we actually store).
2. Validation (which fields are required, what "valid" means per type).
3. What gets persisted (any key the LLM invents outside the schema is
   dropped before saving).

### 2.3 Extraction — `app/services/business_documents/extraction.py`

One LLM call classifies **and** extracts in a single pass (cheaper than two
round-trips), returning:

```json
{
  "document_type": "invoice",
  "type_confidence": 0.94,
  "fields": { "invoice_number": "INV-1042", "total_amount": 452.10, ... },
  "field_confidence": { "invoice_number": 0.97, "total_amount": 0.9, ... }
}
```

Two entry points, both funnel into the same prompt/parsing logic:

- `extract_from_text(text, expected_type)` — for PDF/DOCX/DOC files with a
  text layer (via `pypdf` / `python-docx`, already in the project).
- `extract_from_image(image_bytes, mime_type, expected_type)` — for
  JPG/PNG/WEBP (a phone photo of a receipt, a scanned form). Sent as a
  base64 data URL to a **vision-capable** OpenRouter model, since the
  project's default chat model isn't guaranteed to support images. This
  required a small addition to `LLMService`
  (`generate_json_with_image`) — additive, doesn't touch any existing method.

If a PDF has no extractable text (i.e. it's actually a scan with no text
layer), the service raises a clear error asking the user to upload it as an
image instead — there's no OCR/PDF-rasterization library in this project
(`pytesseract`/`pdf2image` + poppler aren't installed), so that's the
honest boundary for this phase. See §5 for how to extend this.

### 2.4 Validation — `app/services/business_documents/validation.py`

Given a document type and the extracted `fields` dict, returns
`(is_valid, errors, missing_fields)`:

- Missing required field → added to `missing_fields`.
- Present but wrong shape (bad date, non-numeric amount, malformed
  email/phone, `line_items` not a list, a list item missing a required
  sub-field) → added to `errors` with a human-readable message.
- Soft cross-field check: if `subtotal`, `tax_amount`, and `total_amount`
  are all present, flags it when they don't add up (catches OCR/extraction
  slips even when every individual field "looks" valid).

### 2.5 Confidence scoring — `app/services/business_documents/scoring.py`

Combines the LLM's per-field confidence with whether the field is actually
present and required:

- Required fields are weighted 2× optional fields.
- A field in `missing_fields` always contributes **0**, regardless of what
  the LLM felt about the document as a whole — so the score reflects how
  usable the record actually is, not just how legible the source looked.

### 2.6 Orchestration — `app/services/business_documents/service.py`

`BusinessDocumentService` mirrors the existing `DocumentService`'s shape
(`save_upload` → `create_document_record` → `process_document`) so it's
familiar to anyone who's touched the KB uploader, but every step writes to
`BusinessDocument` instead and never calls the vector store:

1. `save_upload` — streams to disk in 1MB chunks, sha256 hash, size/type
   validation, own upload directory.
2. `create_document_record` — inserts a `PENDING` row.
3. `process_document` — extracts text or reads image bytes → runs
   extraction → validates → scores confidence → sets `status` to
   `completed` (valid) or `needs_review` (extracted but missing/invalid
   fields) → commits.
4. `apply_manual_correction` — admin-edited fields are merged in, marked
   confidence `1.0` (ground truth), re-validated, and `reviewed=True` is
   set. Never re-sent to the LLM.
5. `find_completed_duplicate` — same content hash re-upload returns the
   existing record instead of reprocessing.

### 2.7 API — `app/api/routes/business_documents.py`

All under `/api/v1/admin/business-documents`, admin-auth protected (same
`get_current_admin` dependency as every other admin route):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/upload` | Multi-file upload (`files: list[UploadFile]`, ≤15/batch). Optional `?document_type=invoice` hint. Returns one result per file, including files that failed to even save. |
| `GET` | `` | Paginated list, filterable by `document_type` and `status`. |
| `GET` | `/summary` | Per-type counts (total / needs review / failed) for a dashboard. |
| `GET` | `/{id}` | Full record incl. extracted data, confidence, validation. |
| `PATCH` | `/{id}` | `{ "fields": {...} }` — manual correction of one or more fields. |
| `POST` | `/{id}/reprocess` | Re-run extraction against the stored file. |
| `DELETE` | `/{id}` | Delete the record and its file. |

Registered in `app/main.py` alongside the existing routers.

### 2.8 Config additions — `app/core/config.py` / `.env.example`

Additive only, nothing existing was changed in shape:

```
BUSINESS_DOCUMENT_UPLOAD_DIR=app/uploads/business_documents
BUSINESS_DOCUMENT_MAX_UPLOAD_SIZE_MB=20
BUSINESS_DOCUMENT_ALLOWED_EXTENSIONS=.pdf,.jpg,.jpeg,.png,.webp,.docx,.doc
BUSINESS_DOCUMENT_MAX_FILES_PER_BATCH=15
OPENROUTER_VISION_MODEL=google/gemini-2.0-flash-001
```

`OPENROUTER_VISION_MODEL` defaults to a reasonable OpenRouter vision model
but should be reviewed against your actual OpenRouter budget/access before
going live — swap it for whatever vision model you're provisioned for.

---

## 3. Frontend

### 3.1 Sidebar

Added **one** new sidebar icon — "Business management" (`FolderKanban`) —
as a collapsible group, per your instruction not to add a separate icon per
document type. Expanding it shows:

- **Upload documents** (its own page, own icon)
- A small "Document records" sub-heading
- One link per document type (Invoices, Receipts, Purchase Orders, Resumes,
  Expense Reports, Application Forms, Contracts), each with its own small
  icon, indented under the group.

The group auto-expands when you're already on one of its routes, and
remembers your manual toggle otherwise (`components/layout/AdminSidebar.jsx`).

### 3.2 Upload is its own page, separate from the record tables

Per your requirement #4, uploading is **not** bundled into a type's table
page:

- `pages/admin/BusinessManagement/BusinessDocumentUploadPage.jsx` — the one
  place to upload. Multi-file drag-and-drop, accepts PDF/JPG/PNG/WEBP/DOC/DOCX,
  shows a live per-file batch result (detected type, confidence, validity,
  missing fields) right after upload, plus a reference grid of what each
  document type extracts.
- `pages/admin/BusinessManagement/BusinessDocumentTypePage.jsx` — one route
  (`/admin/business-management/:docPath`) reused for all 7 types via the
  shared config in `config/businessDocumentTypes.js`. Pure record table +
  a "Upload {type}s" button that deep-links back to the upload page.

### 3.3 Components (`components/BusinessDocuments/`)

- `BusinessDocumentUploadZone.jsx` — the drag/drop + click uploader with
  batch results, reusable (used stand-alone on the Upload page).
- `BusinessDocumentTable.jsx` — paginated table (reuses the existing
  `useServerPagination` hook, `Pagination`, `EmptyState`, `icon-button`
  patterns from the KB document list) with a "key details" column built
  from `getHeadline()` (a per-type shortlist of the most useful fields,
  e.g. invoice number + vendor + total) so the table is scannable without
  opening every row.
- `BusinessDocumentDetailModal.jsx` — full extracted-field view. Shows a
  confidence meter per field, flags missing/invalid fields inline, and lets
  an admin correct any scalar field in place (saves via `PATCH`,
  re-validates immediately). Also exposes "Re-run extraction" and "Delete".
- `FieldValue.jsx` — generic renderer for whatever shape a field has: plain
  text/number, a chip list (skills, key terms), a mini-table (line items,
  work experience, education), or a nested object (application form's
  catch-all `additional_fields`). This means the UI never needs a
  per-document-type template — the same modal renders all 7 types correctly
  because it just walks whatever `extracted_data` came back.
- `BusinessDocumentStatusBadge.jsx` / `ConfidenceMeter.jsx` — small reusable
  bits matching the existing `status-badge` visual language, extended with
  a `needs_review` variant.

### 3.4 Styling

Everything reuses the existing design tokens (`--color-primary`,
`--color-accent`, `--radius-*`, the `data-table` / `status-badge` /
`icon-button` / `empty-state` classes already in `styles/index.css`) —
no new color palette, no new component library. New rules were appended to
the end of `index.css` rather than touching existing blocks.

### 3.5 API client — `services/adminApi.js`

Six new functions added (`uploadBusinessDocuments`, `listBusinessDocuments`,
`getBusinessDocument`, `updateBusinessDocument`, `reprocessBusinessDocument`,
`deleteBusinessDocument`, `getBusinessDocumentsSummary`), following the exact
calling convention every other function in that file already uses.

---

## 4. End-to-end flow

```
Admin selects files (Upload page, or a type page's "Upload" button)
        │
        ▼
POST /admin/business-documents/upload  (multipart, up to 15 files)
        │
        ▼
BusinessDocumentService.save_upload      → file streamed to disk + sha256 hash
        │
        ▼
BusinessDocumentService.process_document
        │
        ├─ PDF/DOCX/DOC → extract_text() → extraction.extract_from_text()
        ├─ JPG/PNG/WEBP  → read bytes    → extraction.extract_from_image()
        │
        ▼
   LLM: classify type + extract fields + per-field confidence
        │
        ▼
   validate_fields()  → is_valid, validation_errors, missing_fields
   compute_confidence() → overall confidence_score
        │
        ▼
   BusinessDocument row saved (status: completed / needs_review / failed)
        │
        ▼
Admin sees it in the batch result immediately, and in the matching
type's table (Invoices / Receipts / etc.) going forward. Never touches
the RAG vector store at any point.
```

---

## 5. Known limitations & natural next steps

- **Scanned PDFs with no text layer aren't OCR'd.** The service detects this
  and asks the user to re-upload as an image instead of silently failing.
  To close this gap: add `pdf2image` + poppler (or `pymupdf`) to rasterize
  the first page and route it through the same `extract_from_image` path
  already built for photos.
- **Legacy `.doc` files** hit the same `UnsupportedFileTypeError` the
  existing KB pipeline already has (python-docx can't read the old binary
  format). Same TODO as the existing code: convert via
  `libreoffice --headless --convert-to docx` first, or reject at upload.
- **`OPENROUTER_VISION_MODEL`** ships with a sensible default but you should
  confirm it against what your OpenRouter account actually has access to
  before relying on photo uploads in production.
- **Bulk export / CSV download** of a type's table isn't built yet — the
  data's all there in `extracted_data`, so this is a pure frontend addition
  when you want it.
- **Line-item and other nested-array fields aren't editable** in the detail
  modal yet (only top-level scalar fields are, by design for this phase) —
  correcting a line item today means re-running extraction or editing the
  source file and re-uploading.

---

## 6. Files touched

**New (backend):**
```
app/models/business_document.py
app/schemas/business_document.py
app/services/business_documents/__init__.py
app/services/business_documents/field_schemas.py
app/services/business_documents/validation.py
app/services/business_documents/scoring.py
app/services/business_documents/extraction.py
app/services/business_documents/service.py
app/api/routes/business_documents.py
alembic/versions/b1a1e6c9f3d2_business_documents.py
```

**Modified (backend):** `app/models/__init__.py`, `app/main.py`,
`app/core/config.py`, `app/services/llm_service.py` (added
`generate_json_with_image`, nothing removed/changed), `.env.example`.

**New (frontend):**
```
src/config/businessDocumentTypes.js
src/utils/businessDocuments.js
src/components/BusinessDocuments/BusinessDocumentUploadZone.jsx
src/components/BusinessDocuments/BusinessDocumentTable.jsx
src/components/BusinessDocuments/BusinessDocumentDetailModal.jsx
src/components/BusinessDocuments/FieldValue.jsx
src/components/BusinessDocuments/BusinessDocumentStatusBadge.jsx
src/components/BusinessDocuments/ConfidenceMeter.jsx
src/pages/admin/BusinessManagement/BusinessDocumentUploadPage.jsx
src/pages/admin/BusinessManagement/BusinessDocumentTypePage.jsx
```

**Modified (frontend):** `src/App.jsx` (routes), `src/components/layout/AdminSidebar.jsx`
(new group), `src/components/common/Icons.jsx` (new icons, additive),
`src/services/adminApi.js` (new functions, additive), `src/styles/index.css`
(new rules appended at the end).

**Incidental fixes** (pre-existing bugs found while verifying the build —
unrelated to this phase but were blocking `npm run build` on this
case-sensitive filesystem): renamed `Adminlogin.jsx` → `AdminLogin.jsx` and
`Documentlist.jsx` → `DocumentList.jsx` to match their import statements.

---

## 7. Setup checklist

1. `alembic upgrade head` (creates `business_document_uploads` and the
   per-type tables — see the status note at the top of this doc for the
   real migration IDs).
2. Set `OPENAI_API_KEY` and confirm/adjust `OPENAI_MODEL`/`OPENAI_VISION_MODEL`
   in `.env` (this pipeline is OpenAI-backed, not OpenRouter — see the
   status note at the top of this doc).
3. Make sure a Celery worker is running (`CELERY_SETUP.md`) — uploads are
   processed via `process_business_document_task`, not inline; without a
   worker they'll stay `pending`.
4. Restart the backend — no other migration/seed steps needed.
5. In the admin panel: **Business management → Upload documents**, drop in
   a few sample files, then check the matching type's table.