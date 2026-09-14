from __future__ import annotations

import base64
import logging

from app.models.business_document import BusinessDocumentType
from app.services.business_documents.field_schemas import FIELD_SCHEMAS, get_schema
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 20_000
EXTRACTION_MAX_TOKENS = 3000

VALID_TYPES = [t.value for t in BusinessDocumentType if t != BusinessDocumentType.UNKNOWN]


def _schema_hint() -> str:
    lines = []
    for doc_type, schema in FIELD_SCHEMAS.items():
        field_bits = []
        for name, spec in schema.items():
            if spec["type"] == "object_list":
                sub = ", ".join(spec["item_fields"].keys())
                field_bits.append(f'{name}: [{{{sub}}}]')
            else:
                field_bits.append(name)
        lines.append(f"- {doc_type.value}: {', '.join(field_bits)}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are a document-intelligence engine. You read a business document and:
1. Classify it as exactly one of: {", ".join(VALID_TYPES)}, or "unknown" if it clearly isn't any of those.
2. Extract every field defined for that document type below, using ONLY information actually
   present in the document. Never invent, guess, or hallucinate values.
3. Give a confidence score from 0.0 to 1.0 for the type classification, and a separate 0.0-1.0
   confidence score for EACH extracted field (1.0 = printed clearly and unambiguous, 0.5 = present
   but partly illegible/ambiguous, lower = mostly guessed from weak context). Fields you couldn't
   find at all should be null and get confidence 0.0.

Field definitions per document type (only extract the fields for the type you classified):
{_schema_hint()}

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
- Numbers (amounts, quantities, prices) should be plain numbers, not strings, and without currency
  symbols or thousands separators.
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

    # Drop keys the schema for this type doesn't know about, so we never
    # persist arbitrary LLM-invented fields into the structured record.
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