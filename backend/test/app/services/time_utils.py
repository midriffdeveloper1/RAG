import re
from datetime import date, datetime, time

_DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]
_TIME_FORMATS = ["%H:%M", "%I:%M %p", "%I %p", "%H%M"]

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")


def parse_date(value: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Couldn't understand the date '{value}'. Use YYYY-MM-DD.")


def parse_time(value: str) -> time:
    cleaned = value.strip().upper().replace(".", "")
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Couldn't understand the time '{value}'. Use HH:MM (24-hour).")


def is_valid_email(value: str) -> bool:
    return bool(_EMAIL_PATTERN.match(value.strip()))


def is_valid_phone(value: str) -> bool:
    return bool(_PHONE_PATTERN.match(re.sub(r"[\s-]", "", value.strip())))


def day_name(value: date) -> str:
    return value.strftime("%A")