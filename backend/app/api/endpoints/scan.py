"""
Scan endpoints - REST + WebSocket interface for running and exporting scans.
"""

import asyncio
import csv
import logging
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, get_current_user_required
from app.db.database import SessionLocal, get_db
from app.db.models import User
from app.services.auth_service import decode_token
from app.services.neo4j_service import is_neo4j_available
from app.services.scan_service import compare_scans, get_scan, get_scan_history, run_scan
from app.services.scheduler_service import (
    add_scheduled_scan,
    list_scheduled_scans,
    remove_scheduled_scan,
    update_scheduled_scan,
)
from src.utils.validators import normalize_domain

logger = logging.getLogger(__name__)
router = APIRouter()

_DEBUG_API_KEY_NAMES = (
    "SHODAN_API_KEY",
    "VIRUSTOTAL_API_KEY",
    "ALIENVAULT_OTX_API_KEY",
    "ABUSEIPDB_API_KEY",
    "SECURITYTRAILS_API_KEY",
    "CERTSPOTTER_API_TOKEN",
    "ZOOMEYE_API_KEY",
    "PHISHTANK_APP_KEY",
    "CRIMINALIP_API_KEY",
    "PULSEDIVE_API_KEY",
    "NVD_API_KEY",
    "CENSYS_API_TOKEN",
    "CENSYS_API_ID",
    "CENSYS_API_SECRET",
)


@router.get("/debug/neo4j")
async def debug_neo4j():
    """Return whether Neo4j is configured and reachable."""
    try:
        return {"neo4j": "connected" if is_neo4j_available() else "not configured or unreachable"}
    except Exception as exc:
        logger.warning("Neo4j debug check failed: %s", exc)
        return {"neo4j": "error", "message": str(exc)}


@router.get("/debug/keys")
async def debug_api_keys(_: User = Depends(get_current_user_required)):
    """Report which external-API keys are present (values are never returned)."""
    from src.config import settings

    status: dict = {}
    for name in _DEBUG_API_KEY_NAMES:
        value = getattr(settings, name, None)
        status[name.lower()] = "set" if value else "not set"
    return status


class ScanRequest(BaseModel):
    domain: str


class ScheduleRequest(BaseModel):
    domain: str
    interval_hours: int = 24


class ScheduleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    domain: Optional[str] = None
    interval_hours: Optional[int] = None

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.enabled is None and self.domain is None and self.interval_hours is None:
            raise ValueError("At least one of enabled, domain, interval_hours is required")
        return self


@router.post("/scan")
async def start_scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Start a domain scan. Results are persisted only for authenticated users."""
    try:
        user_id = user.id if user else None
        scan_id, results = run_scan(request.domain, db, user_id=user_id)
        return {
            "success": True,
            "scan_id": scan_id,
            "results": results.model_dump(mode="json"),
            "saved": user_id is not None,
        }
    except Exception as exc:
        logger.warning("Scan failed for %s: %s", request.domain, exc)
        return {"success": False, "error": str(exc)}


@router.get("/scan/history")
async def scan_history(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    domain: Optional[str] = Query(None),
    risk_min: Optional[int] = Query(None),
    risk_max: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """List scans. When authenticated, only the current user's scans are returned."""
    user_id = user.id if user else None
    scans = get_scan_history(
        db,
        limit=limit,
        offset=offset,
        domain=domain,
        risk_min=risk_min,
        risk_max=risk_max,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
    )
    return {"scans": scans}


@router.get("/scan/compare")
async def scan_compare(
    scan_id_1: str = Query(..., description="First scan ID"),
    scan_id_2: str = Query(..., description="Second scan ID"),
    db: Session = Depends(get_db),
):
    """Compare two scans (subdomains, IPs, risk). Only scans of the same domain are comparable."""
    comparison, error = compare_scans(db, scan_id_1, scan_id_2)
    if error:
        return {"error": error}
    return {"comparison": comparison}


@router.get("/scan/{scan_id}")
async def get_scan_results(scan_id: str, db: Session = Depends(get_db)):
    """Return scan results for the given ``scan_id``."""
    results = get_scan(db, scan_id)
    if results is None:
        return {"scan_id": scan_id, "status": "not_found", "results": None}
    return {"scan_id": scan_id, "status": "completed", "results": results}


