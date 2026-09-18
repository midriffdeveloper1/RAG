from __future__ import annotations

import base64
import logging

from app.models.business_documents.upload import BusinessDocumentType
from app.services.business_documents.field_schemas import FIELD_SCHEMAS, get_schema
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 20_000
EXTRACTION_MAX_TOKENS = 8000

VALID_TYPES = [t.value for t in BusinessDocumentType if t != BusinessDocumentType.UNKNOWN]

FIELD_NOTES: dict[tuple[BusinessDocumentType, str], str] = {
    (BusinessDocumentType.RESUME, "total_experience_years"): (
        "usually NOT printed directly — compute it from the `experience` entries "
        "below; see DERIVED FIELDS"
    ),
    (BusinessDocumentType.RESUME, "certifications"): (
        "scan the WHOLE resume for these, not just a section titled "
        "'Certifications' — see DERIVED FIELDS"
    ),
    (BusinessDocumentType.RESUME, "skills"): (
        "include skills named in a dedicated section AND ones only mentioned "
        "inside job descriptions"
    ),
    (BusinessDocumentType.EXPENSE_REPORT, "total_amount"): (
        "if not printed as a single figure, compute it as the sum of `expenses[].amount`"
    ),
    (BusinessDocumentType.EXPENSE_REPORT, "expense_period_start"): (
        "if not stated, use the earliest date among `expenses[].date`"
    ),
    (BusinessDocumentType.EXPENSE_REPORT, "expense_period_end"): (
        "if not stated, use the latest date among `expenses[].date`"
    ),
    (BusinessDocumentType.INVOICE, "subtotal"): (
        "if not printed, compute it as the sum of `line_items[].amount`"
    ),
    (BusinessDocumentType.INVOICE, "total_amount"): (
        "if not printed, compute it as subtotal + tax_amount (or just subtotal if there's no tax line)"
    ),
    (BusinessDocumentType.RECEIPT, "subtotal"): (
        "if not printed, compute it as the sum of `items[].amount`"
    ),
    (BusinessDocumentType.RECEIPT, "total_amount"): (
        "if not printed, compute it as subtotal + tax_amount (or just subtotal if there's no tax line)"
    ),
    (BusinessDocumentType.PURCHASE_ORDER, "subtotal"): (
        "if not printed, compute it as the sum of `line_items[].amount`"
    ),
    (BusinessDocumentType.PURCHASE_ORDER, "total_amount"): (
        "if not printed, compute it as subtotal + tax_amount (or just subtotal if there's no tax line)"
    ),
}

LINE_ITEM_AMOUNT_NOTE = "if not printed, compute it as quantity × unit_price"


