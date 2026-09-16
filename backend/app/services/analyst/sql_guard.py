from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.analyst.schema_catalog import ALLOWED_TABLES

# Statement types that may never appear, in any position.
FORBIDDEN_KEYWORDS: frozenset[str] = frozenset(
    {
        # DML / DDL
        "insert", "update", "delete", "drop", "truncate", "alter", "create",
        "replace", "rename", "merge", "upsert",
        # permissions / session
        "grant", "revoke", "set", "reset", "session", "role",
        # execution / escalation
        "call", "do", "execute", "prepare", "declare", "listen", "notify",
        "copy", "vacuum", "analyze", "cluster", "reindex", "refresh",
        "lock", "commit", "rollback", "savepoint", "begin", "start",
        # extension / file access
        "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "lo_import",
        "lo_export", "dblink", "pg_sleep", "pg_terminate_backend",
    }
)

# Schemas/prefixes that must never be touched even if someone adds a table
# with a colliding name to the catalog.
FORBIDDEN_SCHEMA_PREFIXES: tuple[str, ...] = ("pg_", "information_schema")

MAX_QUERY_LENGTH = 6000


class UnsafeSQLError(ValueError):
    """Raised when generated SQL fails validation. Never shown raw to the user."""


@dataclass
class GuardResult:
    sql: str
    tables: list[str]
    limit_applied: int | None


def _strip_comments(sql: str) -> str:
    """Remove -- line comments and /* */ block comments."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def _mask_string_literals(sql: str) -> str:
    """
    Replace the contents of quoted literals with a placeholder so keyword
    scanning can't be fooled by (or trip over) literal text.
    """
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r'"(?:[^"]|"")*"', '""', sql)
    return sql


def _split_single_statement(sql: str) -> str:
    """
    Enforce exactly one statement. A single trailing semicolon is fine;
    anything with content after it is a stacked query.
    """
    parts = [part for part in sql.split(";")]

    if len(parts) > 1 and any(part.strip() for part in parts[1:]):
        raise UnsafeSQLError("Only a single SQL statement is allowed.")

    return parts[0].strip()


ALLOWED_TABLE_FUNCTIONS: frozenset[str] = frozenset(
    {
        "jsonb_array_elements_text",
        "json_array_elements_text",
        "jsonb_array_elements",
        "json_array_elements",
        "jsonb_each_text",
        "json_each_text",
        "unnest",
        "generate_series",
        "regexp_split_to_table",
    }
)

_RELATION_PREFIX_KEYWORDS: frozenset[str] = frozenset({"lateral", "only"})

_RELATION_REF_RE = re.compile(
    r"\b(?:from|join|into|update)\s+"
    r"(?:(?:lateral|only)\s+)*"  
    r"((?:[a-zA-Z_][\w$]*\s*\.\s*)?[a-zA-Z_][\w$]*)"
    r"\s*(\()?", 
    re.IGNORECASE,
)


def _extract_referenced_relations(sql: str) -> tuple[set[str], set[str]]:

    tables: set[str] = set()
    functions: set[str] = set()

    for match in _RELATION_REF_RE.finditer(sql):
        raw = re.sub(r"\s+", "", match.group(1)).lower()

        if raw in _RELATION_PREFIX_KEYWORDS:
            continue

        if match.group(2):
            functions.add(raw)
        else:
            tables.add(raw)

    return tables, functions


def _collect_cte_names(sql: str) -> set[str]:

    names: set[str] = set()

    for match in re.finditer(
        r"(?:\bwith\b|,)\s+([a-zA-Z_][\w$]*)\s+as\s*(?:materialized\s*|not\s+materialized\s*)?\(",
        sql,
        re.IGNORECASE,
    ):
        names.add(match.group(1).lower())

    return names


def _apply_limit(sql: str, max_rows: int) -> tuple[str, int | None]:

    existing = re.search(r"\blimit\s+(\d+)\s*$", sql, re.IGNORECASE)

    if existing:
        requested = int(existing.group(1))

        if requested <= max_rows:
            return sql, requested

        clamped = re.sub(r"\blimit\s+\d+\s*$", f"LIMIT {max_rows}", sql, flags=re.IGNORECASE)
        return clamped, max_rows

    if re.search(r"\blimit\b", sql, re.IGNORECASE):
        return f"SELECT * FROM (\n{sql}\n) AS analyst_capped LIMIT {max_rows}", max_rows

    return f"{sql}\nLIMIT {max_rows}", max_rows


def validate_sql(raw_sql: str, max_rows: int = 500) -> GuardResult:

    if not raw_sql or not raw_sql.strip():
        raise UnsafeSQLError("No SQL was generated.")

    if len(raw_sql) > MAX_QUERY_LENGTH:
        raise UnsafeSQLError("Generated SQL is unreasonably long.")

    sql = raw_sql.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)

    cleaned = _strip_comments(sql)
    cleaned = _split_single_statement(cleaned)

    if not cleaned:
        raise UnsafeSQLError("No SQL was generated.")

    # Must be a read: SELECT, or WITH ... SELECT.
    if not re.match(r"^\s*(select|with)\b", cleaned, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    masked = _mask_string_literals(cleaned)
    tokens = set(re.findall(r"[a-zA-Z_][\w$]*", masked.lower()))

    forbidden_hits = tokens & FORBIDDEN_KEYWORDS
    if forbidden_hits:
        raise UnsafeSQLError(
            f"Query contains a forbidden operation: {', '.join(sorted(forbidden_hits))}."
        )

    # `SELECT ... INTO new_table` writes; catch it explicitly since INTO is
    # also legitimate in other dialects' contexts.
    if re.search(r"\binto\b", masked, re.IGNORECASE):
        raise UnsafeSQLError("SELECT ... INTO is not allowed.")

    # FOR UPDATE / FOR SHARE take row locks.
    if re.search(r"\bfor\s+(update|share|no\s+key\s+update|key\s+share)\b", masked, re.IGNORECASE):
        raise UnsafeSQLError("Locking clauses are not allowed.")

    cte_names = _collect_cte_names(masked)
    referenced, table_functions = _extract_referenced_relations(masked)

    for function in sorted(table_functions):
        if function in cte_names:
            continue

        if function not in ALLOWED_TABLE_FUNCTIONS:
            raise UnsafeSQLError(
                f"Function '{function}' is not permitted in a FROM/JOIN position."
            )

    real_tables: list[str] = []

    for table in sorted(referenced):
        if table in cte_names:
            continue

        if any(table.startswith(prefix) for prefix in FORBIDDEN_SCHEMA_PREFIXES):
            raise UnsafeSQLError("System catalog access is not allowed.")

        if "." in table:
            raise UnsafeSQLError("Schema-qualified table names are not allowed.")

        if table not in ALLOWED_TABLES:
            raise UnsafeSQLError(
                f"Table '{table}' is outside the scope this assistant can query."
            )

        real_tables.append(table)

    if not real_tables:
        raise UnsafeSQLError("Query does not reference any in-scope business document table.")

    limited_sql, limit_applied = _apply_limit(cleaned, max_rows)

    return GuardResult(sql=limited_sql, tables=real_tables, limit_applied=limit_applied)