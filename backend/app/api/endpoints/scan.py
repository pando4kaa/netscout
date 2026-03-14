"""
Scan endpoints
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, get_current_user_required
from app.db.database import get_db
from app.db.models import User
from app.services.scan_service import run_scan, get_scan, get_scan_history, compare_scans
from app.services.scheduler_service import (
    add_scheduled_scan,
    remove_scheduled_scan,
    toggle_scheduled_scan,
    list_scheduled_scans,
)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

router = APIRouter()


@router.get("/debug/neo4j")
async def debug_neo4j():
    """Check if Neo4j is configured and reachable."""
    try:
        from app.services.neo4j_service import is_neo4j_available
        return {"neo4j": "connected" if is_neo4j_available() else "not configured or unreachable"}
    except Exception as e:
        return {"neo4j": "error", "message": str(e)}


@router.get("/debug/keys")
async def debug_api_keys():
    """Check if API keys are loaded (masks values for security)."""
    from src.config.settings import (
        SHODAN_API_KEY,
        VIRUSTOTAL_API_KEY,
        CENSYS_API_TOKEN,
        CENSYS_API_ID,
        CENSYS_API_SECRET,
        ALIENVAULT_OTX_API_KEY,
        ABUSEIPDB_API_KEY,
        SECURITYTRAILS_API_KEY,
        CERTSPOTTER_API_TOKEN,
        ZOOMEYE_API_KEY,
        PHISHTANK_APP_KEY,
        CRIMINALIP_API_KEY,
        PULSEDIVE_API_KEY,
    )
    return {
        "shodan": "set" if SHODAN_API_KEY else "not set",
        "virustotal": "set" if VIRUSTOTAL_API_KEY else "not set",
        "alienvault_otx": "set" if ALIENVAULT_OTX_API_KEY else "not set",
        "abuseipdb": "set" if ABUSEIPDB_API_KEY else "not set",
        "securitytrails": "set" if SECURITYTRAILS_API_KEY else "not set",
        "certspotter": "set" if CERTSPOTTER_API_TOKEN else "not set",
        "zoomeye": "set" if ZOOMEYE_API_KEY else "not set",
        "phishtank": "set" if PHISHTANK_APP_KEY else "not set",
        "criminalip": "set" if CRIMINALIP_API_KEY else "not set",
        "pulsedive": "set" if PULSEDIVE_API_KEY else "not set",
        "censys_token": "set" if CENSYS_API_TOKEN else "not set",
        "censys_id": "set" if CENSYS_API_ID else "not set",
        "censys_secret": "set" if CENSYS_API_SECRET else "not set",
    }


class ScanRequest(BaseModel):
    domain: str


class ScheduleRequest(BaseModel):
    domain: str
    interval_hours: int = 24


class ScheduleToggleRequest(BaseModel):
    enabled: bool


@router.post("/scan")
async def start_scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Start domain scan. Persist results only when authenticated.
    """
    try:
        user_id = user.id if user else None
        scan_id, results = run_scan(request.domain, db, user_id=user_id)
        return {
            "success": True,
            "scan_id": scan_id,
            "results": results.model_dump(mode="json"),
            "saved": user_id is not None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


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
    """
    Get scan history. When authenticated, returns only user's scans.
    """
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
    """
    Compare two scans (subdomains, IPs, risk). Only scans of the same domain can be compared.
    """
    result, error = compare_scans(db, scan_id_1, scan_id_2)
    if error:
        return {"error": error}
    return {"comparison": result}


@router.get("/scan/{scan_id}")
async def get_scan_results(scan_id: str, db: Session = Depends(get_db)):
    """
    Get scan results by scan_id.
    """
    results = get_scan(db, scan_id)
    if results is None:
        return {"scan_id": scan_id, "status": "not_found", "results": None}
    return {"scan_id": scan_id, "status": "completed", "results": results}


@router.get("/scan/{scan_id}/export/json")
async def export_json(scan_id: str, db: Session = Depends(get_db)):
    """Export scan results as JSON."""
    results = get_scan(db, scan_id)
    if results is None:
        return {"error": "Scan not found"}
    return results


@router.get("/scan/{scan_id}/export/csv")
async def export_csv(scan_id: str, db: Session = Depends(get_db)):
    """Export subdomains and IPs as CSV."""
    import csv
    from fastapi.responses import StreamingResponse
    from io import StringIO

    results = get_scan(db, scan_id)
    if results is None:
        return {"error": "Scan not found"}

    output = StringIO()
    writer = csv.writer(output)
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

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
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
        from src.utils.validators import normalize_domain
        domain = normalize_domain(request.domain)
        s = add_scheduled_scan(db, user.id, domain, request.interval_hours)
        return {"success": True, "schedule": {"id": s.id, "domain": s.domain, "interval_hours": s.interval_hours}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Delete a scheduled scan (auth required)."""
    ok = remove_scheduled_scan(db, schedule_id, user.id)
    return {"success": ok}


@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    request: ScheduleToggleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Enable or disable a scheduled scan (auth required)."""
    s = toggle_scheduled_scan(db, schedule_id, request.enabled, user.id)
    if s is None:
        return {"success": False, "error": "Not found"}
    return {"success": True, "enabled": s.enabled}


@router.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    """
    WebSocket: start scan with real-time progress.
    Client sends: {"domain": "example.com", "token": "jwt..."} (token optional; if present, scan is saved)
    Server sends: {"stage": "dns", "progress": 20, "message": "..."} then {"stage": "done", "results": {...}, "saved": true/false}
    """
    await websocket.accept()
    progress_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(stage: str, progress: int, message: str):
        progress_queue.put_nowait({"stage": stage, "progress": progress, "message": message})

    async def send_progress():
        while True:
            msg = await progress_queue.get()
            if msg.get("stage") == "done":
                break
            await websocket.send_json(msg)

    try:
        data = await websocket.receive_json()
        domain = data.get("domain")
        if not domain:
            await websocket.send_json({"error": "domain required"})
            await websocket.close()
            return

        user_id = None
        token = data.get("token")
        if token:
            from app.services.auth_service import decode_token
            payload = decode_token(token)
            if payload and "sub" in payload:
                try:
                    user_id = int(payload["sub"])
                except (ValueError, TypeError):
                    pass

        from app.db.database import SessionLocal
        db = SessionLocal()

        progress_task = asyncio.create_task(send_progress())
        scan_id, results = await asyncio.to_thread(run_scan, domain, db, on_progress, user_id)
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
        db.close()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
