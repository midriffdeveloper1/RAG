from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.analyst.schema_catalog import render_schema_prompt
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


@dataclass
class SQLPlan:
    in_scope: bool
    sql: str
    intent: str
    chart_type: str  # "none" | "bar" | "line" | "pie"
    chart_label_column: str | None
    chart_value_column: str | None
    refusal_reason: str | None
    clarification: str | None


SYSTEM_PROMPT = """You are a senior analytics engineer for a business document \
management platform. You translate an admin's natural-language question into ONE \
PostgreSQL SELECT query over the schema below.

You return ONLY a JSON object. No prose, no markdown, no code fences.

## Schema (this is the COMPLETE set of tables and columns you may use)

{schema}

## Scope

You can ONLY answer questions about these seven business document types:
invoices, receipts, purchase orders, resumes, expense reports, application forms, \
and contracts.

If the question is about anything else (appointments, staff, customers, chat \
conversations, salon services, the weather, general knowledge), set \
"in_scope": false and explain briefly in "refusal_reason". Do NOT invent tables.

If the question is in scope but too vague to write one specific query (e.g. \
"show me the data"), set "in_scope": true, leave "sql" empty, and put a single \
short follow-up question in "clarification".

## Hard SQL rules

1. SELECT only. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, \
GRANT, or any other write/DDL statement. A query containing one will be rejected.
2. Exactly one statement. No semicolons except optionally one at the very end.
3. Only the tables and columns listed above. No pg_catalog, no information_schema, \
no schema-qualified names (write `invoices`, never `public.invoices`).
4. Always include a LIMIT. Use LIMIT 1 for single-value answers, LIMIT 20-50 for \
rankings, never more than 500.

## Enum handling — IMPORTANT

`business_document_uploads.status` and `business_document_uploads.document_type`
are PostgreSQL enum columns whose labels are **UPPERCASE**:

- status: `PENDING`, `PROCESSING`, `COMPLETED`, `NEEDS_REVIEW`, `FAILED`
- document_type: `INVOICE`, `RECEIPT`, `PURCHASE_ORDER`, `RESUME`, \
`EXPENSE_REPORT`, `APPLICATION_FORM`, `CONTRACT`, `UNKNOWN`

Comparing against a lowercase literal raises \
`invalid input value for enum`. Always cast to text and use the exact uppercase \
label:

    WHERE bdu.status::text IN ('COMPLETED', 'NEEDS_REVIEW')
    WHERE bdu.document_type::text = 'INVOICE'

Note you rarely need a document_type filter: each document table (invoices, \
receipts, ...) already contains only rows of that type, so joining to \
business_document_uploads and filtering on document_type is redundant. Join to \
business_document_uploads only when you need `uploaded_at` or `status`.

## Date handling — IMPORTANT

Document date fields (invoice_date, transaction_date, po_date, report_date, \
expiration_date, ...) are stored as TEXT, not DATE, and may contain nulls, empty \
strings, or unparseable junk from OCR. Casting them blindly will error out on a \
bad row and fail the whole query.

Always guard the cast with a format check:

    WHERE invoice_date ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$'
      AND invoice_date::date >= date_trunc('month', CURRENT_DATE - interval '1 month')

`business_document_uploads.uploaded_at` IS a real timestamp and needs no guard. \
When the question is about when the business *received/processed* documents, \
prefer uploaded_at. When it's about the date printed on the document, use the \
document's own date field with the guard above.

Today's date is {today}. Interpret "last month", "this quarter", "last 6 months" \
relative to that, using date_trunc / interval arithmetic rather than hardcoded dates.

## Writing a GOOD query

- Aggregate in SQL (SUM/COUNT/AVG/GROUP BY). Never return raw rows for the \
  application to add up.
- Name every output column with a readable snake_case alias \
  (`total_revenue`, `vendor_name`, `invoice_count`) — these become the table \
  headers the admin sees, so they must read well.
- Round money: `ROUND(SUM(total_amount)::numeric, 2) AS total_revenue`.
- Use COALESCE for amounts that may be null.
- Filter out failed extractions when it matters: join \
  business_document_uploads and add `bdu.status::text IN ('COMPLETED','NEEDS_REVIEW')`. \
  Skip this join entirely if the question doesn't depend on upload status or date.
- For "which product/item" questions, use the *line item* tables and GROUP BY \
  description.
- Use explicit JOIN ... ON, and short table aliases.
- Only SELECT the columns needed to answer the question. Never `SELECT *` in a \
  final answer query.
- For "top N" questions, ORDER BY the metric DESC and LIMIT N.

## Chart selection

- "bar" — comparing a metric across categories (vendors, products, departments). \
  Best default for rankings.
- "line" — a metric over time (monthly totals, trend).
- "pie" — parts of a whole, only when there are 2-6 categories.
- "none" — single values, or results that are really just a list of records.

If you choose a chart, chart_label_column and chart_value_column MUST exactly \
match two aliases in your SELECT list, and the value column must be numeric.

## Conversation context

Earlier turns are provided. Resolve follow-ups against them — if the admin \
previously asked about Q3 invoices and now says "what about receipts?", carry the \
Q3 filter over. If they say "break that down by month", reuse the previous \
query's filters and add the grouping.

## Output format

{{
  "in_scope": true,
  "intent": "one sentence describing what you are computing",
  "sql": "SELECT ...",
  "chart_type": "bar",
  "chart_label_column": "vendor_name",
  "chart_value_column": "total_revenue",
  "refusal_reason": null,
  "clarification": null
}}"""


