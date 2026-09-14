from __future__ import annotations

from app.models.business_document import BusinessDocumentType

LINE_ITEM_FIELDS = {
    "description": {"type": "string", "required": True, "label": "Description"},
    "quantity": {"type": "number", "required": False, "label": "Quantity"},
    "unit_price": {"type": "number", "required": False, "label": "Unit price"},
    "amount": {"type": "number", "required": False, "label": "Amount"},
}

FIELD_SCHEMAS: dict[BusinessDocumentType, dict] = {
    BusinessDocumentType.INVOICE: {
        "invoice_number": {"type": "string", "required": True, "label": "Invoice number"},
        "invoice_date": {"type": "date", "required": True, "label": "Invoice date"},
        "due_date": {"type": "date", "required": False, "label": "Due date"},
        "vendor_name": {"type": "string", "required": True, "label": "Vendor name"},
        "vendor_address": {"type": "string", "required": False, "label": "Vendor address"},
        "customer_name": {"type": "string", "required": True, "label": "Bill to"},
        "customer_address": {"type": "string", "required": False, "label": "Customer address"},
        "line_items": {
            "type": "object_list", "required": True, "label": "Line items",
            "item_fields": LINE_ITEM_FIELDS,
        },
        "subtotal": {"type": "number", "required": False, "label": "Subtotal"},
        "tax_amount": {"type": "number", "required": False, "label": "Tax"},
        "total_amount": {"type": "number", "required": True, "label": "Total amount"},
        "currency": {"type": "string", "required": False, "label": "Currency"},
        "payment_terms": {"type": "string", "required": False, "label": "Payment terms"},
    },
    BusinessDocumentType.RECEIPT: {
        "receipt_number": {"type": "string", "required": False, "label": "Receipt number"},
        "merchant_name": {"type": "string", "required": True, "label": "Merchant"},
        "merchant_address": {"type": "string", "required": False, "label": "Merchant address"},
        "transaction_date": {"type": "date", "required": True, "label": "Date"},
        "transaction_time": {"type": "string", "required": False, "label": "Time"},
        "items": {
            "type": "object_list", "required": False, "label": "Items",
            "item_fields": LINE_ITEM_FIELDS,
        },
        "subtotal": {"type": "number", "required": False, "label": "Subtotal"},
        "tax_amount": {"type": "number", "required": False, "label": "Tax"},
        "total_amount": {"type": "number", "required": True, "label": "Total"},
        "payment_method": {"type": "string", "required": False, "label": "Payment method"},
        "currency": {"type": "string", "required": False, "label": "Currency"},
    },
    BusinessDocumentType.PURCHASE_ORDER: {
        "po_number": {"type": "string", "required": True, "label": "PO number"},
        "po_date": {"type": "date", "required": True, "label": "PO date"},
        "vendor_name": {"type": "string", "required": True, "label": "Vendor"},
        "buyer_name": {"type": "string", "required": False, "label": "Buyer"},
        "delivery_date": {"type": "date", "required": False, "label": "Delivery date"},
        "delivery_address": {"type": "string", "required": False, "label": "Delivery address"},
        "line_items": {
            "type": "object_list", "required": True, "label": "Line items",
            "item_fields": LINE_ITEM_FIELDS,
        },
        "subtotal": {"type": "number", "required": False, "label": "Subtotal"},
        "tax_amount": {"type": "number", "required": False, "label": "Tax"},
        "total_amount": {"type": "number", "required": True, "label": "Total amount"},
        "currency": {"type": "string", "required": False, "label": "Currency"},
        "payment_terms": {"type": "string", "required": False, "label": "Payment terms"},
    },
    BusinessDocumentType.RESUME: {
        "candidate_name": {"type": "string", "required": True, "label": "Candidate name"},
        "email": {"type": "email", "required": True, "label": "Email"},
        "phone": {"type": "phone", "required": False, "label": "Phone"},
        "address": {"type": "string", "required": False, "label": "Address"},
        "summary": {"type": "string", "required": False, "label": "Summary"},
        "skills": {"type": "list", "required": False, "label": "Skills"},
        "total_experience_years": {"type": "number", "required": False, "label": "Years of experience"},
        "education": {
            "type": "object_list", "required": False, "label": "Education",
            "item_fields": {
                "institution": {"type": "string", "required": True, "label": "Institution"},
                "degree": {"type": "string", "required": False, "label": "Degree"},
                "field": {"type": "string", "required": False, "label": "Field of study"},
                "start_date": {"type": "date", "required": False, "label": "Start"},
                "end_date": {"type": "date", "required": False, "label": "End"},
            },
        },
        "experience": {
            "type": "object_list", "required": True, "label": "Work experience",
            "item_fields": {
                "company": {"type": "string", "required": True, "label": "Company"},
                "title": {"type": "string", "required": True, "label": "Title"},
                "start_date": {"type": "date", "required": False, "label": "Start"},
                "end_date": {"type": "date", "required": False, "label": "End"},
                "description": {"type": "string", "required": False, "label": "Description"},
            },
        },
        "certifications": {"type": "list", "required": False, "label": "Certifications"},
    },
    BusinessDocumentType.EXPENSE_REPORT: {
        "employee_name": {"type": "string", "required": True, "label": "Employee name"},
        "employee_id": {"type": "string", "required": False, "label": "Employee ID"},
        "department": {"type": "string", "required": False, "label": "Department"},
        "report_date": {"type": "date", "required": True, "label": "Report date"},
        "expense_period_start": {"type": "date", "required": False, "label": "Period start"},
        "expense_period_end": {"type": "date", "required": False, "label": "Period end"},
        "expenses": {
            "type": "object_list", "required": True, "label": "Expenses",
            "item_fields": {
                "date": {"type": "date", "required": False, "label": "Date"},
                "category": {"type": "string", "required": False, "label": "Category"},
                "description": {"type": "string", "required": True, "label": "Description"},
                "amount": {"type": "number", "required": True, "label": "Amount"},
            },
        },
        "total_amount": {"type": "number", "required": True, "label": "Total amount"},
        "currency": {"type": "string", "required": False, "label": "Currency"},
        "approver_name": {"type": "string", "required": False, "label": "Approver"},
    },
    BusinessDocumentType.APPLICATION_FORM: {
        "applicant_name": {"type": "string", "required": True, "label": "Applicant name"},
        "email": {"type": "email", "required": False, "label": "Email"},
        "phone": {"type": "phone", "required": False, "label": "Phone"},
        "address": {"type": "string", "required": False, "label": "Address"},
        "date_of_birth": {"type": "date", "required": False, "label": "Date of birth"},
        "position_applied_for": {"type": "string", "required": False, "label": "Position applied for"},
        "submission_date": {"type": "date", "required": False, "label": "Submission date"},
        "additional_fields": {"type": "object", "required": False, "label": "Other form fields"},
    },
    BusinessDocumentType.CONTRACT: {
        "contract_title": {"type": "string", "required": True, "label": "Title"},
        "contract_type": {"type": "string", "required": False, "label": "Contract type"},
        "party_a": {"type": "string", "required": True, "label": "Party A"},
        "party_b": {"type": "string", "required": True, "label": "Party B"},
        "effective_date": {"type": "date", "required": True, "label": "Effective date"},
        "expiration_date": {"type": "date", "required": False, "label": "Expiration date"},
        "contract_value": {"type": "number", "required": False, "label": "Contract value"},
        "currency": {"type": "string", "required": False, "label": "Currency"},
        "key_terms": {"type": "list", "required": False, "label": "Key terms"},
        "signatories": {
            "type": "object_list", "required": False, "label": "Signatories",
            "item_fields": {
                "name": {"type": "string", "required": True, "label": "Name"},
                "role": {"type": "string", "required": False, "label": "Role"},
            },
        },
        "governing_law": {"type": "string", "required": False, "label": "Governing law"},
    },
}

DOCUMENT_TYPE_LABELS: dict[BusinessDocumentType, str] = {
    BusinessDocumentType.INVOICE: "Invoice",
    BusinessDocumentType.RECEIPT: "Receipt",
    BusinessDocumentType.PURCHASE_ORDER: "Purchase order",
    BusinessDocumentType.RESUME: "Resume",
    BusinessDocumentType.EXPENSE_REPORT: "Expense report",
    BusinessDocumentType.APPLICATION_FORM: "Application form",
    BusinessDocumentType.CONTRACT: "Contract",
    BusinessDocumentType.UNKNOWN: "Unknown",
}


def get_schema(document_type: BusinessDocumentType) -> dict:
    return FIELD_SCHEMAS.get(document_type, {})


def required_fields(document_type: BusinessDocumentType) -> list[str]:
    return [name for name, spec in get_schema(document_type).items() if spec.get("required")]