"""
Scheduler service — runs scheduled scans in background.
"""

from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import ScheduledScan
from app.services.scan_service import run_scan


_scheduler: Optional[BackgroundScheduler] = None


def _run_scheduled_scan(schedule_id: int, domain: str, user_id: int) -> None:
    """Execute a scheduled scan (called by APScheduler)."""
    db = SessionLocal()
    try:
        run_scan(domain, db, user_id=user_id)
        record = db.query(ScheduledScan).filter(ScheduledScan.id == schedule_id).first()
        if record:
            record.last_run_at = datetime.utcnow()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Start scheduler and load jobs from DB."""
    scheduler = get_scheduler()
    if scheduler.running:
        return
    db = SessionLocal()
    try:
        for s in db.query(ScheduledScan).filter(
            ScheduledScan.enabled == True,
            ScheduledScan.user_id.isnot(None),
        ).all():
            scheduler.add_job(
                _run_scheduled_scan,
                trigger=IntervalTrigger(hours=s.interval_hours),
                id=f"sched_{s.id}",
                args=[s.id, s.domain, s.user_id],
                replace_existing=True,
            )
        scheduler.start()
    finally:
        db.close()


def add_scheduled_scan(db: Session, user_id: int, domain: str, interval_hours: int = 24) -> ScheduledScan:
    """Add a new scheduled scan (requires user_id)."""
    s = ScheduledScan(user_id=user_id, domain=domain, interval_hours=max(1, interval_hours), enabled=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.add_job(
            _run_scheduled_scan,
            trigger=IntervalTrigger(hours=s.interval_hours),
            id=f"sched_{s.id}",
            args=[s.id, s.domain, s.user_id],
        )
    return s


def remove_scheduled_scan(db: Session, schedule_id: int, user_id: int) -> bool:
    """Remove a scheduled scan (only owner)."""
    s = db.query(ScheduledScan).filter(ScheduledScan.id == schedule_id, ScheduledScan.user_id == user_id).first()
    if not s:
        return False
    db.delete(s)
    db.commit()
    scheduler = get_scheduler()
    if scheduler.running:
        try:
            scheduler.remove_job(f"sched_{schedule_id}")
        except Exception:
            pass
    return True


def toggle_scheduled_scan(db: Session, schedule_id: int, enabled: bool, user_id: int) -> Optional[ScheduledScan]:
    """Enable or disable a scheduled scan (only owner)."""
    s = db.query(ScheduledScan).filter(ScheduledScan.id == schedule_id, ScheduledScan.user_id == user_id).first()
    if not s:
        return None
    s.enabled = enabled
    db.commit()
    db.refresh(s)
    scheduler = get_scheduler()
    if scheduler.running:
        try:
            scheduler.remove_job(f"sched_{schedule_id}")
        except Exception:
            pass
        if enabled:
            scheduler.add_job(
                _run_scheduled_scan,
                trigger=IntervalTrigger(hours=s.interval_hours),
                id=f"sched_{s.id}",
                args=[s.id, s.domain, s.user_id],
            )
    return s


def list_scheduled_scans(db: Session, user_id: int) -> List[dict]:
    """List scheduled scans for user."""
    records = db.query(ScheduledScan).filter(ScheduledScan.user_id == user_id).order_by(ScheduledScan.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "domain": r.domain,
            "interval_hours": r.interval_hours,
            "enabled": r.enabled,
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
