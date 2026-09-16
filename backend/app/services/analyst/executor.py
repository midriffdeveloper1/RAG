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
    if value is None or isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, decimal.Decimal):
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
    started = time.perf_counter()
    db = SessionLocal()

    try:
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))

        result = db.execute(text(sql))
        columns = list(result.keys())

        fetched = result.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = fetched[:max_rows]

        payload = [[_to_jsonable(value) for value in row] for row in rows]

    except SQLAlchemyError as exc:
        logger.warning("Analyst query failed: %s", exc)
        detail = str(getattr(exc, "orig", exc)).strip().splitlines()
        raise QueryExecutionError(detail[0] if detail else "Query execution failed.") from exc

    finally:
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
