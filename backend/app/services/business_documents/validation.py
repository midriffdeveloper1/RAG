from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.models.business_document import BusinessDocumentType
from app.services.business_documents.field_schemas import get_schema

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[\d\s()+.\-]{7,20}$")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y")


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _parse_date(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _validate_scalar(field_type: str, value: Any) -> bool:
    if field_type == "string":
        return isinstance(value, str)
    if field_type == "number":
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value.replace(",", ""))
                return True
            except ValueError:
                return False
        return False
    if field_type == "date":
        return _parse_date(value)
    if field_type == "email":
        return isinstance(value, str) and bool(EMAIL_RE.match(value.strip()))
    if field_type == "phone":
        return isinstance(value, str) and bool(PHONE_RE.match(value.strip()))
    if field_type == "list":
        return isinstance(value, list)
    if field_type == "object":
        return isinstance(value, dict)
    return True


def validate_fields(
    document_type: BusinessDocumentType, fields: dict[str, Any]
) -> tuple[bool, list[dict[str, str]], list[str]]:
    """Returns (is_valid, errors, missing_fields)."""

    schema = get_schema(document_type)
    errors: list[dict[str, str]] = []
    missing: list[str] = []

    for name, spec in schema.items():
        value = fields.get(name)
        field_type = spec["type"]

        if _is_empty(value):
            if spec.get("required"):
                missing.append(name)
            continue

        if field_type == "object_list":
            if not isinstance(value, list):
                errors.append({"field": name, "message": f"{spec['label']} should be a list."})
                continue
            item_schema = spec.get("item_fields", {})
            for idx, item in enumerate(value):
                if not isinstance(item, dict):
                    errors.append(
                        {"field": f"{name}[{idx}]", "message": "Expected an object with fields."}
                    )
                    continue
                for item_field, item_spec in item_schema.items():
                    item_value = item.get(item_field)
                    if _is_empty(item_value):
                        if item_spec.get("required"):
                            errors.append(
                                {
                                    "field": f"{name}[{idx}].{item_field}",
                                    "message": f"{item_spec['label']} is required for each item.",
                                }
                            )
                        continue
                    if not _validate_scalar(item_spec["type"], item_value):
                        errors.append(
                            {
                                "field": f"{name}[{idx}].{item_field}",
                                "message": f"{item_spec['label']} has an invalid format.",
                            }
                        )
            continue

        if not _validate_scalar(field_type, value):
            errors.append({"field": name, "message": f"{spec['label']} has an invalid format."})

    _validate_totals_consistency(fields, errors)

    is_valid = not errors and not missing
    return is_valid, errors, missing


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _validate_totals_consistency(fields: dict[str, Any], errors: list[dict[str, str]]) -> None:
    """Soft cross-field check: subtotal + tax ~= total, when all three are present."""

    subtotal = _to_number(fields.get("subtotal"))
    tax = _to_number(fields.get("tax_amount"))
    total = _to_number(fields.get("total_amount"))

    if subtotal is None or tax is None or total is None:
        return

    expected = round(subtotal + tax, 2)
    if abs(expected - round(total, 2)) > max(0.02, round(total, 2) * 0.01):
        errors.append(
            {
                "field": "total_amount",
                "message": (
                    f"Total ({total}) doesn't match subtotal + tax ({expected}). "
                    "Double-check the extracted amounts."
                ),
            }
        )