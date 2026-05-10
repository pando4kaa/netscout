"""
Notification service - creates change notifications from scan comparison.
Runs after scan completion when a previous scan exists for the same domain.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import Notification, ScanRecord
from app.services.comparison_service import build_comparison
from app.services.scan_service import get_scan

logger = logging.getLogger(__name__)

_SUBDOMAIN_PREVIEW = 5
_RISK_DELTA_THRESHOLD = 20


def _make_notification(
    *,
    user_id: int,
    domain: str,
    scan_id: str,
    scan_id_prev: str,
    type_: str,
    title: str,
    message: str,
    details: Any,
    severity: str,
) -> Notification:
    return Notification(
        user_id=user_id,
        domain=domain,
        scan_id=scan_id,
        scan_id_prev=scan_id_prev,
        type=type_,
        title=title,
        message=message,
        details=details,
        severity=severity,
    )


def _join_preview(items: List[str], limit: int = _SUBDOMAIN_PREVIEW) -> str:
    suffix = "..." if len(items) > limit else ""
    return ", ".join(items[:limit]) + suffix


def _create_notifications_from_comparison(
    db: Session,
    user_id: int,
    domain: str,
    scan_id: str,
    scan_id_prev: str,
    comparison: Dict[str, Any],
) -> List[Notification]:
    """Build notification records from a comparison result."""
    notifications: List[Notification] = []
    summary = comparison.get("summary") or {}
    subdomains = comparison.get("subdomains") or {}
    ssl = comparison.get("ssl") or {}
    ports = comparison.get("ports") or {}
    alerts = comparison.get("alerts") or {}

    common_ids = {"user_id": user_id, "domain": domain, "scan_id": scan_id, "scan_id_prev": scan_id_prev}

    for change in ssl.get("expired_changes") or []:
        if change.get("is_expired_2") and not change.get("was_expired_1"):
            host = change.get("host", domain)
            notifications.append(_make_notification(
                **common_ids,
                type_="ssl_cert_expired",
                title=f"Certificate expired: {host}",
                message=f"SSL certificate for {host} has expired.",
                details=change,
                severity="critical",
            ))

    for host in ssl.get("hosts_only_in_2") or []:
        notifications.append(_make_notification(
            **common_ids,
            type_="ssl_cert_new",
            title=f"New certificate: {host}",
            message=f"SSL certificate appeared for {host}.",
            details={"host": host},
            severity="info",
        ))

    added = subdomains.get("only_in_2") or []
    if added:
        notifications.append(_make_notification(
            **common_ids,
            type_="subdomain_added",
            title=f"New subdomains: +{len(added)}",
            message=f"Added {len(added)} subdomain(s): {_join_preview(added)}",
            details={"added": added, "count": len(added)},
            severity="info",
        ))

    removed = subdomains.get("only_in_1") or []
    if removed:
        notifications.append(_make_notification(
            **common_ids,
            type_="subdomain_removed",
            title=f"Subdomains removed: -{len(removed)}",
            message=f"Removed {len(removed)} subdomain(s): {_join_preview(removed)}",
            details={"removed": removed, "count": len(removed)},
            severity="warning",
        ))

    new_ports = ports.get("new_ports_count") or 0
    if new_ports > 0:
        notifications.append(_make_notification(
            **common_ids,
            type_="port_opened",
            title=f"New ports opened: +{new_ports}",
            message=f"Detected {new_ports} new open ports.",
            details={"by_ip": ports.get("by_ip") or {}, "new_ports_count": new_ports},
            severity="warning",
        ))

    closed = ports.get("closed_ports_count") or 0
    if closed > 0:
        notifications.append(_make_notification(
            **common_ids,
            type_="port_closed",
            title=f"Ports closed: -{closed}",
            message=f"Closed {closed} port(s).",
            details=ports,
            severity="info",
        ))

    new_alerts = alerts.get("only_in_2") or []
    if new_alerts:
        first_message = (new_alerts[0].get("message", "") or "")[:80]
        any_high = any(a.get("level") == "HIGH" for a in new_alerts)
        notifications.append(_make_notification(
            **common_ids,
            type_="alert_new",
            title=f"New risks: +{len(new_alerts)}",
            message=f"Detected {len(new_alerts)} new alerts: {first_message}...",
            details={"alerts": new_alerts, "count": len(new_alerts)},
            severity="critical" if any_high else "warning",
        ))

    risk_delta = summary.get("risk_delta") or 0
    if abs(risk_delta) >= _RISK_DELTA_THRESHOLD:
        notifications.append(_make_notification(
            **common_ids,
            type_="risk_changed",
            title=f"Risk change: {summary.get('risk_1', 0)} → {summary.get('risk_2', 0)}",
            message=f"Risk score changed by {risk_delta:+d}.",
            details=summary,
            severity="warning" if risk_delta > 0 else "info",
        ))

    return notifications


def create_notifications_after_scan(
    db: Session,
    user_id: int,
    domain: str,
    scan_id: str,
    current_results: Dict[str, Any],
) -> int:
    """
    Compare current scan with previous, create notifications for changes.
    Returns count of notifications created.
    """
    # Get previous scan for same domain and user
    prev_records = (
        db.query(ScanRecord)
        .filter(
            ScanRecord.domain == domain,
            ScanRecord.user_id == user_id,
            ScanRecord.scan_id != scan_id,
        )
        .order_by(ScanRecord.created_at.desc())
        .limit(1)
        .all()
    )
    if not prev_records:
        return 0

    prev_record = prev_records[0]
    prev_results = get_scan(db, prev_record.scan_id)
    if not prev_results:
        return 0

    current_results["scan_id"] = scan_id
    prev_results["scan_id"] = prev_record.scan_id

    comparison = build_comparison(prev_results, current_results)
    notifications = _create_notifications_from_comparison(
        db, user_id, domain, scan_id, prev_record.scan_id, comparison
    )

    for notification in notifications:
        db.add(notification)
    db.commit()

    try:
        from app.db.models import User
        from app.services.email_service import send_notification_email

        user = db.query(User).filter(User.id == user_id).first()
        if user and getattr(user, "email_notifications_enabled", False) and user.email:
            items = [{"title": n.title, "message": n.message} for n in notifications]
            send_notification_email(user.email, domain, items)
    except Exception as exc:
        logger.warning("Email notification dispatch failed for user %s: %s", user_id, exc)

    return len(notifications)


def list_notifications(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    domain: Optional[str] = None,
    unread_only: bool = False,
) -> List[Dict[str, Any]]:
    """List notifications for user."""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if domain:
        query = query.filter(Notification.domain.ilike(f"%{domain}%"))
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    records = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": record.id,
            "domain": record.domain,
            "scan_id": record.scan_id,
            "scan_id_prev": record.scan_id_prev,
            "type": record.type,
            "title": record.title,
            "message": record.message,
            "details": record.details,
            "severity": record.severity,
            "read_at": record.read_at.isoformat() if record.read_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]


def get_unread_count(db: Session, user_id: int) -> int:
    """Get count of unread notifications."""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    ).count()


def mark_read(db: Session, notification_id: int, user_id: int) -> bool:
    """Mark a single notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not notification:
        return False
    notification.read_at = datetime.utcnow()
    db.commit()
    return True


def mark_all_read(db: Session, user_id: int) -> int:
    """Mark every unread notification for ``user_id`` as read; return rows updated."""
    stmt = update(Notification).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    ).values(read_at=datetime.utcnow())
    result = db.execute(stmt)
    db.commit()
    return result.rowcount if result.rowcount is not None else 0


def get_notification_report(db: Session, notification_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Return the full comparison report for a notification (used for export)."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not notification or not notification.scan_id or not notification.scan_id_prev:
        return None

    prev_scan = get_scan(db, notification.scan_id_prev)
    new_scan = get_scan(db, notification.scan_id)
    if not prev_scan or not new_scan:
        return None
    prev_scan["scan_id"] = notification.scan_id_prev
    new_scan["scan_id"] = notification.scan_id
    return {
        "notification": {
            "id": notification.id,
            "domain": notification.domain,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        },
        "comparison": build_comparison(prev_scan, new_scan),
    }
