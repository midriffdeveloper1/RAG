import json
import logging

from sqlalchemy.orm import Session

from app.models.knowledge_base import Business, OpeningHour, Service
from app.models.staff import Staff
from app.schemas.document_extraction import (
    DocumentExtractionResult,
    ExtractionSummary,
)
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

MAX_EXTRACTION_CHARS = 60_000
EXTRACTION_MAX_TOKENS = 5000

EXTRACTION_SYSTEM_PROMPT = """You extract structured business facts from a document so they can be \
saved into a database. Read the document text and return ONLY a single valid JSON object — no \
markdown fences, no commentary, no trailing text — matching exactly this shape:

{
  "business": {
    "name": string or null,
    "description": string or null,
    "address": string or null,
    "phone": string or null,
    "email": string or null
  },
  "opening_hours": [
    {"day_of_week": "Monday", "open_time": "10:00", "close_time": "19:00", "is_closed": false}
  ],
  "services": [
    {"name": string, "description": string or null, "price": number or null, "duration_minutes": integer or null}
  ],
  "staff": [
    {"name": string, "email": string or null, "phone": string or null, "service_names": [string, ...]}
  ]
}

Rules:
- Use information ONLY from the document text. Never invent, guess, or fill in plausible-sounding
  values.
- If a field genuinely isn't mentioned anywhere in the document, use null (or an empty list for
  opening_hours/services/staff/service_names) — do not omit the key.
- day_of_week must be a full weekday name (Monday..Sunday). Only include days actually mentioned.
  Times should be 24-hour "HH:MM" strings when a specific time is stated.
- Only list a "service" if it's something customers can book/purchase (with or without a stated
  price/duration) — not general amenities.
- Only list "staff" if named individuals are mentioned as people who provide the services (not
  generic phrases like "our team").
- Output raw JSON only. Do not wrap it in ```json fences or any other text.
"""


class DocumentExtractionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- LLM call + parsing -------------------------------------------------

    def _call_llm(self, document_text: str) -> DocumentExtractionResult | None:
        try:
            llm = get_llm_service()
        except RuntimeError:
            logger.warning("Skipping document extraction — LLM service isn't configured.")
            return None

        truncated = document_text[:MAX_EXTRACTION_CHARS]
        try:
            raw = llm.generate(
                EXTRACTION_SYSTEM_PROMPT,
                f"Document text:\n\n{truncated}",
                max_tokens=EXTRACTION_MAX_TOKENS,
                temperature=0.0,
            )
        except Exception:
            logger.exception("LLM call failed during document field extraction")
            return None

        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> DocumentExtractionResult | None:
        if not raw:
            return None
        text = raw.strip()
        # Defensive: strip a ```json ... ``` fence if the model added one anyway.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            data = json.loads(text)
            return DocumentExtractionResult.model_validate(data)
        except Exception:
            logger.warning("Couldn't parse document extraction output as valid JSON")
            return None

    # --- Applying to the database -------------------------------------------

    def _apply_business(self, extracted, summary: ExtractionSummary) -> Business:
        business = self.db.query(Business).first()
        if business is None:
            business = Business(name=extracted.name or "My Business")
            self.db.add(business)
            self.db.flush()

        for field in ("name", "description", "address", "phone", "email"):
            value = getattr(extracted, field)
            if value:  # the uploaded document takes priority whenever it has a value
                setattr(business, field, value)
                summary.business_fields_updated.append(field)

        return business

    def _apply_opening_hours(self, business: Business, extracted_hours, summary: ExtractionSummary) -> None:
        if not extracted_hours:
            return
        existing = {oh.day_of_week: oh for oh in business.opening_hours}
        for item in extracted_hours:
            row = existing.get(item.day_of_week)
            if row is None:
                row = OpeningHour(business_id=business.id, day_of_week=item.day_of_week)
                self.db.add(row)
                existing[item.day_of_week] = row
            row.open_time = item.open_time
            row.close_time = item.close_time
            row.is_closed = item.is_closed
            summary.opening_hours_updated += 1

    def _apply_services(self, business: Business, extracted_services, summary: ExtractionSummary) -> dict[str, Service]:
        services_by_name: dict[str, Service] = {
            s.name.strip().lower(): s for s in self.db.query(Service).filter(Service.business_id == business.id)
        }
        for item in extracted_services:
            key = item.name.strip().lower()
            service = services_by_name.get(key)
            if service is None:
                service = Service(business_id=business.id, name=item.name.strip())
                self.db.add(service)
                services_by_name[key] = service
                summary.services_created += 1
            else:
                summary.services_updated += 1

            if item.description:
                service.description = item.description
            if item.price is not None:
                service.price = item.price
            if item.duration_minutes is not None:
                service.duration_minutes = item.duration_minutes

        self.db.flush()
        return services_by_name

    def _apply_staff(self, extracted_staff, services_by_name: dict[str, Service], summary: ExtractionSummary) -> None:
        if not extracted_staff:
            return
        existing_staff = {s.name.strip().lower(): s for s in self.db.query(Staff).all()}
        for item in extracted_staff:
            key = item.name.strip().lower()
            member = existing_staff.get(key)
            if member is None:
                member = Staff(name=item.name.strip())
                self.db.add(member)
                existing_staff[key] = member
                summary.staff_created += 1
            else:
                summary.staff_updated += 1

            if item.email:
                member.email = item.email
            if item.phone:
                member.phone = item.phone

            for service_name in item.service_names:
                service = services_by_name.get(service_name.strip().lower())
                if service is not None and service not in member.services:
                    member.services.append(service)

    def extract_and_apply(self, document_text: str) -> ExtractionSummary:
       
        summary = ExtractionSummary()

        result = self._call_llm(document_text)
        if result is None:
            return summary

        try:
            business = self._apply_business(result.business, summary)
            self.db.flush()
            self._apply_opening_hours(business, result.opening_hours, summary)
            services_by_name = self._apply_services(business, result.services, summary)
            self._apply_staff(result.staff, services_by_name, summary)
            self.db.commit()
        except Exception:
            logger.exception("Failed to apply extracted document fields to the database")
            self.db.rollback()
            return ExtractionSummary()

        return summary