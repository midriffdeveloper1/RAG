from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.business_documents.application_form import ApplicationForm
from app.models.business_documents.contract import Contract, ContractSignatory
from app.models.business_documents.expense_report import ExpenseReport, ExpenseReportItem
from app.models.business_documents.invoice import Invoice, InvoiceLineItem
from app.models.business_documents.purchase_order import PurchaseOrder, PurchaseOrderLineItem
from app.models.business_documents.receipt import Receipt, ReceiptItem
from app.models.business_documents.resume import Resume, ResumeEducation, ResumeExperience
from app.models.business_documents.upload import BusinessDocumentType, BusinessDocumentUpload
from app.services.business_documents.field_schemas import get_schema

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y")


def _normalize_date(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # keep whatever text we got so nothing silently disappears


def _to_float(value) -> float | None:
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


def _coerce_scalar(field_type: str, value):
    if value in (None, ""):
        return None
    if field_type in ("string", "email", "phone"):
        return str(value)
    if field_type == "number":
        return _to_float(value)
    if field_type == "date":
        return _normalize_date(value)
    if field_type in ("list", "object"):
        return value
    return value


@dataclass
class ListFieldConfig:
    child_model: type
    fk_field: str
    relationship_name: str


@dataclass
class TypeConfig:
    model: type
    relationship_name: str  # attribute name on BusinessDocumentUpload
    list_fields: dict[str, ListFieldConfig]


REGISTRY: dict[BusinessDocumentType, TypeConfig] = {
    BusinessDocumentType.INVOICE: TypeConfig(
        model=Invoice,
        relationship_name="invoice",
        list_fields={
            "line_items": ListFieldConfig(InvoiceLineItem, "invoice_id", "line_items"),
        },
    ),
    BusinessDocumentType.RECEIPT: TypeConfig(
        model=Receipt,
        relationship_name="receipt",
        list_fields={
            "items": ListFieldConfig(ReceiptItem, "receipt_id", "items"),
        },
    ),
    BusinessDocumentType.PURCHASE_ORDER: TypeConfig(
        model=PurchaseOrder,
        relationship_name="purchase_order",
        list_fields={
            "line_items": ListFieldConfig(PurchaseOrderLineItem, "purchase_order_id", "line_items"),
        },
    ),
    BusinessDocumentType.RESUME: TypeConfig(
        model=Resume,
        relationship_name="resume",
        list_fields={
            "education": ListFieldConfig(ResumeEducation, "resume_id", "education"),
            "experience": ListFieldConfig(ResumeExperience, "resume_id", "experience"),
        },
    ),
    BusinessDocumentType.EXPENSE_REPORT: TypeConfig(
        model=ExpenseReport,
        relationship_name="expense_report",
        list_fields={
            "expenses": ListFieldConfig(ExpenseReportItem, "expense_report_id", "expenses"),
        },
    ),
    BusinessDocumentType.APPLICATION_FORM: TypeConfig(
        model=ApplicationForm,
        relationship_name="application_form",
        list_fields={},
    ),
    BusinessDocumentType.CONTRACT: TypeConfig(
        model=Contract,
        relationship_name="contract",
        list_fields={
            "signatories": ListFieldConfig(ContractSignatory, "contract_id", "signatories"),
        },
    ),
}


def get_or_create_parent(db: Session, upload: BusinessDocumentUpload, document_type: BusinessDocumentType):
    config = REGISTRY.get(document_type)
    if config is None:
        return None
    existing = getattr(upload, config.relationship_name)
    if existing is not None:
        return existing
    parent = config.model(upload_id=upload.id)
    setattr(upload, config.relationship_name, parent)
    db.add(parent)
    db.flush()
    return parent


def get_parent(upload: BusinessDocumentUpload, document_type: BusinessDocumentType):
    config = REGISTRY.get(document_type)
    if config is None:
        return None
    return getattr(upload, config.relationship_name)


def apply_fields(
    db: Session, upload: BusinessDocumentUpload, document_type: BusinessDocumentType, fields: dict
) -> None:
    """Writes `fields` (any subset of the type's schema) onto the relational
    tables. Scalar keys update columns; object_list keys fully replace that
    field's child rows (so this doubles as both the initial-extraction
    write and a partial admin correction)."""

    config = REGISTRY.get(document_type)
    schema = get_schema(document_type)
    if config is None or not schema:
        return

    parent = get_or_create_parent(db, upload, document_type)

    for name, value in fields.items():
        spec = schema.get(name)
        if spec is None:
            continue  # not part of this type's schema — ignore silently

        if spec["type"] == "object_list":
            list_config = config.list_fields.get(name)
            if list_config is None:
                continue
            item_schema = spec.get("item_fields", {})
            items = value if isinstance(value, list) else []
            new_rows = []
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                kwargs = {"position": idx}
                for sub_name, sub_spec in item_schema.items():
                    kwargs[sub_name] = _coerce_scalar(sub_spec["type"], item.get(sub_name))
                new_rows.append(list_config.child_model(**kwargs))
            setattr(parent, list_config.relationship_name, new_rows)
        else:
            setattr(parent, name, _coerce_scalar(spec["type"], value))

    db.flush()


def serialize_fields(upload: BusinessDocumentUpload) -> dict:
    """Reassembles the flat `extracted_data` dict shape the frontend expects,
    by reading the relational tables back through the schema."""

    document_type = upload.document_type
    schema = get_schema(document_type)
    parent = get_parent(upload, document_type)
    if parent is None or not schema:
        return {}

    config = REGISTRY[document_type]
    result: dict = {}

    for name, spec in schema.items():
        if spec["type"] == "object_list":
            list_config = config.list_fields.get(name)
            if list_config is None:
                result[name] = []
                continue
            item_schema = spec.get("item_fields", {})
            children = getattr(parent, list_config.relationship_name) or []
            result[name] = [
                {sub_name: getattr(child, sub_name, None) for sub_name in item_schema}
                for child in children
            ]
        else:
            result[name] = getattr(parent, name, None)

    return result