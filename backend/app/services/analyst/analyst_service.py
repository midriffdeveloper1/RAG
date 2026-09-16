from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.analyst import sql_generator
from app.services.analyst.executor import QueryExecutionError, execute_readonly
from app.services.analyst.sql_guard import UnsafeSQLError, validate_sql

logger = logging.getLogger(__name__)

MAX_ROWS = 500
MAX_SQL_REPAIR_ATTEMPTS = 1


@dataclass
class ChartSpec:
    type: str
    label_column: str
    value_column: str


@dataclass
class AnalystAnswer:
    answer: str
    status: str  
    sql: str | None = None
    intent: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    duration_ms: int | None = None
    chart: ChartSpec | None = None
    tables_used: list[str] = field(default_factory=list)


def _build_chart(
    plan: sql_generator.SQLPlan,
    columns: list[str],
    rows: list[list[Any]],
) -> ChartSpec | None:

    if plan.chart_type == "none":
        return None

    label = plan.chart_label_column
    value = plan.chart_value_column

    if not label or not value:
        return None

    if label not in columns or value not in columns:
        logger.info(
            "Skipping chart: columns %s/%s not in result %s", label, value, columns
        )
        return None

    if len(rows) < 2:
        return None

    value_index = columns.index(value)

    numeric_count = sum(
        1
        for row in rows
        if isinstance(row[value_index], (int, float)) and not isinstance(row[value_index], bool)
    )

    
    if numeric_count < max(2, int(len(rows) * 0.6)):
        return None

    chart_type = plan.chart_type
    if chart_type == "pie" and len(rows) > 6:
        chart_type = "bar"

    return ChartSpec(type=chart_type, label_column=label, value_column=value)


class AnalystService:

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> AnalystAnswer:
        question = (question or "").strip()

        if not question:
            return AnalystAnswer(
                answer="Ask me a question about your business documents and I'll look it up.",
                status="needs_clarification",
            )

        try:
            plan = sql_generator.generate_sql_plan(question, history)
        except RuntimeError as exc:
            raise
        except ValueError as exc:
            logger.warning("Analyst planning failed: %s", exc)
            return AnalystAnswer(
                answer=(
                    "I had trouble interpreting that question. Could you rephrase it, "
                    "or be a bit more specific about which documents and time period "
                    "you mean?"
                ),
                status="error",
            )

        if not plan.in_scope:
            reason = plan.refusal_reason or (
                "I can only answer questions about your business documents."
            )
            return AnalystAnswer(
                answer=(
                    f"{reason} I can help with invoices, receipts, purchase orders, "
                    "resumes, expense reports, application forms, and contracts."
                ),
                status="out_of_scope",
            )

        if plan.clarification and not plan.sql:
            return AnalystAnswer(answer=plan.clarification, status="needs_clarification")

        if not plan.sql:
            return AnalystAnswer(
                answer=(
                    "I wasn't able to turn that into a specific query. Could you rephrase it?"
                ),
                status="error",
            )

        attempt = 0
        last_error: str | None = None
        current_sql = plan.sql

        while True:
            try:
                guarded = validate_sql(current_sql, max_rows=MAX_ROWS)
            except UnsafeSQLError as exc:
                logger.warning(
                    "Blocked unsafe SQL for question %r: %s | sql=%r",
                    question,
                    exc,
                    current_sql,
                )
                return AnalystAnswer(
                    answer=(
                        "I can't run that query — it falls outside what this assistant is "
                        "allowed to do. I can only read from your business document tables, "
                        "and I can't modify any data."
                    ),
                    status="blocked",
                    intent=plan.intent,
                )

            try:
                result = execute_readonly(guarded.sql, max_rows=MAX_ROWS)
                break
            except QueryExecutionError as exc:
                last_error = str(exc)
                attempt += 1

                if attempt > MAX_SQL_REPAIR_ATTEMPTS:
                    logger.warning("Analyst query failed after repair: %s", last_error)
                    return AnalystAnswer(
                        answer=(
                            "I built a query for that but it didn't run successfully. "
                            "This usually means the data isn't in the shape the question "
                            "assumes. Try narrowing it down — for example, naming a "
                            "specific document type or date range."
                        ),
                        status="error",
                        sql=guarded.sql,
                        intent=plan.intent,
                    )

                logger.info("Retrying analyst SQL after error: %s", last_error)

                repaired = self._repair_sql(question, current_sql, last_error, history)

                if not repaired:
                    return AnalystAnswer(
                        answer=(
                            "I couldn't build a working query for that question. "
                            "Could you rephrase it?"
                        ),
                        status="error",
                        intent=plan.intent,
                    )

                current_sql = repaired

        try:
            answer_text = sql_generator.generate_answer(
                question=question,
                intent=plan.intent,
                columns=result.columns,
                rows=result.rows,
                truncated=result.truncated,
            )
        except Exception as exc:  
            logger.warning("Answer generation failed, falling back: %s", exc)
            answer_text = self._fallback_answer(result.columns, result.rows)

        chart = _build_chart(plan, result.columns, result.rows)

        return AnalystAnswer(
            answer=answer_text,
            status="ok",
            sql=guarded.sql,
            intent=plan.intent,
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            duration_ms=result.duration_ms,
            chart=chart,
            tables_used=guarded.tables,
        )

    def _repair_sql(
        self,
        question: str,
        broken_sql: str,
        error: str,
        history: list[dict[str, str]] | None,
    ) -> str | None:
        """Feed the database's own error back to the model for one retry."""
        repair_note = (
            f"{question}\n\n"
            f"[SYSTEM] Your previous query failed with this PostgreSQL error:\n"
            f"{error}\n\n"
            f"Previous query:\n{broken_sql}\n\n"
            f"{self._repair_hint(error)}"
            "Return a corrected query that avoids this error."
        )

        try:
            plan = sql_generator.generate_sql_plan(repair_note, history)
        except (ValueError, RuntimeError) as exc:
            logger.warning("SQL repair attempt failed: %s", exc)
            return None

        return plan.sql or None

    @staticmethod
    def _repair_hint(error: str) -> str:
        lowered = error.lower()

        if "invalid input value for enum" in lowered:
            return (
                "FIX: enum labels are UPPERCASE. Use "
                "bdu.status::text IN ('COMPLETED','NEEDS_REVIEW') and "
                "bdu.document_type::text = 'INVOICE' (valid statuses: PENDING, "
                "PROCESSING, COMPLETED, NEEDS_REVIEW, FAILED). Better still, drop "
                "the filter entirely if the question doesn't depend on it.\n\n"
            )

        if "invalid input syntax for type date" in lowered or "date/time field" in lowered:
            return (
                "FIX: document date columns are TEXT and contain unparseable "
                "values. Guard every cast with "
                "`col ~ '^\\d{4}-\\d{2}-\\d{2}$'` before using `col::date`.\n\n"
            )

        if "does not exist" in lowered and "column" in lowered:
            return (
                "FIX: that column does not exist. Re-read the schema above and "
                "use only the listed column names.\n\n"
            )

        return ""

    @staticmethod
    def _fallback_answer(columns: list[str], rows: list[list[Any]]) -> str:
        if not rows:
            return "No matching documents were found for that question."

        if len(rows) == 1 and len(columns) == 1:
            return f"{columns[0].replace('_', ' ').capitalize()}: {rows[0][0]}"

        return f"Found {len(rows)} matching row(s). The details are in the table below."