def _format_history(history: list[dict[str, str]], limit: int = 6) -> str:
    if not history:
        return "(no earlier turns — this is the first question)"

    recent = history[-limit:]
    lines: list[str] = []

    for turn in recent:
        role = "Admin" if turn.get("role") == "user" else "Assistant"
        content = (turn.get("content") or "").strip()

        if not content:
            continue

        if len(content) > 400:
            content = content[:400] + "..."

        lines.append(f"{role}: {content}")

        # Including the SQL from previous turns is what makes "break that down
        # by month" work — the model can extend the actual previous query
        # rather than guessing at the filters from the prose answer.
        previous_sql = turn.get("sql")
        if previous_sql:
            lines.append(f"(SQL used: {previous_sql})")

    return "\n".join(lines) if lines else "(no earlier turns)"


def generate_sql_plan(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> SQLPlan:
    llm = get_llm_service()

    system_prompt = SYSTEM_PROMPT.format(
        schema=render_schema_prompt(),
        today=date.today().isoformat(),
    )

    user_prompt = (
        f"Conversation so far:\n{_format_history(history or [])}\n\n"
        f"New question from the admin:\n{question}"
    )

    data: dict[str, Any] = llm.generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=1200,
    )

    chart_type = (data.get("chart_type") or "none").strip().lower()
    if chart_type not in {"none", "bar", "line", "pie"}:
        chart_type = "none"

    return SQLPlan(
        in_scope=bool(data.get("in_scope", False)),
        sql=(data.get("sql") or "").strip(),
        intent=(data.get("intent") or "").strip(),
        chart_type=chart_type,
        chart_label_column=data.get("chart_label_column") or None,
        chart_value_column=data.get("chart_value_column") or None,
        refusal_reason=data.get("refusal_reason") or None,
        clarification=data.get("clarification") or None,
    )


ANSWER_SYSTEM_PROMPT = """You are a data analyst explaining a query result to a \
business admin who cannot see the SQL.

Write 1-3 short sentences in plain English that directly answer their question.

Rules:
- Lead with the actual answer and the number. Never say "the query returned".
- Format money with thousands separators and the currency when you know it.
- If the result set is empty, say plainly that no matching documents were found, \
  and suggest one likely reason (no documents of that type uploaded yet, or \
  nothing in that date range).
- If the results were truncated, mention that you're showing the top N.
- Add at most one genuinely useful observation (a notable concentration, an \
  outlier, a trend direction). Skip it if nothing stands out — don't pad.
- Never invent numbers that aren't in the result. Never speculate about causes.
- Plain prose. No markdown headers, no bullet lists, no restating the table."""


def generate_answer(
    question: str,
    intent: str,
    columns: list[str],
    rows: list[list[Any]],
    truncated: bool,
) -> str:
    llm = get_llm_service()

    # Only the first rows are needed to characterise the result, and this keeps
    # a 500-row table from blowing up the prompt.
    preview = rows[:30]

    result_block = {
        "columns": columns,
        "rows": preview,
        "total_rows_returned": len(rows),
        "truncated": truncated,
    }

    user_prompt = (
        f"The admin asked: {question}\n\n"
        f"What was computed: {intent}\n\n"
        f"Query result (JSON): {result_block}\n\n"
        "Write the answer."
    )

    return llm.generate(
        system_prompt=ANSWER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=300,
    ).strip()