@router.get("/scan/{scan_id}/export/json")
async def export_json(scan_id: str, db: Session = Depends(get_db)):
    """Export scan results as raw JSON."""
    results = get_scan(db, scan_id)
    if results is None:
        return {"error": "Scan not found"}
    return results


@router.get("/scan/{scan_id}/export/csv")
async def export_csv(scan_id: str, db: Session = Depends(get_db)):
    """Export subdomains and IP addresses as a CSV download."""
    results = get_scan(db, scan_id)
    if results is None:
        return {"error": "Scan not found"}

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["type", "value"])
    domain = results.get("target_domain", "")
    writer.writerow(["domain", domain])
    for sub in results.get("subdomains") or []:
        writer.writerow(["subdomain", sub])
    dns = results.get("dns_info") or {}
    for ip in dns.get("a_records") or []:
        writer.writerow(["ip", ip])
    for ip in dns.get("aaaa_records") or []:
        writer.writerow(["ipv6", ip])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scan_{domain}.csv"},
    )


@router.get("/schedules")
async def get_schedules(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """List scheduled scans (auth required)."""
    return {"schedules": list_scheduled_scans(db, user.id)}


@router.post("/schedules")
async def create_schedule(
    request: ScheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Create a scheduled scan (auth required)."""
    try:
        domain = normalize_domain(request.domain)
        schedule = add_scheduled_scan(db, user.id, domain, request.interval_hours)
        return {
            "success": True,
            "schedule": {
                "id": schedule.id,
                "domain": schedule.domain,
                "interval_hours": schedule.interval_hours,
            },
        }
    except Exception as exc:
        logger.warning("Failed to create schedule for %s: %s", request.domain, exc)
        return {"success": False, "error": str(exc)}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Delete a scheduled scan (auth required)."""
    return {"success": remove_scheduled_scan(db, schedule_id, user.id)}


@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    request: ScheduleUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Update a scheduled scan: enable/disable, domain, and/or interval (auth required)."""
    domain_norm: Optional[str] = None
    if request.domain is not None:
        try:
            domain_norm = normalize_domain(request.domain)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    schedule = update_scheduled_scan(
        db,
        schedule_id,
        user.id,
        domain=domain_norm if request.domain is not None else None,
        interval_hours=request.interval_hours,
        enabled=request.enabled,
    )
    if schedule is None:
        return {"success": False, "error": "Not found"}
    return {
        "success": True,
        "schedule": {
            "id": schedule.id,
            "domain": schedule.domain,
            "interval_hours": schedule.interval_hours,
            "enabled": schedule.enabled,
        },
    }


@router.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    """
    WebSocket: start scan with real-time progress.
    Client sends: {"domain": "example.com", "token": "jwt..."} (token optional; if present, scan is saved)
    Server sends: {"stage": "dns", "progress": 20, "message": "..."} then {"stage": "done", "results": {...}, "saved": true/false}
    """
    await websocket.accept()
    progress_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(stage: str, progress: int, message: str) -> None:
        progress_queue.put_nowait({"stage": stage, "progress": progress, "message": message})

    async def send_progress() -> None:
        while True:
            msg = await progress_queue.get()
            if msg.get("stage") == "done":
                break
            await websocket.send_json(msg)

    try:
        request = await websocket.receive_json()
        domain = request.get("domain")
        if not domain:
            await websocket.send_json({"error": "domain required"})
            await websocket.close()
            return

        user_id: Optional[int] = None
        token = request.get("token")
        if token:
            payload = decode_token(token)
            if payload and "sub" in payload:
                try:
                    user_id = int(payload["sub"])
                except (ValueError, TypeError):
                    user_id = None

        db = SessionLocal()
        progress_task = asyncio.create_task(send_progress())
        try:
            scan_id, results = await asyncio.to_thread(
                run_scan, domain, db, on_progress, user_id
            )
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            await websocket.send_json({
                "stage": "done",
                "progress": 100,
                "scan_id": scan_id,
                "results": results.model_dump(mode="json"),
                "saved": user_id is not None,
            })
        finally:
            db.close()
    except WebSocketDisconnect:
        logger.debug("WebSocket scan client disconnected")
    except Exception as exc:
        logger.warning("WebSocket scan failed: %s", exc)
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception as send_exc:
            logger.debug("Failed to push WebSocket error frame: %s", send_exc)
