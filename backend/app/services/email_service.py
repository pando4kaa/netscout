"""
Email service — sends change notifications. Uses SMTP with best practices to avoid spam.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from src.config.settings import (
    APP_URL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)


def _is_email_configured() -> bool:
    """Check if SMTP is configured."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _build_email_body(domain: str, notifications: List[Dict[str, Any]], unsubscribe_url: str) -> tuple[str, str]:
    """
    Build plain text and HTML body. Professional format to avoid spam filters.
    Returns (plain_text, html).
    """
    lines = [
        f"NetScout виявив зміни на домені {domain}.",
        "",
        "Сповіщення:",
    ]
    for n in notifications[:10]:  # Limit to 10 in email
        lines.append(f"  • {n.get('title', '')}")
        if n.get("message"):
            lines.append(f"    {n.get('message', '')[:120]}")
        lines.append("")
    if len(notifications) > 10:
        lines.append(f"  ... та ще {len(notifications) - 10} сповіщень.")
        lines.append("")

    lines.append("Перегляньте деталі в NetScout:")
    lines.append(f"{APP_URL.rstrip('/')}/notifications")
    lines.append("")
    lines.append("Щоб вимкнути email-сповіщення:")
    lines.append(unsubscribe_url)

    plain = "\n".join(lines)

    html_lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body style='font-family: sans-serif; line-height: 1.5; color: #333;'>",
        f"<p>NetScout виявив зміни на домені <strong>{domain}</strong>.</p>",
        "<p><strong>Сповіщення:</strong></p>",
        "<ul>",
    ]
    for n in notifications[:10]:
        html_lines.append(f"<li><strong>{n.get('title', '')}</strong>")
        if n.get("message"):
            html_lines.append(f"<br><small>{n.get('message', '')[:120]}</small></li>")
        else:
            html_lines.append("</li>")
    if len(notifications) > 10:
        html_lines.append(f"<li>... та ще {len(notifications) - 10} сповіщень.</li>")
    html_lines.append("</ul>")
    html_lines.append(f'<p><a href="{APP_URL.rstrip("/")}/notifications" style="color: #1976d2;">Переглянути в NetScout</a></p>')
    html_lines.append(f'<p style="font-size: 12px; color: #666;">Щоб вимкнути email-сповіщення: <a href="{unsubscribe_url}">{unsubscribe_url}</a></p>')
    html_lines.append("</body></html>")

    html = "\n".join(html_lines)
    return plain, html


def send_notification_email(
    to_email: str,
    domain: str,
    notifications: List[Dict[str, Any]],
) -> bool:
    """
    Send change notification email. Returns True on success.
    Uses List-Unsubscribe header and professional format to reduce spam score.
    """
    if not _is_email_configured():
        return False

    unsubscribe_url = f"{APP_URL.rstrip('/')}/notifications?unsubscribe=1"
    # In production, use a proper unsubscribe token; for now, link to settings

    subject = f"[NetScout] Зміни на {domain}"
    plain, html = _build_email_body(domain, notifications, unsubscribe_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg["X-Priority"] = "3"  # Normal
    msg["Precedence"] = "auto"
    msg["Auto-Submitted"] = "auto-generated"

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except Exception:
        return False
