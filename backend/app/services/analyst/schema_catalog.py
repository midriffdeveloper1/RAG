from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str
    note: str = ""


@dataclass(frozen=True)
class TableInfo:
    name: str
    description: str
    columns: list[ColumnInfo]
    joins: list[str] = field(default_factory=list)


_LINE_ITEM_COLUMNS = [
    ColumnInfo("id", "text"),
    ColumnInfo("position", "integer", "ordering within the parent document"),
    ColumnInfo("description", "text", "the product/service name — use this for 'which product' questions"),
    ColumnInfo("quantity", "numeric"),
    ColumnInfo("unit_price", "numeric"),
    ColumnInfo("amount", "numeric", "line total; prefer this over quantity * unit_price"),
]


SCHEMA: dict[str, TableInfo] = {
    "business_document_uploads": TableInfo(
        name="business_document_uploads",
        description=(
            "One row per uploaded document file. Every document table below hangs off "
            "this via upload_id. This is the ONLY table with a reliable real timestamp "
            "(uploaded_at), so it is the safest basis for time-range questions."
        ),
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("original_filename", "text"),
            ColumnInfo("file_type", "text", "pdf, jpg, png, docx, doc"),
            ColumnInfo("file_size_bytes", "bigint"),
            ColumnInfo(
                "document_type",
                "enum text",
                "one of: invoice, receipt, purchase_order, resume, expense_report, "
                "application_form, contract, unknown",
            ),
            ColumnInfo("type_confidence", "numeric", "0..1 confidence in the classification"),
            ColumnInfo(
                "status",
                "enum text",
                "one of: pending, processing, completed, needs_review, failed",
            ),
            ColumnInfo("confidence_score", "numeric", "0..1 overall extraction confidence"),
            ColumnInfo("is_valid", "boolean"),
            ColumnInfo("reviewed", "boolean"),
            ColumnInfo("uploaded_at", "timestamp", "REAL timestamp — use for date filtering"),
            ColumnInfo("processed_at", "timestamp"),
        ],
    ),
    
    "invoices": TableInfo(
        name="invoices",
        description="Extracted invoice header data. One row per invoice document.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("invoice_number", "text"),
            ColumnInfo("invoice_date", "TEXT 'YYYY-MM-DD'", "TEXT, not a date — see date rules"),
            ColumnInfo("due_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("vendor_name", "text", "who issued the invoice"),
            ColumnInfo("vendor_address", "text"),
            ColumnInfo("customer_name", "text", "who received it"),
            ColumnInfo("customer_address", "text"),
            ColumnInfo("subtotal", "numeric"),
            ColumnInfo("tax_amount", "numeric"),
            ColumnInfo("total_amount", "numeric", "use for revenue/spend totals"),
            ColumnInfo("currency", "text"),
            ColumnInfo("payment_terms", "text"),
        ],
        joins=["invoices.upload_id = business_document_uploads.id"],
    ),
    "invoice_line_items": TableInfo(
        name="invoice_line_items",
        description="Individual line items on an invoice. Use for per-product analysis.",
        columns=[ColumnInfo("invoice_id", "text", "FK -> invoices.id")] + _LINE_ITEM_COLUMNS,
        joins=["invoice_line_items.invoice_id = invoices.id"],
    ),

    "receipts": TableInfo(
        name="receipts",
        description="Extracted receipt data. One row per receipt document.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("receipt_number", "text"),
            ColumnInfo("merchant_name", "text"),
            ColumnInfo("merchant_address", "text"),
            ColumnInfo("transaction_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("transaction_time", "text"),
            ColumnInfo("subtotal", "numeric"),
            ColumnInfo("tax_amount", "numeric"),
            ColumnInfo("total_amount", "numeric"),
            ColumnInfo("payment_method", "text"),
            ColumnInfo("currency", "text"),
        ],
        joins=["receipts.upload_id = business_document_uploads.id"],
    ),
    "receipt_items": TableInfo(
        name="receipt_items",
        description="Individual items on a receipt.",
        columns=[ColumnInfo("receipt_id", "text", "FK -> receipts.id")] + _LINE_ITEM_COLUMNS,
        joins=["receipt_items.receipt_id = receipts.id"],
    ),

    "purchase_orders": TableInfo(
        name="purchase_orders",
        description="Extracted purchase order header data.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("po_number", "text"),
            ColumnInfo("po_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("vendor_name", "text"),
            ColumnInfo("buyer_name", "text"),
            ColumnInfo("delivery_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("delivery_address", "text"),
            ColumnInfo("subtotal", "numeric"),
            ColumnInfo("tax_amount", "numeric"),
            ColumnInfo("total_amount", "numeric"),
            ColumnInfo("currency", "text"),
            ColumnInfo("payment_terms", "text"),
        ],
        joins=["purchase_orders.upload_id = business_document_uploads.id"],
    ),
    "purchase_order_line_items": TableInfo(
        name="purchase_order_line_items",
        description="Individual line items on a purchase order.",
        columns=[ColumnInfo("purchase_order_id", "text", "FK -> purchase_orders.id")]
        + _LINE_ITEM_COLUMNS,
        joins=["purchase_order_line_items.purchase_order_id = purchase_orders.id"],
    ),

    "resumes": TableInfo(
        name="resumes",
        description="Extracted candidate resume data.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("candidate_name", "text"),
            ColumnInfo("email", "text"),
            ColumnInfo("phone", "text"),
            ColumnInfo("address", "text"),
            ColumnInfo("summary", "text"),
            ColumnInfo("total_experience_years", "numeric"),
            ColumnInfo(
                "skills",
                "json array of text",
                "query with: EXISTS (SELECT 1 FROM jsonb_array_elements_text(resumes.skills::jsonb) s "
                "WHERE s ILIKE '%python%')",
            ),
            ColumnInfo("certifications", "json array of text", "same jsonb pattern as skills"),
        ],
        joins=["resumes.upload_id = business_document_uploads.id"],
    ),
    "resume_education": TableInfo(
        name="resume_education",
        description="Education entries for a resume.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("resume_id", "text", "FK -> resumes.id"),
            ColumnInfo("position", "integer"),
            ColumnInfo("institution", "text"),
            ColumnInfo("degree", "text"),
            ColumnInfo("field", "text"),
            ColumnInfo("start_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("end_date", "TEXT 'YYYY-MM-DD'"),
        ],
        joins=["resume_education.resume_id = resumes.id"],
    ),
    "resume_experience": TableInfo(
        name="resume_experience",
        description="Work-experience entries for a resume.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("resume_id", "text", "FK -> resumes.id"),
            ColumnInfo("position", "integer"),
            ColumnInfo("company", "text"),
            ColumnInfo("title", "text", "job title"),
            ColumnInfo("start_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("end_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("description", "text"),
        ],
        joins=["resume_experience.resume_id = resumes.id"],
    ),

    "expense_reports": TableInfo(
        name="expense_reports",
        description="Extracted expense report header data.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("employee_name", "text"),
            ColumnInfo("employee_id", "text"),
            ColumnInfo("department", "text"),
            ColumnInfo("report_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("expense_period_start", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("expense_period_end", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("total_amount", "numeric"),
            ColumnInfo("currency", "text"),
            ColumnInfo("approver_name", "text"),
        ],
        joins=["expense_reports.upload_id = business_document_uploads.id"],
    ),
    "expense_report_items": TableInfo(
        name="expense_report_items",
        description="Individual expense lines on an expense report.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("expense_report_id", "text", "FK -> expense_reports.id"),
            ColumnInfo("position", "integer"),
            ColumnInfo("date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("category", "text", "e.g. travel, meals, lodging"),
            ColumnInfo("description", "text"),
            ColumnInfo("amount", "numeric"),
        ],
        joins=["expense_report_items.expense_report_id = expense_reports.id"],
    ),

    "application_forms": TableInfo(
        name="application_forms",
        description="Extracted application form data.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("applicant_name", "text"),
            ColumnInfo("email", "text"),
            ColumnInfo("phone", "text"),
            ColumnInfo("address", "text"),
            ColumnInfo("date_of_birth", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("position_applied_for", "text"),
            ColumnInfo("submission_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("additional_fields", "json object", "free-form extra fields; avoid unless asked"),
        ],
        joins=["application_forms.upload_id = business_document_uploads.id"],
    ),

    "contracts": TableInfo(
        name="contracts",
        description="Extracted contract data.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("upload_id", "text", "FK -> business_document_uploads.id"),
            ColumnInfo("contract_title", "text"),
            ColumnInfo("contract_type", "text", "e.g. NDA, MSA, employment"),
            ColumnInfo("party_a", "text"),
            ColumnInfo("party_b", "text"),
            ColumnInfo("effective_date", "TEXT 'YYYY-MM-DD'"),
            ColumnInfo("expiration_date", "TEXT 'YYYY-MM-DD'", "use for 'expiring soon' questions"),
            ColumnInfo("contract_value", "numeric"),
            ColumnInfo("currency", "text"),
            ColumnInfo("key_terms", "json array of text", "same jsonb pattern as resumes.skills"),
            ColumnInfo("governing_law", "text"),
        ],
        joins=["contracts.upload_id = business_document_uploads.id"],
    ),
    "contract_signatories": TableInfo(
        name="contract_signatories",
        description="People who signed a contract.",
        columns=[
            ColumnInfo("id", "text"),
            ColumnInfo("contract_id", "text", "FK -> contracts.id"),
            ColumnInfo("position", "integer"),
            ColumnInfo("name", "text"),
            ColumnInfo("role", "text"),
        ],
        joins=["contract_signatories.contract_id = contracts.id"],
    ),
}


ALLOWED_TABLES: frozenset[str] = frozenset(SCHEMA.keys())

ALLOWED_COLUMNS: frozenset[str] = frozenset(
    column.name for table in SCHEMA.values() for column in table.columns
)


def render_schema_prompt() -> str:
    lines: list[str] = []

    for table in SCHEMA.values():
        lines.append(f"TABLE {table.name}")
        lines.append(f"  -- {table.description}")

        for column in table.columns:
            suffix = f"  -- {column.note}" if column.note else ""
            lines.append(f"  {column.name} : {column.type}{suffix}")

        if table.joins:
            lines.append(f"  JOIN: {'; '.join(table.joins)}")

        lines.append("")

    return "\n".join(lines).strip()
