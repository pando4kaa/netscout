"""
Scan service — orchestrates scanning and persistence.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from src.core.orchestrator import scan_domain
from src.core.models import ScanResult
from src.utils.validators import normalize_domain
from app.db.models import ScanRecord


def _generate_scan_id(domain: str) -> str:
    """Generate unique scan ID."""
    return f"scan_{uuid.uuid4().hex[:12]}"


def run_scan(
    domain: str,
    db: Session,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
    user_id: Optional[int] = None,
) -> tuple[str, ScanResult]:
    """
    Run scan. Persist to DB only when user_id is provided (authenticated user).

    Returns:
        (scan_id, ScanResult)
    """
    domain = normalize_domain(domain)
    scan_id = _generate_scan_id(domain)
    results = scan_domain(domain, on_progress=on_progress)

    if user_id is not None:
        record = ScanRecord(
            scan_id=scan_id,
            domain=domain,
            results=results.model_dump_json(),
            user_id=user_id,
        )
        db.add(record)
        db.commit()

        # Persist to Neo4j if configured
        try:
            from app.services.neo4j_service import persist_scan_to_neo4j
            persist_scan_to_neo4j(scan_id, domain, results.model_dump(mode="json"))
        except Exception:
            pass

    return scan_id, results


def get_scan(db: Session, scan_id: str) -> Optional[Dict[str, Any]]:
    """Get scan results by ID."""
    record = db.query(ScanRecord).filter(ScanRecord.scan_id == scan_id).first()
    if not record or not record.results:
        return None
    return json.loads(record.results)


def get_scan_history(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    domain: Optional[str] = None,
    risk_min: Optional[int] = None,
    risk_max: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get list of recent scans with summary and optional filters. Filter by user_id when provided."""
    q = db.query(ScanRecord).order_by(ScanRecord.created_at.desc())
    if user_id is not None:
        q = q.filter(ScanRecord.user_id == user_id)
    else:
        q = q.filter(ScanRecord.user_id.is_(None))  # Anonymous scans only; we never save those, so []
    if domain:
        q = q.filter(ScanRecord.domain.ilike(f"%{domain}%"))
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            q = q.filter(ScanRecord.created_at >= dt)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            q = q.filter(ScanRecord.created_at <= dt)
        except (ValueError, TypeError):
            pass
    records = q.offset(offset).limit(limit).all()
    result = []
    for r in records:
        item = {
            "scan_id": r.scan_id,
            "domain": r.domain,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        if r.results:
            try:
                data = json.loads(r.results)
                summary = data.get("summary") or {}
                item["total_subdomains"] = summary.get("total_subdomains", 0)
                item["total_alerts"] = summary.get("total_alerts", 0)
                item["risk_score"] = summary.get("risk_score", 0)
                if risk_min is not None and (item.get("risk_score") or 0) < risk_min:
                    continue
                if risk_max is not None and (item.get("risk_score") or 0) > risk_max:
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(item)
    return result


def compare_scans(db: Session, scan_id_1: str, scan_id_2: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Compare two scans and return detailed diff. Only scans of the same domain can be compared.
    Returns (comparison_dict, error_message). error_message is None on success.
    """
    from app.services.comparison_service import build_comparison

    r1 = get_scan(db, scan_id_1)
    r2 = get_scan(db, scan_id_2)
    if not r1 or not r2:
        return None, "One or both scans not found"
    d1 = (r1.get("target_domain") or "").lower()
    d2 = (r2.get("target_domain") or "").lower()
    if d1 != d2:
        return None, "Can only compare scans of the same domain"
    r1["scan_id"] = scan_id_1
    r2["scan_id"] = scan_id_2
    comparison = build_comparison(r1, r2)
    return comparison, None
