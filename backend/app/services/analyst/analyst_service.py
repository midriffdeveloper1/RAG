"""
The AI SQL & Data Analyst agent.

Pipeline per question:

    understand -> inspect schema -> generate SQL -> VALIDATE -> execute
               -> analyze result -> natural-language answer (+ optional chart)

Every step is recoverable: an out-of-scope question, an unsafe query, a SQL
error, or an empty result each produce a useful reply rather than a stack trace.
"""

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
    status: str  # "ok" | "out_of_scope" | "needs_clarification" | "blocked" | "error"
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
    """
    Charts are the exception, not the default — most answers read better as a
    sentence and a table. This is the second (and stricter) gate on top of the
    prompt's own "default to none" instruction: even when the model asks for a
    chart, we only actually draw one when the result genuinely has a shape
    worth looking at.
    """
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

    # A trend needs at least 3 points to show direction; a comparison needs at
    # least 3 categories to be worth a picture rather than just reading two
    # numbers off the table. Two rows is exactly the case people complain
    # about — a chart with two bars says nothing a sentence didn't already.
    min_rows = 3
    if len(rows) < min_rows:
        return None

    value_index = columns.index(value)

    numeric_values = [
        row[value_index]
        for row in rows
        if isinstance(row[value_index], (int, float)) and not isinstance(row[value_index], bool)
    ]

    # Require most values to be numeric; a stray null shouldn't kill the chart.
    if len(numeric_values) < max(3, int(len(rows) * 0.6)):
        return None

    # If every value is effectively the same, a chart just shows a flat line
    # of identical bars — there's no shape to see, so it isn't worth drawing.
    if max(numeric_values) - min(numeric_values) == 0:
        return None

    chart_type = plan.chart_type
    if chart_type == "pie" and len(rows) > 6:
        chart_type = "bar"

    return ChartSpec(type=chart_type, label_column=label, value_column=value)


class AnalystService:
    """
    Note there is no `db` on this service. Query execution deliberately opens
    its own read-only connection (see `executor.execute_readonly`) so that
    agent-generated SQL never touches the request's session, which is holding
    the uncommitted conversation records.
    """

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> AnalystAnswer:
        question = (question or "").strip()

        if not question:
            return AnalystAnswer(
                answer=(
                    "What would you like to know? I can total things up, rank "
                    "vendors or products, break spend down by category, or check "
                    "what's expiring soon — just ask."
                ),
                status="needs_clarification",
            )

        # --- 1. Understand + generate -------------------------------------
        try:
            plan = sql_generator.generate_sql_plan(question, history)
        except RuntimeError as exc:
            # LLMService raises this when no API key is configured.
            raise
        except ValueError as exc:
            logger.warning("Analyst planning failed: %s", exc)
            return AnalystAnswer(
                answer=(
                    "Hmm, I'm not quite following that one — mind rephrasing it? "
                    "It helps if you name a document type and roughly what time "
                    "period you're interested in."
                ),
                status="error",
            )

        if not plan.in_scope:
            # The prompt already asks the model for one warm, complete sentence
            # that names what it *can* help with — appending the same list again
            # would make it read like a form letter. Only add the fallback list
            # when the model didn't give us a reason to work with.
            answer = plan.refusal_reason or (
                "That's a bit outside what I can help with — I only work with "
                "your document records: invoices, receipts, purchase orders, "
                "resumes, expense reports, application forms, and contracts."
            )
            return AnalystAnswer(answer=answer, status="out_of_scope")

        if plan.clarification and not plan.sql:
            return AnalystAnswer(answer=plan.clarification, status="needs_clarification")

        if not plan.sql:
            return AnalystAnswer(
                answer="I couldn't quite turn that into a lookup — could you say it a different way?",
                status="error",
            )

        # --- 2. Validate + 3. Execute (with one repair attempt) -----------
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
                        "I had to stop myself there — that one either reached for data "
                        "outside your document records or wanted to change something, "
                        "and I only ever read from invoices, receipts, and the rest. "
                        "Try rephrasing it and I'll take another pass."
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
                            "I put together a query for that, but it didn't come back "
                            "cleanly — usually that means the data isn't shaped quite "
                            "the way the question assumes. Try narrowing it a bit, "
                            "like naming a specific document type or date range."
                        ),
                        status="error",
                        sql=guarded.sql,
                        intent=plan.intent,
                    )

                logger.info("Retrying analyst SQL after error: %s", last_error)

                repaired = self._repair_sql(question, current_sql, last_error, history)

                if not repaired:
                    return AnalystAnswer(
                        answer="I couldn't quite land that one — could you try phrasing it differently?",
                        status="error",
                        intent=plan.intent,
                    )

                current_sql = repaired

        # --- 4. Analyze + 5. Answer ---------------------------------------
        try:
            answer_text = sql_generator.generate_answer(
                question=question,
                intent=plan.intent,
                columns=result.columns,
                rows=result.rows,
                truncated=result.truncated,
            )
        except Exception as exc:  # noqa: BLE001 - never lose a good result to a bad summary
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
        """
        Postgres error messages say what's invalid but not what's valid, so a
        blind retry tends to repeat the same class of mistake. These hints
        supply the missing half.
        """
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
        """Deterministic answer used when the summarising LLM call fails."""
        if not rows:
            return "Came up empty — nothing matched that."

        if len(rows) == 1 and len(columns) == 1:
            return f"{columns[0].replace('_', ' ').capitalize()}: {rows[0][0]}"

        return f"Found {len(rows)} matching record(s) — take a look below."
