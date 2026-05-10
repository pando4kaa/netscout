"""
Notifications API - change notifications produced by scan comparison.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

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
    domain: Optional[str] = Query(None),
    unread_only: bool = Query(False),
):
    """List notifications for the current user."""
    return {
        "notifications": list_notifications(
            db, user.id, limit=limit, offset=offset, domain=domain, unread_only=unread_only
        ),
        "unread_count": get_unread_count(db, user.id),
    }


@router.get("/notifications/unread-count")
async def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Return the unread-notification count for the badge in the UI."""
    return {"count": get_unread_count(db, user.id)}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Mark a single notification as read."""
    return {"success": mark_read(db, notification_id, user.id)}


@router.patch("/notifications/read-all")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Mark every unread notification for the current user as read."""
    return {"success": True, "updated": mark_all_read(db, user.id)}


@router.get("/notifications/{notification_id}/report")
async def get_notification_report_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Return the full comparison report behind a notification (used for details + export)."""
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
    """Stream the notification report as a downloadable JSON file."""
    report = get_notification_report(db, notification_id, user.id)
    if not report:
        return {"error": "Notification not found"}
    domain = report.get("notification", {}).get("domain", "report")
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    filename = f"notification_{notification_id}_{domain}.json"
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