def _schema_hint() -> str:
    lines = []
    for doc_type, schema in FIELD_SCHEMAS.items():
        field_bits = []
        for name, spec in schema.items():
            if spec["type"] == "object_list":
                item_fields = spec["item_fields"]
                has_unit_price = "quantity" in item_fields and "unit_price" in item_fields
                sub_bits = []
                for sub_name in item_fields:
                    if sub_name == "amount" and has_unit_price:
                        sub_bits.append(f"{sub_name} [{LINE_ITEM_AMOUNT_NOTE}]")
                    else:
                        sub_bits.append(sub_name)
                field_bits.append(f'{name}: [{{{", ".join(sub_bits)}}}]')
            else:
                note = FIELD_NOTES.get((doc_type, name))
                field_bits.append(f"{name} [{note}]" if note else name)
        lines.append(f"- {doc_type.value}: {', '.join(field_bits)}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are a document-intelligence engine. You read a business document and:
1. Classify it as exactly one of: {", ".join(VALID_TYPES)}, or "unknown" if it clearly isn't any of those.
2. Extract every field defined for that document type below.
3. Give a confidence score from 0.0 to 1.0 for the type classification, and a separate 0.0-1.0
   confidence score for EACH extracted field (see CONFIDENCE below for how to score computed fields).

Field definitions per document type (only extract the fields for the type you classified). Some
fields have a note in [brackets] telling you how to handle them when they aren't printed directly —
read those notes, they matter as much as the field list itself:
{_schema_hint()}

=== EXTRACTION: two different skills, don't confuse them ===

TRANSCRIBING is copying a value that's printed in the document. Never transcribe a value that
isn't there — a field with no basis in the text stays null. This is where "don't hallucinate" applies.

COMPUTING is arithmetic or aggregation over values you already transcribed elsewhere in the SAME
document — summing line items into a total, adding up date ranges into years of experience. This is
not hallucination, it's using data that's genuinely in the document, and it is REQUIRED wherever a
field's [bracketed note] above or the DERIVED FIELDS section below says to do it. A field is only
left null when it can neither be transcribed nor computed from anything in the document — not simply
because the final number itself wasn't printed as one figure somewhere.

Getting this distinction backwards is the single biggest quality problem with document extraction:
treating "not printed as a single figure" the same as "not knowable" throws away information the
document actually contains. A resume listing five jobs with dates has years of experience in it even
though no line says "X years." An expense report with ten itemized expenses and no grand total line
still has a grand total — it's the sum of the ten lines.

=== DERIVED FIELDS: how to compute the common ones ===

Resume — total_experience_years: sum the duration of every entry in `experience`. Convert each
entry's start_date/end_date into a span in years (a job from 2021-03 to 2023-09 is ~2.5 years).
Treat "Present" / "Current" / no end_date as running through today. If two entries' date ranges
overlap (e.g. a part-time role held during another job), don't double-count the overlapping months —
sum the union of the time covered, not the sum of each entry's raw length. Round to one decimal
place. If experience entries have no dates at all to work from, leave this null rather than guessing.

Resume — certifications: this is the field most often under-extracted. Don't limit yourself to a
block literally titled "Certifications" or "Licenses" — read the summary, every experience entry's
description, and the education section too. A line like "AWS Certified Solutions Architect, 2022" or
"PMP-certified project manager" inside a job bullet is a certification even with no dedicated heading
for it. Collect every one you find into a single flat, deduplicated list.

Expense report — total_amount: if the document doesn't print one combined total, sum the `amount` of
every entry in `expenses`. Round to 2 decimal places. If it DOES print a total, use the printed value
even if it differs slightly from the sum of the lines (rounding in the source document is normal) —
printed beats computed when both exist.

Expense report — expense_period_start / expense_period_end: if not stated as its own field, use the
earliest and latest dates found among the `expenses` entries.

Invoice / receipt / purchase order — line item `amount`: if a line shows quantity and unit price but
no extended amount, multiply them. If the document already prints an amount for the line, use the
printed value, even if it doesn't exactly match quantity × unit price (discounts and rounding happen
in real documents).

Invoice / receipt / purchase order — subtotal: if not printed, sum the (possibly computed, from the
rule above) `amount` of every line item.

