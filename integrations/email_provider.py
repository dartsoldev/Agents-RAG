"""Send reviewed correspondence over TLS SMTP; demo deliveries are explicitly simulated."""

import smtplib
import ssl
from email.message import EmailMessage

from backend.config import settings


def deliver(approval):
    if settings.demo_mode:
        return "simulated"
    if not all(
        [
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from,
        ]
    ):
        raise ValueError("Configure SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM first")
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = approval.payload["to"]
    message["Subject"] = approval.title
    message["Message-ID"] = f"<{approval.id}@arav-case-operations.local>"
    message.set_content(approval.body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    return "sent"
