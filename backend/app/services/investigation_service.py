"""
Investigation service - CRUD for investigations, run enrichers on entities.
Orchestrates PostgreSQL (metadata) and Neo4j (graph).
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Investigation
from app.services.neo4j_service import (
    add_investigation_entity,
    add_enricher_result_to_investigation,
    get_investigation_graph,
    delete_investigation_graph,
    update_investigation_node_metadata,
    is_neo4j_available,
)

logger = logging.getLogger(__name__)


def require_neo4j_for_investigation():
    """Raise HTTP 503 if Neo4j is not available."""
    if not is_neo4j_available():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Neo4j is required for Investigation mode. Set NEO4J_PASSWORD and ensure Neo4j is running (docker compose up -d)",
        )


def _serialize_investigation(inv: Investigation, *, graph: Optional[Dict[str, Any]] = None,
                             read_only: bool = False) -> Dict[str, Any]:
    """Convert ORM record to API-friendly dict, optionally embedding graph payload."""
    payload: Dict[str, Any] = {
        "id": str(inv.id),
        "name": inv.name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }
    if graph is not None:
        payload["graph"] = graph
    if read_only:
        payload["read_only"] = True
    return payload


def _parse_uuid(value: str) -> Optional[UUID]:
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def _get_owned_investigation(db: Session, investigation_id: str, user_id: int) -> Optional[Investigation]:
    """Return the Investigation owned by ``user_id``, or ``None`` if missing/invalid."""
    uid = _parse_uuid(investigation_id)
    if uid is None:
        return None
    return (
        db.query(Investigation)
        .filter(Investigation.id == uid, Investigation.user_id == user_id)
        .first()
    )


def list_investigations(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """List investigations belonging to ``user_id``."""
    records = (
        db.query(Investigation)
        .filter(Investigation.user_id == user_id)
        .order_by(Investigation.updated_at.desc())
        .all()
    )
    return [_serialize_investigation(record) for record in records]


def create_investigation(db: Session, user_id: int, name: str = "New Investigation") -> Dict[str, Any]:
    """Create a new investigation."""
    require_neo4j_for_investigation()
    inv = Investigation(user_id=user_id, name=name)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return _serialize_investigation(inv)


def get_investigation(db: Session, investigation_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Return investigation metadata together with its Neo4j graph."""
    require_neo4j_for_investigation()
    inv = _get_owned_investigation(db, investigation_id, user_id)
    if not inv:
        return None
    return _serialize_investigation(inv, graph=get_investigation_graph(investigation_id))


