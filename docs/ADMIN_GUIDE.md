# Admin Guide

## Logging in

There is no signup page — a single admin account is seeded automatically
the first time the backend starts, from `ADMIN_EMAIL` / `ADMIN_PASSWORD`
in `backend/.env`.

1. Set real values for `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `backend/.env`
   before your first run (defaults are placeholders and not secure).
2. Start the backend — the admin row is created automatically on startup
   (`app/db/init_db.py`).
3. Go to `http://localhost:5173/admin/login` and sign in.

### Rotating the password later

Editing `ADMIN_PASSWORD` in `.env` alone does **not** update an
already-seeded account. To rotate it:

1. Set the new `ADMIN_PASSWORD` in `.env`
2. Set `ADMIN_SEED_FORCE_UPDATE=true`
3. Restart the backend once
4. Set `ADMIN_SEED_FORCE_UPDATE=false` again (so future restarts don't
   keep overwriting it)

## Uploading documents

From the admin dashboard (`/admin`):

1. Click the upload area and choose a `.pdf` or `.docx` file (business
   info, price lists, policies, FAQs — anything you want the assistant to
   be able to answer from).
2. The file is processed immediately: text is extracted, split into
   chunks, embedded, and stored in Qdrant. You'll see its status move from
   **Pending → Processing → Completed** in the table, along with a chunk
   count.
3. If a document fails (e.g. a scanned PDF with no extractable text, or an
   unsupported `.doc` file), the row shows **Failed** with the error
   message — hover over it for details.

### Re-uploading the same file

If you upload a file whose content is byte-for-byte identical to one
already processed, nothing new is embedded — the existing record is
reused. This avoids piling up duplicate vectors from accidental re-uploads.

### Reindexing

Click **Reindex** on a row to force a full re-process of that file: its
existing vectors are deleted from Qdrant first, then it's re-extracted,
re-chunked, and re-embedded, with its version number incremented. Use this
after:

- Replacing the file's *content* but wanting to reuse the same row (in
  this scaffold, easiest is delete + re-upload — reindex is for re-running
  the *same* file through an updated pipeline)
- Changing `CHUNK_SIZE`, `CHUNK_OVERLAP`, or the embedding model in `.env`
- Suspecting the first processing run had a transient failure

### Deleting

Click **Delete** to remove a document entirely: its vectors are deleted
from Qdrant, its row is removed from Postgres, and the file is deleted
from disk. This can't be undone.

## What admins can't do yet

There's no UI for editing extracted text, browsing individual chunks, or
previewing what the assistant will retrieve for a given question — the
`VectorStoreService.search()` method backs all of that, so it's a matter
of adding an endpoint + UI on top of it, not building it from scratch.
