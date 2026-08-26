from pydantic import BaseModel, Field


class ExtractedOpeningHour(BaseModel):
    day_of_week: str
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool = False


class ExtractedService(BaseModel):
    name: str
    description: str | None = None
    price: float | None = None
    duration_minutes: int | None = None


class ExtractedStaff(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    service_names: list[str] = Field(default_factory=list)


class ExtractedBusiness(BaseModel):
    name: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class DocumentExtractionResult(BaseModel):

    business: ExtractedBusiness = Field(default_factory=ExtractedBusiness)
    opening_hours: list[ExtractedOpeningHour] = Field(default_factory=list)
    services: list[ExtractedService] = Field(default_factory=list)
    staff: list[ExtractedStaff] = Field(default_factory=list)


class ExtractionSummary(BaseModel):

    business_fields_updated: list[str] = Field(default_factory=list)
    opening_hours_updated: int = 0
    services_created: int = 0
    services_updated: int = 0
    staff_created: int = 0
    staff_updated: int = 0

    def is_empty(self) -> bool:
        return not (
            self.business_fields_updated
            or self.opening_hours_updated
            or self.services_created
            or self.services_updated
            or self.staff_created
            or self.staff_updated
        )

    def to_text(self) -> str:
        if self.is_empty():
            return "No business details were found to extract from this document."
        parts = []
        if self.business_fields_updated:
            parts.append(f"business info: {', '.join(self.business_fields_updated)}")
        if self.opening_hours_updated:
            parts.append(f"{self.opening_hours_updated} opening-hour entries")
        if self.services_created or self.services_updated:
            parts.append(f"{self.services_created} new / {self.services_updated} updated services")
        if self.staff_created or self.staff_updated:
            parts.append(f"{self.staff_created} new / {self.staff_updated} updated staff")
        return "Updated from this document — " + "; ".join(parts) + "."