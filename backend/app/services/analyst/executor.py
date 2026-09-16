"""
Executes guard-approved SQL against a hardened, read-only connection.

Even though `sql_guard` has already rejected anything non-SELECT, this layer
assumes the guard could be bypassed and makes writes impossible at the database
level:

- **A dedicated connection.** Agent-generated SQL never runs on the request's
  own session. That session holds uncommitted conversation records, and the
  rollbacks below would discard them — but more importantly, isolating the
  connection means the one place arbitrary SQL executes is a connection that
  has no pending writes on it and is always thrown away afterwards.
- `SET TRANSACTION READ ONLY` — Postgres itself refuses any write, so a guard
  bypass still cannot mutate data.
- `statement_timeout` — a pathological join can't pin a connection forever.
- The transaction is always rolled back, never committed.
"""

from __future__ import annotations

import decimal
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

STATEMENT_TIMEOUT_MS = 10_000


class QueryExecutionError(RuntimeError):
    """Raised when the query fails to execute."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    duration_ms: int


def _to_jsonable(value: Any) -> Any:
    """Normalise driver types into something JSON-serialisable and display-ready."""
    if value is None or isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, decimal.Decimal):
        # float() keeps it numeric for the frontend's formatting/charting,
        # which matters more here than exact decimal fidelity for display.
        return float(value)

    if isinstance(value, float):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, (list, dict)):
        return value

    return str(value)


def execute_readonly(
    sql: str,
    max_rows: int = 500,
    timeout_ms: int = STATEMENT_TIMEOUT_MS,
) -> QueryResult:
    """
    Run a guard-approved SELECT on a throwaway read-only connection.

    Deliberately takes no Session argument: the caller must not be able to hand
    in a session carrying pending writes, because this function rolls back
    unconditionally and would silently discard them.
    """
    started = time.perf_counter()
    db = SessionLocal()

    try:
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))

        result = db.execute(text(sql))
        columns = list(result.keys())

        # Fetch one extra row so we can tell "exactly at the cap" apart from
        # "there was more data we didn't show".
        fetched = result.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = fetched[:max_rows]

        payload = [[_to_jsonable(value) for value in row] for row in rows]

    except SQLAlchemyError as exc:
        logger.warning("Analyst query failed: %s", exc)

        # Surface only the database's own message, not the full driver traceback.
        detail = str(getattr(exc, "orig", exc)).strip().splitlines()
        raise QueryExecutionError(detail[0] if detail else "Query execution failed.") from exc

    finally:
        # Never commit — this path is read-only by construction — and always
        # hand the connection back to the pool.
        db.rollback()
        db.close()

    duration_ms = int((time.perf_counter() - started) * 1000)

    return QueryResult(
        columns=columns,
        rows=payload,
        row_count=len(payload),
        truncated=truncated,
        duration_ms=duration_ms,
    )
