"""Small inline HTML builders for the appointment lifecycle emails. Kept as
plain functions (subject, html) rather than a templating engine — the
project has no Jinja-for-email setup and these are short enough not to
need one.
"""

from app.core.config import get_settings

settings = get_settings()

_WRAPPER = """
<div style="font-family: -apple-system, Segoe UI, Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px; color: #2b2b28;">
  <h2 style="margin: 0 0 12px; font-size: 18px; color: #3a2f28;">{heading}</h2>
  <p style="margin: 0 0 16px; font-size: 14px; line-height: 1.5;">{intro}</p>
  <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 16px;">
    {rows}
  </table>
  <p style="margin: 0; font-size: 12.5px; color: #7a7268;">{footer}</p>
</div>
"""

_ROW = """
<tr>
  <td style="padding: 6px 0; color: #7a7268; width: 40%;">{label}</td>
  <td style="padding: 6px 0; font-weight: 600;">{value}</td>
</tr>
"""


def _render(heading: str, intro: str, rows: dict[str, str], footer: str) -> str:
    rows_html = "".join(_ROW.format(label=k, value=v) for k, v in rows.items())
    return _WRAPPER.format(heading=heading, intro=intro, rows=rows_html, footer=footer)


def booking_confirmation_email(appointment_data: dict) -> tuple[str, str]:
    subject = f"Booking confirmed — {appointment_data['service']} on {appointment_data['display_date']}"
    html = _render(
        heading="Your appointment is confirmed",
        intro=f"Hi {appointment_data['customer_name']}, this confirms your booking.",
        rows={
            "Reference": appointment_data["appointment_id"],
            "Service": appointment_data["service"],
            "With": appointment_data.get("staff", "—"),
            "Date": appointment_data["display_date"],
            "Time": appointment_data["display_time"],
        },
        footer=(
            "Need to change or cancel? Reply to this email or contact us directly, "
            "quoting your reference above."
        ),
    )
    return subject, html


def cancellation_email(appointment_data: dict) -> tuple[str, str]:
    subject = f"Appointment cancelled — {appointment_data.get('service', '')}"
    rows = {
        "Reference": appointment_data["appointment_id"],
        "Service": appointment_data.get("service", "—"),
        "Was scheduled": appointment_data.get("display_date", "—"),
    }
    if appointment_data.get("cancellation_reason"):
        rows["Reason"] = appointment_data["cancellation_reason"]

    html = _render(
        heading="Your appointment has been cancelled",
        intro=f"Hi {appointment_data.get('customer_name', '')}, this confirms the cancellation below.",
        rows=rows,
        footer="Want to rebook? Just get in touch or head back to the booking page.",
    )
    return subject, html


def reschedule_email(appointment_data: dict) -> tuple[str, str]:
    subject = f"Appointment rescheduled — {appointment_data['service']} on {appointment_data['display_date']}"
    html = _render(
        heading="Your appointment has been rescheduled",
        intro=f"Hi {appointment_data['customer_name']}, here are your new appointment details.",
        rows={
            "New reference": appointment_data["appointment_id"],
            "Service": appointment_data["service"],
            "With": appointment_data.get("staff", "—"),
            "New date": appointment_data["display_date"],
            "New time": appointment_data["display_time"],
        },
        footer="Your previous booking has been cancelled automatically — no action needed.",
    )
    return subject, html