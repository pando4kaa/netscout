"""
Scan service - orchestrates scanning and persistence.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import ScanRecord
from src.core.models import ScanResult
from src.core.orchestrator import scan_domain
from src.utils.validators import normalize_domain

logger = logging.getLogger(__name__)


def _generate_scan_id() -> str:
    """Generate a globally-unique scan ID."""
    return f"scan_{uuid.uuid4().hex[:12]}"


def run_scan(
    domain: str,
    db: Session,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
    user_id: Optional[int] = None,
) -> tuple[str, ScanResult]:
    """
    Run a scan. Persist to DB only when ``user_id`` is provided (authenticated).

    Returns:
        (scan_id, ScanResult)
    """
    domain = normalize_domain(domain)
    scan_id = _generate_scan_id()
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

        try:
            from app.services.neo4j_service import persist_scan_to_neo4j

            persist_scan_to_neo4j(scan_id, domain, results.model_dump(mode="json"))
        except Exception as exc:
            logger.warning("Neo4j persist failed for scan %s: %s", scan_id, exc)

        try:
            from app.services.notification_service import create_notifications_after_scan

            create_notifications_after_scan(
                db, user_id, domain, scan_id, results.model_dump(mode="json"),
            )
        except Exception as exc:
            logger.warning("Notification creation failed for scan %s: %s", scan_id, exc)

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
    """Return recent scans with summary stats; filter by user_id when provided."""
    query = db.query(ScanRecord).order_by(ScanRecord.created_at.desc())
    if user_id is not None:
        query = query.filter(ScanRecord.user_id == user_id)
    else:
        # Anonymous scans are never persisted, so this branch always yields [].
        query = query.filter(ScanRecord.user_id.is_(None))
    if domain:
        query = query.filter(ScanRecord.domain.ilike(f"%{domain}%"))
    if date_from:
        try:
            query = query.filter(
                ScanRecord.created_at >= datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            )
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            query = query.filter(
                ScanRecord.created_at <= datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            )
        except (ValueError, TypeError):
            pass
    records = query.offset(offset).limit(limit).all()

    result: List[Dict[str, Any]] = []
    for record in records:
        item: Dict[str, Any] = {
            "scan_id": record.scan_id,
            "domain": record.domain,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        if record.results:
            try:
                summary = (json.loads(record.results).get("summary") or {})
                item["total_subdomains"] = summary.get("total_subdomains", 0)
                item["total_alerts"] = summary.get("total_alerts", 0)
                item["risk_score"] = summary.get("risk_score", 0)
                risk_score = item.get("risk_score") or 0
                if risk_min is not None and risk_score < risk_min:
                    continue
                if risk_max is not None and risk_score > risk_max:
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

    scan_one = get_scan(db, scan_id_1)
    scan_two = get_scan(db, scan_id_2)
    if not scan_one or not scan_two:
        return None, "One or both scans not found"
    if (scan_one.get("target_domain") or "").lower() != (scan_two.get("target_domain") or "").lower():
        return None, "Can only compare scans of the same domain"
    scan_one["scan_id"] = scan_id_1
    scan_two["scan_id"] = scan_id_2
    return build_comparison(scan_one, scan_two), None