def update_investigation(db: Session, investigation_id: str, user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """Rename investigation."""
    inv = _get_owned_investigation(db, investigation_id, user_id)
    if not inv:
        return None
    inv.name = name
    db.commit()
    db.refresh(inv)
    return _serialize_investigation(inv)


def create_share_link(
    db: Session, investigation_id: str, user_id: int, expires_days: int = 7
) -> Optional[Dict[str, Any]]:
    """Create a share link for the investigation. Returns {share_url, share_token}."""
    inv = _get_owned_investigation(db, investigation_id, user_id)
    if not inv:
        return None
    token = str(uuid.uuid4())
    inv.share_token = token
    inv.share_expires_at = (
        datetime.utcnow() + timedelta(days=expires_days) if expires_days > 0 else None
    )
    db.commit()
    return {"share_token": token, "share_url": f"/investigations/shared/{token}"}


def get_investigation_by_share_token(db: Session, token: str) -> Optional[Dict[str, Any]]:
    """Resolve a share token to a read-only investigation payload."""
    inv = db.query(Investigation).filter(Investigation.share_token == token).first()
    if not inv:
        return None
    if inv.share_expires_at and inv.share_expires_at < datetime.utcnow():
        return None
    return _serialize_investigation(
        inv, graph=get_investigation_graph(str(inv.id)), read_only=True
    )


def delete_investigation(db: Session, investigation_id: str, user_id: int) -> bool:
    """Delete investigation in both PostgreSQL and Neo4j."""
    require_neo4j_for_investigation()
    inv = _get_owned_investigation(db, investigation_id, user_id)
    if not inv:
        return False
    delete_investigation_graph(investigation_id)
    db.delete(inv)
    db.commit()
    return True


def update_entity_metadata(
    db: Session,
    investigation_id: str,
    user_id: int,
    cy_id: str,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> bool:
    """Update notes and tags for an entity in the investigation graph."""
    if not _get_owned_investigation(db, investigation_id, user_id):
        return False
    meta: Dict[str, Any] = {}
    if notes is not None:
        meta["notes"] = notes
    if tags is not None:
        meta["tags"] = tags
    if not meta:
        return True
    return update_investigation_node_metadata(investigation_id, cy_id, meta)


def add_entity(
    db: Session,
    investigation_id: str,
    user_id: int,
    entity_type: str,
    entity_value: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Add entity to investigation graph."""
    require_neo4j_for_investigation()
    inv = _get_owned_investigation(db, investigation_id, user_id)
    if not inv:
        return None
    node_id = add_investigation_entity(investigation_id, entity_type, entity_value, metadata)
    if not node_id:
        return None
    # Auto-name investigation by the very first entity added.
    if inv.name.strip().lower() == "new investigation":
        graph = get_investigation_graph(investigation_id)
        if len(graph.get("nodes") or []) == 1:
            inv.name = entity_value
            db.commit()
    return {"id": node_id, "type": entity_type, "value": entity_value}


def run_enricher(
    db: Session,
    investigation_id: str,
    user_id: int,
    entity_type: str,
    entity_value: str,
    enricher_name: str,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run enricher on entity. Returns {success, new_nodes, new_edges, error}.
    Writes result to Neo4j.
    """
    require_neo4j_for_investigation()
    if not _get_owned_investigation(db, investigation_id, user_id):
        return {"success": False, "error": "Investigation not found"}

    def progress(stage: str, pct: int, msg: str):
        if on_progress:
            on_progress(stage, pct, msg)

    progress("start", 0, f"Running {enricher_name} on {entity_type}...")

    try:
        new_nodes, new_edges = _run_enricher_impl(
            investigation_id, entity_type, entity_value, enricher_name, progress
        )
        if not new_nodes and not new_edges:
            return {"success": True, "new_nodes": [], "new_edges": [], "message": "No new data"}

        ok = add_enricher_result_to_investigation(
            investigation_id,
            entity_type,
            entity_value,
            enricher_name,
            new_nodes,
            new_edges,
        )
        if not ok:
            return {"success": False, "error": "Failed to persist to Neo4j"}
        progress("done", 100, "Complete")
        return {"success": True, "new_nodes": new_nodes, "new_edges": new_edges}
    except Exception as exc:
        logger.warning("Enricher %s failed for %s/%s: %s",
                       enricher_name, entity_type, entity_value, exc)
        progress("error", 0, str(exc))
        return {"success": False, "error": str(exc)}


def _entity_to_cy_id(entity_type: str, entity_value: str) -> str:
    """Convert entity to Cytoscape node id."""
    if entity_type == "ip":
        return f"ip_{entity_value}"
    return f"{entity_type}_{entity_value}"


def _parent_fqdn_under_apex(sub: str, apex: str) -> str:
    """
    Return the immediate parent hostname of ``sub`` within the zone rooted at ``apex``.
    If ``sub`` is a direct child of ``apex``, ``apex`` itself is returned.
    e.g. accounts.smart-stage.ukma.edu.ua -> smart-stage.ukma.edu.ua (apex ukma.edu.ua).
    """
    sub_norm = sub.lower().strip().rstrip(".")
    apex_norm = apex.lower().strip().rstrip(".")
    if sub_norm == apex_norm or not sub_norm.endswith("." + apex_norm):
        return apex_norm
    rel = sub_norm[: -(len(apex_norm) + 1)]
    if not rel or "." not in rel:
        return apex_norm
    return sub_norm.split(".", 1)[1]


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert Pydantic model or mapping to a plain dict for safe ``.get()`` access."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {}


def _run_enricher_impl(
    investigation_id: str,
    entity_type: str,
    entity_value: str,
    enricher_name: str,
    progress: Callable[[str, int, str], None],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute enricher and return (new_nodes, new_edges)."""
    domain = entity_value if entity_type in ("domain", "subdomain") else None
    ip = entity_value if entity_type == "ip" else None

    if enricher_name == "dns" and domain:
        return _enricher_dns(domain, entity_type, entity_value, progress)
    if enricher_name == "whois" and domain:
        return _enricher_whois(investigation_id, domain, entity_type, entity_value, progress)
    if enricher_name == "subdomains" and domain:
        return _enricher_subdomains(domain, entity_type, entity_value, progress)
    if enricher_name == "ssl" and domain:
        return _enricher_ssl(domain, entity_type, entity_value, progress)
    if enricher_name == "port" and ip:
        return _enricher_port(ip, entity_type, entity_value, progress)
    if enricher_name == "tech" and domain:
        return _enricher_tech(domain, entity_type, entity_value, progress)
    if enricher_name == "geoip" and ip:
        return _enricher_geoip(investigation_id, ip, entity_type, entity_value, progress)
    if enricher_name == "reverse_dns" and ip:
        return _enricher_reverse_dns(ip, entity_type, entity_value, progress)
    if enricher_name == "root_domain" and domain:
        return _enricher_root_domain(domain, entity_type, entity_value, progress)
    if enricher_name == "ip_to_asn" and ip:
        return _enricher_ip_to_asn(ip, entity_type, entity_value, progress)

    if enricher_name.startswith("external_apis:") and (domain or ip):
        api_name = enricher_name.split(":", 1)[1]
        return _enricher_external_api_single(
            investigation_id, domain, ip, entity_type, entity_value, api_name, progress
        )

    return ([], [])


def _enricher_dns(domain: str, entity_type: str, entity_value: str, progress: Callable) -> Tuple[list, list]:
    from src.enrichers.dns import DnsEnricher

    enricher = DnsEnricher()
    ctx = enricher.enrich(domain, {})
    nodes: list = []
    edges: list = []
    source_id = _entity_to_cy_id(entity_type, entity_value)
    dns = _to_dict(ctx.get("dns_info"))
    for ip in (dns.get("a_records") or []) + (dns.get("aaaa_records") or []):
        nodes.append({"type": "ip", "value": ip})
        edges.append({"source": source_id, "target": f"ip_{ip}", "rel": "RESOLVES_TO"})
    for mx in dns.get("mx_records") or []:
        host = (mx.get("host") or mx.get("hostname") or "").rstrip(".")
        if host:
            nodes.append({"type": "mx", "value": host})
            edges.append({"source": source_id, "target": f"mx_{host}", "rel": "HAS_MX"})
    for ns in dns.get("ns_records") or []:
        ns_clean = str(ns).rstrip(".")
        if ns_clean:
            nodes.append({"type": "ns", "value": ns_clean})
            edges.append({"source": source_id, "target": f"ns_{ns_clean}", "rel": "HAS_NS"})
    progress("dns", 100, "DNS complete")
    return nodes, edges


def _enricher_whois(investigation_id: str, domain: str, entity_type: str, entity_value: str,
                    progress: Callable) -> Tuple[list, list]:
    from src.enrichers.whois import WhoisEnricher

    enricher = WhoisEnricher()
    ctx = enricher.enrich(domain, {})
    whois_data = ctx.get("whois_info")
    if not whois_data:
        return [], []
    meta = _to_dict(whois_data)
    meta.pop("domain", None)
    meta.pop("error", None)
    nodes: list = []
    edges: list = []
    source_id = _entity_to_cy_id(entity_type, entity_value)
    if meta:
        update_investigation_node_metadata(investigation_id, source_id, meta)
        for ns in meta.get("name_servers") or []:
            ns_clean = str(ns).strip().rstrip(".").lower()
            if ns_clean:
                nodes.append({"type": "ns", "value": ns_clean})
                edges.append({"source": source_id, "target": f"ns_{ns_clean}", "rel": "HAS_NS"})
    progress("whois", 100, "WHOIS complete")
    return nodes, edges


def _enricher_subdomains(domain: str, entity_type: str, entity_value: str,
                         progress: Callable) -> Tuple[list, list]:
    from src.enrichers.subdomain import SubdomainEnricher

    enricher = SubdomainEnricher(enable_bruteforce=False)
    ctx = enricher.enrich(domain, {})
    raw_subs = ctx.get("subdomains") or []
    suffix = f".{entity_value.lower()}"
    subs = [
        sub for sub in raw_subs
        if sub.lower() != entity_value.lower() and sub.lower().endswith(suffix)
    ]
    # When pivoting on a subdomain (e.g. coach.my-itspecialist.com), exclude sub-subdomains
    # whose direct child label matches a root-level subdomain (coach.coach, events.coach, mail.coach
    # are duplicates of root-level coach, events, mail).
    if entity_type == "subdomain":
        parts = entity_value.lower().split(".")
        root_domain = ".".join(parts[-2:]) if len(parts) >= 2 else entity_value
        if root_domain != entity_value:
            root_ctx = enricher.enrich(root_domain, {})
            root_subs = root_ctx.get("subdomains") or []
            root_first_labels: set = set()
            for root_sub in root_subs:
                if root_sub.lower().endswith(f".{root_domain}") and root_sub.lower() != root_domain:
                    remainder = root_sub[:-len(root_domain) - 1]
                    first_label = remainder.split(".")[-1] if "." in remainder else remainder
                    if first_label:
                        root_first_labels.add(first_label.lower())
            filtered = []
            for sub in subs:
                direct_child = sub[:-len(suffix)].rstrip(".")
                first_label = direct_child.split(".")[0] if direct_child else ""
                if first_label.lower() not in root_first_labels:
                    filtered.append(sub)
            subs = filtered
    nodes: list = []
    edges: list = []
    apex = domain.lower().strip().rstrip(".")
    root_source_id = _entity_to_cy_id(entity_type, entity_value)
    sub_by_lower: Dict[str, str] = {sub.lower(): sub for sub in subs}
    if entity_type == "subdomain":
        ev = entity_value.strip().rstrip(".")
        sub_by_lower[ev.lower()] = ev
    for sub in subs:
        nodes.append({"type": "subdomain", "value": sub})
        parent = _parent_fqdn_under_apex(sub, apex)
        parent_lower = parent.lower().strip().rstrip(".")
        if parent_lower == apex:
            source_id = root_source_id
        elif parent_lower in sub_by_lower:
            source_id = f"subdomain_{sub_by_lower[parent_lower]}"
        else:
            # Intermediate parent not in this discovery batch - anchor to investigation root.
            source_id = root_source_id
        edges.append({"source": source_id, "target": f"subdomain_{sub}", "rel": "HAS_SUBDOMAIN"})
    progress("subdomains", 100, f"Found {len(subs)} subdomains")
    return nodes, edges


def _enricher_ssl(domain: str, entity_type: str, entity_value: str, progress: Callable) -> Tuple[list, list]:
    from src.enrichers.ssl import SslEnricher

    enricher = SslEnricher()
    ctx = enricher.enrich(domain, {})
    ssl = _to_dict(ctx.get("ssl_info"))
    certs = ssl.get("certificates") or []
    nodes: list = []
    edges: list = []
    source_id = _entity_to_cy_id(entity_type, entity_value)
    for cert in certs:
        cert_dict = cert if isinstance(cert, dict) else _to_dict(cert)
        host = cert_dict.get("host", "")
        if host:
            nodes.append({
                "type": "certificate",
                "value": host,
                "metadata": {"issuer": cert_dict.get("issuer"), "is_expired": cert_dict.get("is_expired")},
            })
            edges.append({"source": source_id, "target": f"cert_{host}", "rel": "HAS_CERTIFICATE"})
    progress("ssl", 100, "SSL complete")
    return nodes, edges


def _enricher_port(ip: str, entity_type: str, entity_value: str, progress: Callable) -> Tuple[list, list]:
    from src.enrichers.port import PortEnricher

    enricher = PortEnricher()
    ctx = enricher.enrich("", {"dns_info": {"a_records": [ip], "aaaa_records": []}})
    port_scan_raw = ctx.get("port_scan") or []
    nodes: list = []
    edges: list = []
    source_id = f"ip_{ip}"
    for scan_item in port_scan_raw:
        scan = _to_dict(scan_item)
        scan_ip = scan.get("ip", ip)
        for open_port_item in scan.get("open_ports") or []:
            open_port = _to_dict(open_port_item)
            port = open_port.get("port", 0)
            if port:
                nodes.append({
                    "type": "port",
                    "value": str(port),
                    "metadata": {"ip": scan_ip, "port": port, "service": open_port.get("service", "tcp")},
                })
                edges.append({
                    "source": source_id,
                    "target": f"port_{scan_ip}_{port}",
                    "rel": "HAS_PORT",
                })
    progress("port", 100, "Port scan complete")
    return nodes, edges


def _enricher_tech(domain: str, entity_type: str, entity_value: str, progress: Callable) -> Tuple[list, list]:
    from src.enrichers.tech import TechEnricher

    enricher = TechEnricher()
    ctx = enricher.enrich(domain, {"subdomains": [domain]})
    tech_stack = ctx.get("tech_stack") or {}
    nodes: list = []
    edges: list = []
    source_id = _entity_to_cy_id(entity_type, entity_value)
    seen: set = set()
    if not isinstance(tech_stack, dict):
        tech_stack = {}
    for _scanned_url, raw_data in tech_stack.items():
        details = _to_dict(raw_data) if raw_data else {}
        for tech_item in details.get("technologies") or []:
            if isinstance(tech_item, str):
                name = tech_item
            else:
                name = tech_item.get("name") or tech_item.get("value") or "unknown"
            if name and name not in seen:
                seen.add(name)
                safe_name = str(name).replace(" ", "_")[:80]
                nodes.append({
                    "type": "technology",
                    "value": name,
                    "metadata": {"source": details.get("url")},
                })
                edges.append({
                    "source": source_id,
                    "target": f"technology_{safe_name}",
                    "rel": "HAS_TECHNOLOGY",
                })
    progress("tech", 100, "Tech detection complete")
    return nodes, edges


def _enricher_geoip(investigation_id: str, ip: str, entity_type: str, entity_value: str,
                    progress: Callable) -> Tuple[list, list]:
    from src.enrichers.geoip import GeoipEnricher

    enricher = GeoipEnricher()
    ctx = enricher.enrich("", {"dns_info": {"a_records": [ip]}})
    geo = ctx.get("geoip_info") or {}
    ip_geo = geo.get(ip) if isinstance(geo, dict) else None
    if not ip_geo:
        return [], []
    meta = {
        "country": ip_geo.get("country"),
        "country_code": ip_geo.get("country_code"),
        "city": ip_geo.get("city"),
        "latitude": ip_geo.get("latitude"),
        "longitude": ip_geo.get("longitude"),
    }
    update_investigation_node_metadata(investigation_id, f"ip_{ip}", meta)
    progress("geoip", 100, "GeoIP complete")
    return [], []


def _enricher_reverse_dns(ip: str, entity_type: str, entity_value: str,
                          progress: Callable) -> Tuple[list, list]:
    from src.enrichers.reverse_dns import ReverseDnsEnricher

    enricher = ReverseDnsEnricher()
    return enricher.enrich_for_investigation(ip, progress)


def _enricher_root_domain(domain: str, entity_type: str, entity_value: str,
                          progress: Callable) -> Tuple[list, list]:
    from src.enrichers.root_domain import RootDomainEnricher

    enricher = RootDomainEnricher()
    return enricher.enrich_for_investigation(domain, progress)


def _enricher_external_api_single(
    investigation_id: str,
    domain: Optional[str],
    ip: Optional[str],
    entity_type: str,
    entity_value: str,
    api_name: str,
    progress: Callable,
) -> Tuple[list, list]:
    """Fetch a single external API and store its result as node metadata."""
    from src.enrichers.external_apis import fetch_single_external_api

    progress("external_api", 0, f"Fetching {api_name}...")
    result = fetch_single_external_api(api_name, domain, ip)
    progress("external_api", 50, f"Storing {api_name} result...")
    if result is None:
        progress("external_api", 100, f"No data from {api_name}")
        return [], []

    source_id = _entity_to_cy_id(entity_type, entity_value)
    meta_key = f"external_apis_{api_name}"
    ok = update_investigation_node_metadata(investigation_id, source_id, {meta_key: result})
    progress("external_api", 100, f"{api_name} complete" if ok else f"{api_name} failed")
    return [], []


def _enricher_ip_to_asn(ip: str, entity_type: str, entity_value: str,
                        progress: Callable) -> Tuple[list, list]:
    from src.enrichers.ip_to_asn import IpToAsnEnricher

    enricher = IpToAsnEnricher()
    return enricher.enrich_for_investigation(ip, progress)
