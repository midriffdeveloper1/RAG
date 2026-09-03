from datetime import date as date_

from pydantic import BaseModel, Field, model_validator


class HolidayBase(BaseModel):
    """A closure the business defines for the assistant to respect."""

    date: date_ | None = None
    day_of_week: str | None = Field(
        default=None,
        description="One of Monday..Sunday, for a recurring weekly closure.",
    )
    is_full_day: bool = True
    start_time: str | None = Field(default=None, description="HH:MM, required if is_full_day is False")
    end_time: str | None = Field(default=None, description="HH:MM, required if is_full_day is False")
    note: str | None = Field(default=None, max_length=255)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate(self) -> "HolidayBase":
        if bool(self.date) == bool(self.day_of_week):
            raise ValueError("Provide exactly one of 'date' or 'day_of_week'.")
        if self.day_of_week and self.day_of_week.title() not in {
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        }:
            raise ValueError("day_of_week must be a full weekday name, e.g. 'Sunday'.")
        if not self.is_full_day and (not self.start_time or not self.end_time):
            raise ValueError("start_time and end_time are required when is_full_day is False.")
        return self


class HolidayCreate(HolidayBase):
    pass


class HolidayUpdate(BaseModel):
    date: date_ | None = None
    day_of_week: str | None = None
    is_full_day: bool | None = None
    start_time: str | None = None
    end_time: str | None = None
    note: str | None = None
    is_active: bool | None = None


class HolidayOut(BaseModel):
    id: str
    date: date_ | None = None
    day_of_week: str | None = None
    is_full_day: bool
    start_time: str | None = None
    end_time: str | None = None
    note: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}