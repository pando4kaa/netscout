"""
Notifications API — change notifications from scan comparison.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
from io import StringIO

from app.api.deps import get_current_user_required
from app.db.database import get_db
from app.db.models import User
from app.services.notification_service import (
    list_notifications,
    get_unread_count,
    mark_read,
    mark_all_read,
    get_notification_report,
)

router = APIRouter()


@router.get("/notifications")
async def get_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    domain: str | None = Query(None),
    unread_only: bool = Query(False),
):
    """List notifications for current user."""
    items = list_notifications(db, user.id, limit=limit, offset=offset, domain=domain, unread_only=unread_only)
    count = get_unread_count(db, user.id)
    return {"notifications": items, "unread_count": count}


@router.get("/notifications/unread-count")
async def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Get unread notifications count (for badge)."""
    return {"count": get_unread_count(db, user.id)}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Mark a notification as read."""
    ok = mark_read(db, notification_id, user.id)
    return {"success": ok}


@router.patch("/notifications/read-all")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Mark all notifications as read."""
    count = mark_all_read(db, user.id)
    return {"success": True, "updated": count}


@router.get("/notifications/{notification_id}/report")
async def get_notification_report_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Get full comparison report for a notification (details + export)."""
    report = get_notification_report(db, notification_id, user.id)
    if not report:
        return {"error": "Notification not found"}
    return report


@router.get("/notifications/{notification_id}/export/json")
async def export_notification_report(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Export notification report as JSON file."""
    report = get_notification_report(db, notification_id, user.id)
    if not report:
        return {"error": "Notification not found"}
    domain = report.get("notification", {}).get("domain", "report")
    output = StringIO()
    json.dump(report, output, indent=2, ensure_ascii=False)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=notification_{notification_id}_{domain}.json"},
    )
