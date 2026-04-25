"""
Investigation service — CRUD for investigations, run enrichers on entities.
Orchestrates PostgreSQL (metadata) and Neo4j (graph).
"""

import sys
import os
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from sqlalchemy.orm import Session

from app.db.models import Investigation
from app.services.neo4j_service import (
    add_investigation_entity,
    add_enricher_result_to_investigation,
    get_investigation_graph,
    delete_investigation_graph,
    update_investigation_node_metadata,
    _require_neo4j,
    is_neo4j_available,
)


def require_neo4j_for_investigation():
    """Raise HTTP 503 if Neo4j is not available."""
    if not is_neo4j_available():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Neo4j is required for Investigation mode. Set NEO4J_PASSWORD and ensure Neo4j is running (docker compose up -d)",
        )


def list_investigations(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """List investigations for a user."""
    rows = db.query(Investigation).filter(Investigation.user_id == user_id).order_by(Investigation.updated_at.desc()).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


def create_investigation(db: Session, user_id: int, name: str = "New Investigation") -> Dict[str, Any]:
    """Create a new investigation."""
    require_neo4j_for_investigation()
    inv = Investigation(user_id=user_id, name=name)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return {
        "id": str(inv.id),
        "name": inv.name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def get_investigation(db: Session, investigation_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Get investigation metadata and graph from Neo4j."""
    require_neo4j_for_investigation()
    try:
        uid = UUID(investigation_id)
    except ValueError:
        return None
    inv = db.query(Investigation).filter(Investigation.id == uid, Investigation.user_id == user_id).first()
    if not inv:
        return None
    graph = get_investigation_graph(investigation_id)
    return {
        "id": str(inv.id),
        "name": inv.name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "graph": graph,
    }


def update_investigation(db: Session, investigation_id: str, user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """Update investigation name."""
    try:
        uid = UUID(investigation_id)
    except ValueError:
        return None
    inv = db.query(Investigation).filter(Investigation.id == uid, Investigation.user_id == user_id).first()
    if not inv:
        return None
    inv.name = name
    db.commit()
    db.refresh(inv)
    return {
        "id": str(inv.id),
        "name": inv.name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def create_share_link(
    db: Session, investigation_id: str, user_id: int, expires_days: int = 7
) -> Optional[Dict[str, Any]]:
    """Create a share link for the investigation. Returns {share_url, share_token}."""
    if not _user_owns_investigation(db, investigation_id, user_id):
        return None
    import uuid
    from datetime import datetime, timedelta

    try:
        uid = UUID(investigation_id)
    except ValueError:
        return None
    inv = db.query(Investigation).filter(Investigation.id == uid, Investigation.user_id == user_id).first()
    if not inv:
        return None
    token = str(uuid.uuid4())
    inv.share_token = token
    inv.share_expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days > 0 else None
    db.commit()
    return {"share_token": token, "share_url": f"/investigations/shared/{token}"}


def get_investigation_by_share_token(db: Session, token: str) -> Optional[Dict[str, Any]]:
    """Get investigation by share token (read-only, no auth). Returns None if invalid or expired."""
    from datetime import datetime

    inv = db.query(Investigation).filter(Investigation.share_token == token).first()
    if not inv:
        return None
    if inv.share_expires_at and inv.share_expires_at < datetime.utcnow():
        return None
    graph = get_investigation_graph(str(inv.id))
    return {
        "id": str(inv.id),
        "name": inv.name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "graph": graph,
        "read_only": True,
    }


def delete_investigation(db: Session, investigation_id: str, user_id: int) -> bool:
    """Delete investigation (PostgreSQL + Neo4j)."""
    require_neo4j_for_investigation()
    try:
        uid = UUID(investigation_id)
    except ValueError:
        return False
    inv = db.query(Investigation).filter(Investigation.id == uid, Investigation.user_id == user_id).first()
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
    if not _user_owns_investigation(db, investigation_id, user_id):
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
    try:
        uid = UUID(investigation_id)
    except ValueError:
        return None
    inv = db.query(Investigation).filter(Investigation.id == uid, Investigation.user_id == user_id).first()
    if not inv:
        return None
    node_id = add_investigation_entity(investigation_id, entity_type, entity_value, metadata)
    if not node_id:
        return None
    # If this is the very first entity, auto-name investigation by entity value.
    if inv.name.strip().lower() == "new investigation":
        graph = get_investigation_graph(investigation_id)
        if len(graph.get("nodes") or []) == 1:
            inv.name = entity_value
            db.commit()
    return {"id": node_id, "type": entity_type, "value": entity_value}


def _user_owns_investigation(db: Session, investigation_id: str, user_id: int) -> bool:
    try:
        uid = UUID(investigation_id)
    except ValueError:
        return False
    inv = db.query(Investigation).filter(Investigation.id == uid, Investigation.user_id == user_id).first()
    return inv is not None


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
    if not _user_owns_investigation(db, investigation_id, user_id):
        return {"success": False, "error": "Investigation not found"}

    def progress(stage: str, pct: int, msg: str):
        if on_progress:
            on_progress(stage, pct, msg)

    progress("start", 0, f"Running {enricher_name} on {entity_type}...")

    try:
        new_nodes, new_edges = _run_enricher_impl(investigation_id, entity_type, entity_value, enricher_name, progress)
        if not new_nodes and not new_edges:
            return {"success": True, "new_nodes": [], "new_edges": [], "message": "No new data"}

        source_id = _entity_to_cy_id(entity_type, entity_value)
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
    except Exception as e:
        progress("error", 0, str(e))
        return {"success": False, "error": str(e)}


def _entity_to_cy_id(entity_type: str, entity_value: str) -> str:
    """Convert entity to Cytoscape node id."""
    if entity_type in ("domain", "subdomain"):
        return f"{entity_type}_{entity_value}"
    if entity_type == "ip":
        return f"ip_{entity_value}"
    return f"{entity_type}_{entity_value}"


def _parent_fqdn_under_apex(sub: str, apex: str) -> str:
    """
    Immediate parent hostname of sub within zone rooted at apex.
    If sub is a direct child of apex, returns apex.
    e.g. accounts.smart-stage.ukma.edu.ua -> smart-stage.ukma.edu.ua (apex ukma.edu.ua).
    """
    s = sub.lower().strip().rstrip(".")
    a = apex.lower().strip().rstrip(".")
    if s == a or not s.endswith("." + a):
        return a
    rel = s[: -(len(a) + 1)]
    if not rel or "." not in rel:
        return a
    return s.split(".", 1)[1]


def _to_dict(obj: Any) -> Any:
    """Convert Pydantic model to dict for safe .get() access."""
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
) -> tuple:
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


def _enricher_dns(domain: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.dns import DnsEnricher
    e = DnsEnricher()
    ctx = e.enrich(domain, {})
    nodes, edges = [], []
    src = _entity_to_cy_id(entity_type, entity_value)
    dns = _to_dict(ctx.get("dns_info"))
    for ip in (dns.get("a_records") or []) + (dns.get("aaaa_records") or []):
        nodes.append({"type": "ip", "value": ip})
        edges.append({"source": src, "target": f"ip_{ip}", "rel": "RESOLVES_TO"})
    for mx in dns.get("mx_records") or []:
        host = (mx.get("host") or mx.get("hostname") or "").rstrip(".")
        if host:
            nodes.append({"type": "mx", "value": host})
            edges.append({"source": src, "target": f"mx_{host}", "rel": "HAS_MX"})
    for ns in dns.get("ns_records") or []:
        ns_clean = str(ns).rstrip(".")
        if ns_clean:
            nodes.append({"type": "ns", "value": ns_clean})
            edges.append({"source": src, "target": f"ns_{ns_clean}", "rel": "HAS_NS"})
    progress("dns", 100, "DNS complete")
    return (nodes, edges)


def _enricher_whois(investigation_id: str, domain: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.whois import WhoisEnricher
    from app.services.neo4j_service import update_investigation_node_metadata
    e = WhoisEnricher()
    ctx = e.enrich(domain, {})
    whois_data = ctx.get("whois_info")
    if not whois_data:
        return ([], [])
    meta = _to_dict(whois_data)
    meta.pop("domain", None)
    meta.pop("error", None)
    nodes = []
    edges = []
    src = _entity_to_cy_id(entity_type, entity_value)
    if meta:
        update_investigation_node_metadata(investigation_id, src, meta)
        for ns in meta.get("name_servers") or []:
            ns_clean = str(ns).strip().rstrip(".").lower()
            if ns_clean:
                nodes.append({"type": "ns", "value": ns_clean})
                edges.append({"source": src, "target": f"ns_{ns_clean}", "rel": "HAS_NS"})
    progress("whois", 100, "WHOIS complete")
    return (nodes, edges)


def _enricher_subdomains(domain: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.subdomain import SubdomainEnricher
    e = SubdomainEnricher(enable_bruteforce=False)
    ctx = e.enrich(domain, {})
    raw_subs = ctx.get("subdomains") or []
    suffix = f".{entity_value.lower()}"
    subs = [
        s for s in raw_subs
        if s.lower() != entity_value.lower() and s.lower().endswith(suffix)
    ]
    # When pivoting on a subdomain (e.g. coach.my-itspecialist.com), exclude sub-subdomains
    # whose direct child label matches a root-level subdomain (coach.coach, events.coach, mail.coach
    # are "duplicates" of root-level coach, events, mail).
    if entity_type == "subdomain":
        parts = entity_value.lower().split(".")
        root_domain = ".".join(parts[-2:]) if len(parts) >= 2 else entity_value
        if root_domain != entity_value:
            root_ctx = e.enrich(root_domain, {})
            root_subs = root_ctx.get("subdomains") or []
            root_first_labels: set = set()
            for rs in root_subs:
                if rs.lower().endswith(f".{root_domain}") and rs.lower() != root_domain:
                    rem = rs[:-len(root_domain) - 1]
                    first_label = rem.split(".")[-1] if "." in rem else rem
                    if first_label:
                        root_first_labels.add(first_label.lower())
            before_count = len(subs)
            filtered = []
            for s in subs:
                direct_child = s[:-len(suffix)].rstrip(".")
                first_label = direct_child.split(".")[0] if direct_child else ""
                if first_label.lower() not in root_first_labels:
                    filtered.append(s)
            subs = filtered
    nodes = []
    edges = []
    apex = domain.lower().strip().rstrip(".")
    root_src = _entity_to_cy_id(entity_type, entity_value)
    sub_by_lower: Dict[str, str] = {s.lower(): s for s in subs}
    if entity_type == "subdomain":
        ev = entity_value.strip().rstrip(".")
        sub_by_lower[ev.lower()] = ev
    for sub in subs:
        nodes.append({"type": "subdomain", "value": sub})
        parent = _parent_fqdn_under_apex(sub, apex)
        pl = parent.lower().strip().rstrip(".")
        if pl == apex:
            src = root_src
        elif pl in sub_by_lower:
            src = f"subdomain_{sub_by_lower[pl]}"
        else:
            # Intermediate parent not in this discovery batch — anchor to investigation root
            src = root_src
        edges.append({"source": src, "target": f"subdomain_{sub}", "rel": "HAS_SUBDOMAIN"})
    progress("subdomains", 100, f"Found {len(subs)} subdomains")
    return (nodes, edges)


def _enricher_ssl(domain: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.ssl import SslEnricher
    e = SslEnricher()
    ctx = e.enrich(domain, {})
    ssl = _to_dict(ctx.get("ssl_info"))
    certs = ssl.get("certificates") or []
    nodes = []
    edges = []
    src = _entity_to_cy_id(entity_type, entity_value)
    for cert in certs:
        c = _to_dict(cert) if not isinstance(cert, dict) else cert
        host = c.get("host", "")
        if host:
            nodes.append({"type": "certificate", "value": host, "metadata": {"issuer": c.get("issuer"), "is_expired": c.get("is_expired")}})
            edges.append({"source": src, "target": f"cert_{host}", "rel": "HAS_CERTIFICATE"})
    progress("ssl", 100, "SSL complete")
    return (nodes, edges)


def _enricher_port(ip: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.port import PortEnricher
    e = PortEnricher()
    ctx = e.enrich("", {"dns_info": {"a_records": [ip], "aaaa_records": []}})
    port_scan_raw = ctx.get("port_scan") or []
    nodes = []
    edges = []
    src = f"ip_{ip}"
    for ps_item in port_scan_raw:
        ps = _to_dict(ps_item)
        pip = ps.get("ip", ip)
        for op_item in ps.get("open_ports") or []:
            op = _to_dict(op_item)
            port = op.get("port", 0)
            if port:
                nodes.append({"type": "port", "value": str(port), "metadata": {"ip": pip, "port": port, "service": op.get("service", "tcp")}})
                edges.append({"source": src, "target": f"port_{pip}_{port}", "rel": "HAS_PORT"})
    progress("port", 100, "Port scan complete")
    return (nodes, edges)


def _enricher_tech(domain: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.tech import TechEnricher
    e = TechEnricher()
    ctx = e.enrich(domain, {"subdomains": [domain]})
    tech_stack = ctx.get("tech_stack") or {}
    nodes = []
    edges = []
    src = _entity_to_cy_id(entity_type, entity_value)
    seen = set()
    for _url, data in (tech_stack if isinstance(tech_stack, dict) else {}).items():
        d = _to_dict(data) if data else {}
        tech_list = d.get("technologies") or []
        for t in tech_list:
            name = t if isinstance(t, str) else (t.get("name") or t.get("value") or "unknown")
            if name and name not in seen:
                seen.add(name)
                safe_name = str(name).replace(" ", "_")[:80]
                nodes.append({"type": "technology", "value": name, "metadata": {"source": d.get("url")}})
                edges.append({"source": src, "target": f"technology_{safe_name}", "rel": "HAS_TECHNOLOGY"})
    progress("tech", 100, "Tech detection complete")
    return (nodes, edges)


def _enricher_geoip(investigation_id: str, ip: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    from src.enrichers.geoip import GeoipEnricher
    from app.services.neo4j_service import update_investigation_node_metadata
    e = GeoipEnricher()
    ctx = e.enrich("", {"dns_info": {"a_records": [ip]}})
    geo = ctx.get("geoip_info") or {}
    ip_geo = geo.get(ip) if isinstance(geo, dict) else None
    if not ip_geo:
        return ([], [])
    meta = {
        "country": ip_geo.get("country"),
        "country_code": ip_geo.get("country_code"),
        "city": ip_geo.get("city"),
        "latitude": ip_geo.get("latitude"),
        "longitude": ip_geo.get("longitude"),
    }
    update_investigation_node_metadata(investigation_id, f"ip_{ip}", meta)
    progress("geoip", 100, "GeoIP complete")
    return ([], [])


def _enricher_reverse_dns(ip: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    try:
        from src.enrichers.reverse_dns import ReverseDnsEnricher
        e = ReverseDnsEnricher()
        nodes, edges = e.enrich_for_investigation(ip, progress)
        return (nodes, edges)
    except ImportError:
        # Fallback: PTR via dnspython
        import dns.resolver
        nodes = []
        edges = []
        src = f"ip_{ip}"
        try:
            ptr_name = ".".join(reversed(ip.split("."))) + ".in-addr.arpa."
            answers = dns.resolver.resolve(ptr_name, "PTR")
            for r in answers:
                name = str(r).rstrip(".") if r else ""
                if name:
                    nodes.append({"type": "domain", "value": name})
                    edges.append({"source": src, "target": f"domain_{name}", "rel": "POINTS_TO"})
        except Exception:
            pass
        progress("reverse_dns", 100, "Reverse DNS complete")
        return (nodes, edges)


def _enricher_root_domain(domain: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    try:
        from src.enrichers.root_domain import RootDomainEnricher
        e = RootDomainEnricher()
        return e.enrich_for_investigation(domain, progress)
    except ImportError:
        # Simple fallback: extract root (last two parts)
        parts = domain.lower().split(".")
        if len(parts) >= 2:
            root = ".".join(parts[-2:])
        else:
            root = domain
        nodes = [{"type": "domain", "value": root}]
        src = _entity_to_cy_id(entity_type, entity_value)
        edges = [{"source": src, "target": f"domain_{root}", "rel": "ROOT_OF"}]
        progress("root_domain", 100, "Root domain complete")
        return (nodes, edges)


def _enricher_external_api_single(
    investigation_id: str,
    domain: Optional[str],
    ip: Optional[str],
    entity_type: str,
    entity_value: str,
    api_name: str,
    progress: Callable,
) -> tuple:
    """Fetch a single external API and store result as node metadata."""
    from src.enrichers.external_apis import fetch_single_external_api

    progress("external_api", 0, f"Fetching {api_name}...")
    result = fetch_single_external_api(api_name, domain, ip)
    progress("external_api", 50, f"Storing {api_name} result...")
    if result is None:
        progress("external_api", 100, f"No data from {api_name}")
        return ([], [])

    src = _entity_to_cy_id(entity_type, entity_value)
    meta_key = f"external_apis_{api_name}"
    ok = update_investigation_node_metadata(investigation_id, src, {meta_key: result})
    progress("external_api", 100, f"{api_name} complete" if ok else f"{api_name} failed")
    return ([], [])


def _enricher_ip_to_asn(ip: str, entity_type: str, entity_value: str, progress: Callable) -> tuple:
    try:
        from src.enrichers.ip_to_asn import IpToAsnEnricher
        e = IpToAsnEnricher()
        nodes, edges = e.enrich_for_investigation(ip, progress)
        return (nodes, edges)
    except ImportError:
        from src.enrichers.external_apis import ExternalApiEnricher
        e = ExternalApiEnricher()
        ctx = e.enrich("", {"dns_info": {"a_records": [ip]}})
        ext = ctx.get("external_apis") or {}
        bgp = ext.get("bgpview") or {}
        ips_data = bgp.get("ips") or {}
        ip_data = ips_data.get(ip) or {}
        asn_num = ip_data.get("asn")
        nodes = []
        edges = []
        src = f"ip_{ip}"
        if asn_num:
            nodes.append({"type": "asn", "value": str(asn_num), "metadata": {"org": ip_data.get("asn_name")}})
            edges.append({"source": src, "target": f"asn_{asn_num}", "rel": "BELONGS_TO_ASN"})
        progress("ip_to_asn", 100, "IP to ASN complete")
        return (nodes, edges)
