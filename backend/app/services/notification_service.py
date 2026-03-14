"""
Notification service — creates change notifications from scan comparison.
Runs after scan completion when previous scan exists for same domain.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Notification, ScanRecord
from app.services.comparison_service import build_comparison
from app.services.scan_service import get_scan


def _create_notifications_from_comparison(
    db: Session,
    user_id: int,
    domain: str,
    scan_id: str,
    scan_id_prev: str,
    comparison: Dict[str, Any],
) -> List[Notification]:
    """Build notification records from comparison result."""
    notifications: List[Notification] = []
    summary = comparison.get("summary") or {}
    subdomains = comparison.get("subdomains") or {}
    ssl = comparison.get("ssl") or {}
    ports = comparison.get("ports") or {}
    alerts = comparison.get("alerts") or {}

    # SSL: certificate expired
    for ch in ssl.get("expired_changes") or []:
        if ch.get("is_expired_2") and not ch.get("was_expired_1"):
            notifications.append(Notification(
                user_id=user_id,
                domain=domain,
                scan_id=scan_id,
                scan_id_prev=scan_id_prev,
                type="ssl_cert_expired",
                title=f"Сертифікат прострочено: {ch.get('host', domain)}",
                message=f"SSL-сертифікат для {ch.get('host', domain)} завершив дію.",
                details=ch,
                severity="critical",
            ))

    # SSL: new certificate host
    for h in ssl.get("hosts_only_in_2") or []:
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="ssl_cert_new",
            title=f"Новий сертифікат: {h}",
            message=f"З'явився SSL-сертифікат для {h}.",
            details={"host": h},
            severity="info",
        ))

    # Subdomains added
    added = subdomains.get("only_in_2") or []
    if added:
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="subdomain_added",
            title=f"Нові піддомени: +{len(added)}",
            message=f"Додано {len(added)} піддомен(ів): {', '.join(added[:5])}{'...' if len(added) > 5 else ''}",
            details={"added": added, "count": len(added)},
            severity="info",
        ))

    # Subdomains removed
    removed = subdomains.get("only_in_1") or []
    if removed:
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="subdomain_removed",
            title=f"Піддомени зникли: -{len(removed)}",
            message=f"Прибрано {len(removed)} піддомен(ів): {', '.join(removed[:5])}{'...' if len(removed) > 5 else ''}",
            details={"removed": removed, "count": len(removed)},
            severity="warning",
        ))

    # Ports opened
    new_ports = ports.get("new_ports_count") or 0
    if new_ports > 0:
        by_ip = ports.get("by_ip") or {}
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="port_opened",
            title=f"Відкрито нові порти: +{new_ports}",
            message=f"Виявлено {new_ports} нових відкритих портів.",
            details={"by_ip": by_ip, "new_ports_count": new_ports},
            severity="warning",
        ))

    # Ports closed
    closed = ports.get("closed_ports_count") or 0
    if closed > 0:
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="port_closed",
            title=f"Закрито порти: -{closed}",
            message=f"Закрито {closed} порт(ів).",
            details=ports,
            severity="info",
        ))

    # New alerts (risks)
    new_alerts = alerts.get("only_in_2") or []
    if new_alerts:
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="alert_new",
            title=f"Нові ризики: +{len(new_alerts)}",
            message=f"Виявлено {len(new_alerts)} нових попереджень: {new_alerts[0].get('message', '')[:80]}...",
            details={"alerts": new_alerts, "count": len(new_alerts)},
            severity="critical" if any(a.get("level") == "HIGH" for a in new_alerts) else "warning",
        ))

    # Risk score change (significant)
    risk_delta = summary.get("risk_delta") or 0
    if abs(risk_delta) >= 20:
        notifications.append(Notification(
            user_id=user_id,
            domain=domain,
            scan_id=scan_id,
            scan_id_prev=scan_id_prev,
            type="risk_changed",
            title=f"Зміна ризику: {summary.get('risk_1', 0)} → {summary.get('risk_2', 0)}",
            message=f"Risk score змінився на {risk_delta:+d}.",
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

    for n in notifications:
        db.add(n)
    db.commit()

    # Send email if user has it enabled
    try:
        from app.db.models import User
        from app.services.email_service import send_notification_email
        user = db.query(User).filter(User.id == user_id).first()
        if user and getattr(user, "email_notifications_enabled", False) and user.email:
            items = [
                {"title": n.title, "message": n.message}
                for n in notifications
            ]
            send_notification_email(user.email, domain, items)
    except Exception:
        pass

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
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if domain:
        q = q.filter(Notification.domain.ilike(f"%{domain}%"))
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    records = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": r.id,
            "domain": r.domain,
            "scan_id": r.scan_id,
            "scan_id_prev": r.scan_id_prev,
            "type": r.type,
            "title": r.title,
            "message": r.message,
            "details": r.details,
            "severity": r.severity,
            "read_at": r.read_at.isoformat() if r.read_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


def get_unread_count(db: Session, user_id: int) -> int:
    """Get count of unread notifications."""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    ).count()


def mark_read(db: Session, notification_id: int, user_id: int) -> bool:
    """Mark notification as read."""
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not n:
        return False
    n.read_at = datetime.utcnow()
    db.commit()
    return True


def mark_all_read(db: Session, user_id: int) -> int:
    """Mark all notifications as read. Returns count updated."""
    from sqlalchemy import update
    stmt = update(Notification).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
    ).values(read_at=datetime.utcnow())
    result = db.execute(stmt)
    count = result.rowcount if result.rowcount is not None else 0
    db.commit()
    return count


def get_notification_report(db: Session, notification_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get full comparison report for a notification (for export).
    Fetches both scans and builds comparison.
    """
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not n or not n.scan_id or not n.scan_id_prev:
        return None
    from app.services.scan_service import get_scan
    from app.services.comparison_service import build_comparison
    r1 = get_scan(db, n.scan_id_prev)
    r2 = get_scan(db, n.scan_id)
    if not r1 or not r2:
        return None
    r1["scan_id"] = n.scan_id_prev
    r2["scan_id"] = n.scan_id
    comparison = build_comparison(r1, r2)
    return {
        "notification": {
            "id": n.id,
            "domain": n.domain,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        },
        "comparison": comparison,
    }
