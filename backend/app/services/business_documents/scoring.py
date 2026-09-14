from __future__ import annotations

from app.models.business_document import BusinessDocumentType
from app.services.business_documents.field_schemas import get_schema

REQUIRED_WEIGHT = 2.0
OPTIONAL_WEIGHT = 1.0


def compute_confidence(
    document_type: BusinessDocumentType,
    fields: dict,
    field_confidence: dict[str, float],
    missing_fields: list[str],
) -> float:
    schema = get_schema(document_type)
    if not schema:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for name, spec in schema.items():
        weight = REQUIRED_WEIGHT if spec.get("required") else OPTIONAL_WEIGHT
        total_weight += weight

        if name in missing_fields:
            weighted_sum += 0.0
            continue

        has_value = fields.get(name) not in (None, "", [], {})
        if not has_value:
            weighted_sum += 0.0
            continue

        weighted_sum += weight * field_confidence.get(name, 0.5)

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 3)