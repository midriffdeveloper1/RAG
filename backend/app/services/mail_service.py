"""Outbound email via plain smtplib (no extra dependency). Sending itself
happens inside a Celery task (app.tasks.mail_tasks) so a slow/unreachable
SMTP server never blocks an appointment booking/cancel/reschedule request.

Stays a silent no-op (logged, not raised) when MAIL_ENABLED is false or
SMTP isn't configured, so the rest of the app works fine without email set
up — see .env.example.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def is_mail_configured() -> bool:
    return bool(
        settings.mail_enabled
        and settings.smtp_host
        and settings.smtp_username
        and settings.smtp_password
        and (settings.mail_from_address or settings.smtp_username)
    )


def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """Sends synchronously (called from inside the Celery task, which is
    already off the request thread). Returns False (and logs) instead of
    raising, so a mail outage never surfaces as a 500 to the admin/customer
    — the booking itself already succeeded by the time this runs."""

    if not is_mail_configured():
        logger.info(
            "Mail disabled/unconfigured — skipping email to %s: %s", to_email, subject
        )
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.mail_from_name} <{settings.mail_from_address or settings.smtp_username}>"
    message["To"] = to_email

    if text_body:
        message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(
                settings.mail_from_address or settings.smtp_username, [to_email], message.as_string()
            )
        return True
    except Exception:
        logger.exception("Failed to send email to %s (subject=%r)", to_email, subject)
        return False