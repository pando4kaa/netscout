"""
Email service - sends change notifications. Uses SMTP with best practices to avoid spam.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape as html_escape
from typing import Any, Dict, List

from src.config.settings import (
    APP_URL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)

logger = logging.getLogger(__name__)

_NOTIFICATIONS_PER_EMAIL = 10
_MESSAGE_PREVIEW_CHARS = 120
_SMTP_TIMEOUT_SECONDS = 10


def _is_email_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _build_email_body(
    domain: str, notifications: List[Dict[str, Any]], unsubscribe_url: str
) -> tuple[str, str]:
    """Render the plain-text and HTML bodies. HTML output is escaped."""
    notifications_url = f"{APP_URL.rstrip('/')}/notifications"
    visible = notifications[:_NOTIFICATIONS_PER_EMAIL]
    extra = len(notifications) - _NOTIFICATIONS_PER_EMAIL

    plain_lines = [
        f"NetScout виявив зміни на домені {domain}.",
        "",
        "Сповіщення:",
    ]
    for note in visible:
        plain_lines.append(f"  • {note.get('title', '')}")
        message = (note.get("message") or "")[:_MESSAGE_PREVIEW_CHARS]
        if message:
            plain_lines.append(f"    {message}")
        plain_lines.append("")
    if extra > 0:
        plain_lines.extend([f"  ... та ще {extra} сповіщень.", ""])
    plain_lines.extend([
        "Перегляньте деталі в NetScout:",
        notifications_url,
        "",
        "Щоб вимкнути email-сповіщення:",
        unsubscribe_url,
    ])

    domain_html = html_escape(domain)
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='font-family: sans-serif; line-height: 1.5; color: #333;'>",
        f"<p>NetScout виявив зміни на домені <strong>{domain_html}</strong>.</p>",
        "<p><strong>Сповіщення:</strong></p>",
        "<ul>",
    ]
    for note in visible:
        title = html_escape(str(note.get("title", "")))
        message = html_escape((note.get("message") or "")[:_MESSAGE_PREVIEW_CHARS])
        if message:
            html_parts.append(f"<li><strong>{title}</strong><br><small>{message}</small></li>")
        else:
            html_parts.append(f"<li><strong>{title}</strong></li>")
    if extra > 0:
        html_parts.append(f"<li>... та ще {extra} сповіщень.</li>")
    html_parts.extend([
        "</ul>",
        f'<p><a href="{notifications_url}" style="color: #1976d2;">Переглянути в NetScout</a></p>',
        '<p style="font-size: 12px; color: #666;">'
        f'Щоб вимкнути email-сповіщення: <a href="{unsubscribe_url}">{unsubscribe_url}</a></p>',
        "</body></html>",
    ])

    return "\n".join(plain_lines), "\n".join(html_parts)


def send_notification_email(
    to_email: str,
    domain: str,
    notifications: List[Dict[str, Any]],
) -> bool:
    """
    Send a change-notification email.

    Returns True on success. Uses ``List-Unsubscribe`` header and a professional
    layout to minimise spam-filter score.
    """
    if not _is_email_configured():
        return False

    # TODO: replace with a signed unsubscribe token; current URL just links to settings.
    unsubscribe_url = f"{APP_URL.rstrip('/')}/notifications?unsubscribe=1"
    plain, html = _build_email_body(domain, notifications, unsubscribe_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[NetScout] Зміни на {domain}"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg["X-Priority"] = "3"
    msg["Precedence"] = "auto"
    msg["Auto-Submitted"] = "auto-generated"
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=_SMTP_TIMEOUT_SECONDS) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Email send to %s failed: %s", to_email, exc)
        return False