Invoice / receipt / purchase order — total_amount: if not printed, use subtotal + tax_amount (or just
subtotal if there's no tax/tax is zero or absent).

Before finalizing your answer, sanity-check the arithmetic you did: does total_amount actually equal
subtotal + tax_amount? Does total_experience_years roughly match what the listed jobs' dates imply?
If your own numbers don't add up, recompute rather than submitting an inconsistent result.

=== CONFIDENCE ===

For a TRANSCRIBED field: 1.0 = printed clearly and unambiguous, 0.5 = present but partly
illegible/ambiguous, lower still = mostly guessed from weak context. A field you couldn't find at
all, and couldn't compute either, should be null with confidence 0.0.

For a COMPUTED field, base its confidence on how solid its inputs were, not on whether the final
number itself was printed: if every line item had a clear amount, a computed subtotal can be just as
high-confidence as a printed one (0.85-0.95). If some of the inputs were themselves uncertain or
partially illegible, lower the computed field's confidence to match — it can't be more certain than
the numbers it's built from.

=== OUTPUT FORMAT ===

Respond with ONLY a single valid JSON object, no markdown fences, no commentary, in exactly this
shape:
{{
  "document_type": "<one of: {", ".join(VALID_TYPES)}, unknown>",
  "type_confidence": <0.0-1.0>,
  "fields": {{ ...the fields for the detected type, using the exact field names given above... }},
  "field_confidence": {{ "<field_name>": <0.0-1.0>, ... }}
}}

Rules:
- Dates should be normalized to "YYYY-MM-DD" when you can determine the actual date; otherwise keep
  the text as printed.
- Numbers (amounts, quantities, prices, computed totals, computed years of experience) should be
  plain numbers, not strings, and without currency symbols or thousands separators.
- For "object_list" fields (line_items, expenses, education, experience, signatories, etc.), return
  a JSON array of objects using the sub-field names given.
- If the document doesn't match any of the listed types, set document_type to "unknown", leave
  "fields" as an empty object, and set field_confidence to an empty object.
- Output raw JSON only.
"""


class ExtractionResult:
    def __init__(
        self,
        document_type: BusinessDocumentType,
        type_confidence: float,
        fields: dict,
        field_confidence: dict,
    ) -> None:
        self.document_type = document_type
        self.type_confidence = type_confidence
        self.fields = fields
        self.field_confidence = field_confidence


def _coerce_result(data: dict) -> ExtractionResult:
    raw_type = str(data.get("document_type") or "unknown").strip().lower()
    try:
        document_type = BusinessDocumentType(raw_type)
    except ValueError:
        document_type = BusinessDocumentType.UNKNOWN

    type_confidence = data.get("type_confidence")
    try:
        type_confidence = max(0.0, min(1.0, float(type_confidence)))
    except (TypeError, ValueError):
        type_confidence = 0.0

    fields = data.get("fields")
    fields = fields if isinstance(fields, dict) else {}

    
    schema = get_schema(document_type)
    if schema:
        fields = {k: v for k, v in fields.items() if k in schema}

    raw_confidence = data.get("field_confidence")
    field_confidence: dict[str, float] = {}
    if isinstance(raw_confidence, dict):
        for key, value in raw_confidence.items():
            try:
                field_confidence[key] = max(0.0, min(1.0, float(value)))
            except (TypeError, ValueError):
                continue

    return ExtractionResult(document_type, type_confidence, fields, field_confidence)


def extract_from_text(text: str, expected_type: BusinessDocumentType | None = None) -> ExtractionResult:
    llm = get_llm_service()
    truncated = text[:MAX_TEXT_CHARS]

    hint = ""
    if expected_type is not None:
        hint = (
            f"\n\nThe uploader expects this to be a '{expected_type.value}' — verify that against "
            "the actual content rather than assuming it's correct."
        )

    data = llm.generate_json(
        SYSTEM_PROMPT,
        f"Document text:\n\n{truncated}{hint}",
        max_tokens=EXTRACTION_MAX_TOKENS,
        temperature=0.0,
    )
    return _coerce_result(data)


def extract_from_image(
    image_bytes: bytes, mime_type: str, expected_type: BusinessDocumentType | None = None
) -> ExtractionResult:
    llm = get_llm_service()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    hint = ""
    if expected_type is not None:
        hint = (
            f"\n\nThe uploader expects this to be a '{expected_type.value}' — verify that against "
            "the actual content rather than assuming it's correct."
        )

    data = llm.generate_json_with_image(
        SYSTEM_PROMPT,
        f"Read this document image and extract its fields.{hint}",
        image_base64=image_b64,
        image_mime_type=mime_type,
        max_tokens=EXTRACTION_MAX_TOKENS,
        temperature=0.0,
    )
    return _coerce_result(data)