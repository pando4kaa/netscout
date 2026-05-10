"""
Neo4j graph service - persists scan results and investigation graphs.

The Neo4j driver is a heavyweight object (it owns a connection pool and
performs auth + protocol handshake) and is intended to live for the lifetime
of the application. We expose it via :func:`_get_driver` as a process-wide
singleton; :func:`close_driver` should be called on application shutdown
(e.g. from a FastAPI ``lifespan`` handler).
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from src.config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

_driver: Optional[Any] = None
_driver_init_failed: bool = False
_driver_lock = threading.Lock()


def _require_neo4j() -> None:
    """Raise if Neo4j is not available. Investigation mode requires Neo4j."""
    if not NEO4J_PASSWORD:
        raise RuntimeError("Neo4j is required for Investigation mode. Set NEO4J_PASSWORD in .env")
    if not is_neo4j_available():
        raise RuntimeError("Neo4j is unreachable. Is it running? (docker compose up -d)")


def _get_driver():
    """
    Return the process-wide Neo4j driver, creating it on first use.

    Returns ``None`` (and caches the failure) when the ``neo4j`` package is
    missing, ``NEO4J_PASSWORD`` is empty, or driver construction raises.
    Construction is guarded by a lock so concurrent requests share one driver.
    """
    global _driver, _driver_init_failed
    if _driver is not None:
        return _driver
    if _driver_init_failed or not NEO4J_PASSWORD:
        return None

    with _driver_lock:
        if _driver is not None:
            return _driver
        if _driver_init_failed:
            return None
        try:
            from neo4j import GraphDatabase

            _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            return _driver
        except ImportError as exc:
            logger.warning("neo4j package is not installed: %s", exc)
            _driver_init_failed = True
            return None
        except Exception as exc:
            logger.warning("Failed to create Neo4j driver for %s: %s", NEO4J_URI, exc)
            _driver_init_failed = True
            return None


def close_driver() -> None:
    """Close the cached Neo4j driver. Safe to call multiple times."""
    global _driver, _driver_init_failed
    with _driver_lock:
        if _driver is not None:
            try:
                _driver.close()
            except Exception as exc:
                logger.debug("Neo4j driver close raised: %s", exc)
            _driver = None
        _driver_init_failed = False


def is_neo4j_available() -> bool:
    """Return ``True`` if Neo4j is configured and reachable."""
    if not NEO4J_PASSWORD:
        return False
    driver = _get_driver()
    if not driver:
        return False
    try:
        driver.verify_connectivity()
        return True
    except Exception as exc:
        logger.debug("Neo4j connectivity check failed: %s", exc)
        return False


def persist_scan_to_neo4j(scan_id: str, domain: str, results: Dict[str, Any]) -> bool:
    """
    Persist scan results to Neo4j as a graph.
    Creates nodes: Domain, Subdomain, IP, MX, NS, Certificate, Port.
    Creates relationships: RESOLVES_TO, HAS_SUBDOMAIN, HAS_MX, HAS_NS, HAS_CERT, HAS_PORT.
    """
    if not NEO4J_PASSWORD:
        return False

    try:
        driver = _get_driver()
        if not driver:
            return False

        with driver.session() as session:
            session.run(
                """
                MERGE (d:Domain {name: $domain})
                SET d.scan_id = $scan_id, d.last_scan = datetime()
                """,
                domain=domain,
                scan_id=scan_id,
            )

            dns = results.get("dns_info") or {}
            a_records = dns.get("a_records") or []
            aaaa_records = dns.get("aaaa_records") or []

            for ip in a_records + aaaa_records:
                session.run(
                    """
                    MERGE (ip:IP {address: $ip})
                    WITH ip
                    MATCH (d:Domain {name: $domain})
                    MERGE (d)-[:RESOLVES_TO]->(ip)
                    """,
                    ip=ip,
                    domain=domain,
                )

            for mx in dns.get("mx_records") or []:
                host = (mx.get("host") or mx.get("hostname") or "").rstrip(".")
                if host:
                    session.run(
                        """
                        MERGE (mx:MX {host: $host})
                        WITH mx
                        MATCH (d:Domain {name: $domain})
                        MERGE (d)-[:HAS_MX {priority: $priority}]->(mx)
                        """,
                        host=host,
                        domain=domain,
                        priority=mx.get("priority", 0),
                    )

            for ns in dns.get("ns_records") or []:
                ns_clean = str(ns).rstrip(".")
                if ns_clean:
                    session.run(
                        """
                        MERGE (n:NS {host: $host})
                        WITH n
                        MATCH (d:Domain {name: $domain})
                        MERGE (d)-[:HAS_NS]->(n)
                        """,
                        host=ns_clean,
                        domain=domain,
                    )

            for sub in results.get("subdomains") or []:
                session.run(
                    """
                    MERGE (s:Subdomain {name: $sub})
                    WITH s
                    MATCH (d:Domain {name: $domain})
                    MERGE (d)-[:HAS_SUBDOMAIN]->(s)
                    """,
                    sub=sub,
                    domain=domain,
                )

            for cert in (results.get("ssl_info") or {}).get("certificates") or []:
                host = cert.get("host", "")
                if host:
                    session.run(
                        """
                        MERGE (c:Certificate {host: $host})
                        SET c.issuer = $issuer, c.is_expired = $expired
                        WITH c
                        MATCH (d:Domain {name: $domain})
                        MERGE (d)-[:HAS_CERTIFICATE]->(c)
                        """,
                        host=host,
                        issuer=cert.get("issuer", ""),
                        expired=cert.get("is_expired", False),
                        domain=domain,
                    )

            for port_scan in results.get("port_scan") or []:
                ip = port_scan.get("ip", "")
                for open_port in port_scan.get("open_ports") or []:
                    port = open_port.get("port", 0)
                    if ip and port:
                        session.run(
                            """
                            MERGE (p:Port {ip: $ip, port: $port})
                            SET p.service = $service
                            WITH p
                            MATCH (ip:IP {address: $ip})
                            MERGE (ip)-[:HAS_PORT]->(p)
                            """,
                            ip=ip,
                            port=port,
                            service=open_port.get("service", "tcp"),
                        )
        return True
    except Exception as exc:
        logger.warning("Failed to persist scan %s for %s to Neo4j: %s", scan_id, domain, exc)
        return False


# --- Investigation graph methods ---

def add_investigation_entity(
    investigation_id: str,
    entity_type: str,
    entity_value: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Add a single entity (node) to an investigation graph in Neo4j.
    Returns node id or None on error.
    """
    _require_neo4j()
    inv_id = str(investigation_id)
    meta = metadata or {}

    label_map = {
        "domain": "Domain",
        "subdomain": "Subdomain",
        "ip": "IP",
        "mx": "MX",
        "ns": "NS",
        "certificate": "Certificate",
        "port": "Port",
        "technology": "Technology",
        "asn": "ASN",
    }
    label = label_map.get(entity_type, "Entity")

    if entity_type in ("domain", "subdomain"):
        node_id = f"{entity_type}_{entity_value}"
        props = {"name": entity_value, "investigation_id": inv_id}
    elif entity_type == "mx":
        node_id = f"mx_{entity_value}"
        props = {"host": entity_value, "investigation_id": inv_id}
    elif entity_type == "ns":
        node_id = f"ns_{entity_value}"
        props = {"host": entity_value, "investigation_id": inv_id}
    elif entity_type == "ip":
        node_id = f"ip_{entity_value}"
        props = {"address": entity_value, "investigation_id": inv_id}
    elif entity_type == "port":
        ip = meta.get("ip", "")
        port = meta.get("port", 0)
        node_id = f"port_{ip}_{port}"
        props = {"ip": ip, "port": port, "investigation_id": inv_id, **meta}
    elif entity_type == "asn":
        node_id = f"asn_{entity_value}"
        props = {"number": entity_value, "investigation_id": inv_id, **meta}
    elif entity_type == "certificate":
        node_id = f"cert_{entity_value}"
        props = {"host": entity_value, "investigation_id": inv_id, **meta}
    elif entity_type == "technology":
        node_id = f"technology_{entity_value}".replace(" ", "_")
        props = {"name": entity_value, "investigation_id": inv_id, **meta}
    else:
        node_id = f"{entity_type}_{entity_value}".replace(".", "_")
        props = {"value": entity_value, "investigation_id": inv_id, **meta}

    try:
        driver = _get_driver()
        if not driver:
            return None
        with driver.session() as session:
            if entity_type in ("domain", "subdomain"):
                session.run(
                    f"""
                    MERGE (n:{label} {{name: $name, investigation_id: $inv_id}})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    """,
                    name=entity_value,
                    inv_id=inv_id,
                )
            elif entity_type in ("mx", "ns"):
                session.run(
                    f"""
                    MERGE (n:{label} {{host: $host, investigation_id: $inv_id}})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    """,
                    host=entity_value,
                    inv_id=inv_id,
                )
            elif entity_type == "certificate":
                session.run(
                    """
                    MERGE (n:Certificate {host: $host, investigation_id: $inv_id})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    """,
                    host=entity_value,
                    inv_id=inv_id,
                )
            elif entity_type == "technology":
                session.run(
                    f"""
                    MERGE (n:Technology {{name: $name, investigation_id: $inv_id}})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    """,
                    name=entity_value,
                    inv_id=inv_id,
                )
            elif entity_type == "ip":
                session.run(
                    f"""
                    MERGE (n:{label} {{address: $address, investigation_id: $inv_id}})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    """,
                    address=entity_value,
                    inv_id=inv_id,
                )
            elif entity_type == "port":
                session.run(
                    """
                    MERGE (n:Port {ip: $ip, port: $port, investigation_id: $inv_id})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    SET n.service = $service
                    """,
                    ip=meta.get("ip", ""),
                    port=meta.get("port", 0),
                    service=meta.get("service", "tcp"),
                    inv_id=inv_id,
                )
            elif entity_type == "asn":
                session.run(
                    """
                    MERGE (n:ASN {number: $number, investigation_id: $inv_id})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    SET n.org = $org
                    """,
                    number=entity_value,
                    org=meta.get("org", ""),
                    inv_id=inv_id,
                )
            else:
                session.run(
                    f"""
                    MERGE (n:{label} {{value: $value}})
                    ON CREATE SET n.investigation_id = $inv_id
                    ON MATCH SET n.investigation_id = $inv_id
                    """,
                    value=entity_value,
                    inv_id=inv_id,
                )
        return node_id
    except Exception as exc:
        logger.warning("Failed to add %s entity %s to investigation %s: %s",
                       entity_type, entity_value, inv_id, exc)
        return None


def get_investigation_graph(investigation_id: str) -> Dict[str, Any]:
    """
    Get full graph for an investigation from Neo4j.
    Returns {nodes: [...], edges: [...]} for Cytoscape/frontend.
    """
    _require_neo4j()
    inv_id = str(investigation_id)

    try:
        driver = _get_driver()
        if not driver:
            return {"nodes": [], "edges": []}
        with driver.session() as session:
            node_result = session.run(
                "MATCH (n) WHERE n.investigation_id = $inv_id RETURN n",
                inv_id=inv_id,
            )
            nodes = []
            seen_ids = set()
            for record in node_result:
                node = record.get("n")
                if node:
                    node_id = getattr(node, "element_id", None) or str(id(node))
                    if node_id not in seen_ids:
                        seen_ids.add(node_id)
                        node_dict = _node_to_dict(node, inv_id)
                        if node_dict:
                            nodes.append(node_dict)

            rel_result = session.run(
                """
                MATCH (a)-[r]->(b)
                WHERE a.investigation_id = $inv_id AND b.investigation_id = $inv_id
                RETURN a, r, b
                """,
                inv_id=inv_id,
            )
            edges = []
            edges_seen = set()
            for record in rel_result:
                source_node = record.get("a")
                relation = record.get("r")
                target_node = record.get("b")
                if relation is None or source_node is None or target_node is None:
                    continue
                src_cy = _node_to_cy_id(source_node)
                tgt_cy = _node_to_cy_id(target_node)
                if src_cy and tgt_cy:
                    edge_id = f"{src_cy}_{tgt_cy}_{relation.type}"
                    if edge_id not in edges_seen:
                        edges_seen.add(edge_id)
                        edges.append({
                            "data": {
                                "id": edge_id,
                                "source": src_cy,
                                "target": tgt_cy,
                                "edgeType": relation.type,
                            },
                        })

        return {"nodes": nodes, "edges": edges}
    except Exception as exc:
        logger.warning("Failed to load investigation graph %s: %s", inv_id, exc)
        return {"nodes": [], "edges": []}


def _node_to_cy_id(node) -> Optional[str]:
    """Convert Neo4j node to Cytoscape node id."""
    if not node:
        return None
    props = dict(node)
    labels = list(node.labels) if hasattr(node, "labels") else []
    if "name" in props:
        if "Domain" in labels:
            return f"domain_{props['name']}"
        if "Subdomain" in labels:
            return f"subdomain_{props['name']}"
        if "MX" in labels:
            return f"mx_{props.get('host', props['name'])}"
        if "NS" in labels:
            return f"ns_{props.get('host', props['name'])}"
        if "Certificate" in labels:
            return f"cert_{props.get('host', props['name'])}"
    if "address" in props:
        return f"ip_{props['address']}"
    if "host" in props:
        if "NS" in labels:
            return f"ns_{props['host']}"
        if "Certificate" in labels:
            return f"cert_{props['host']}"
        return f"mx_{props['host']}"
    if "ip" in props and "port" in props:
        return f"port_{props['ip']}_{props['port']}"
    if "number" in props:
        return f"asn_{props['number']}"
    return getattr(node, "element_id", str(id(node)))


_LABEL_TO_TYPE = {
    "IP": "ip",
    "Subdomain": "subdomain",
    "MX": "mx",
    "NS": "ns",
    "Certificate": "certificate",
    "Port": "port",
    "Technology": "technology",
    "ASN": "asn",
}


def _node_to_dict(node, inv_id: str) -> Optional[Dict]:
    """Convert a Neo4j node to the Cytoscape node format used by the frontend."""
    if not node:
        return None
    try:
        props = dict(node)
    except Exception as exc:
        logger.debug("Failed to coerce node properties to dict: %s", exc)
        props = {}
    node_id = _node_to_cy_id(node)
    if not node_id:
        return None
    label = (
        props.get("name")
        or props.get("address")
        or props.get("host")
        or props.get("number")
        or f"{props.get('ip', '')}:{props.get('port', '')}"
        or node_id
    )
    labels = list(node.labels) if hasattr(node, "labels") else []
    node_type = "domain"
    for neo_label, mapped in _LABEL_TO_TYPE.items():
        if neo_label in labels:
            node_type = mapped
            break
    return {
        "data": {
            "id": node_id,
            "label": str(label)[:50],
            "type": node_type,
            **{k: v for k, v in props.items() if k != "investigation_id" and v is not None},
        },
    }


def _cy_id_to_match(cy_id: str) -> tuple:
    """Convert Cytoscape id to Neo4j match params. Returns (label, key, value)."""
    if cy_id.startswith("domain_"):
        return ("Domain", "name", cy_id[7:])
    if cy_id.startswith("subdomain_"):
        return ("Subdomain", "name", cy_id[10:])
    if cy_id.startswith("ip_"):
        return ("IP", "address", cy_id[3:])
    if cy_id.startswith("port_"):
        parts = cy_id[5:].split("_")
        if len(parts) >= 2:
            port_val = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            return ("Port", "ip", (parts[0], port_val))
        return (None, None, None)
    if cy_id.startswith("asn_"):
        return ("ASN", "number", cy_id[4:])
    if cy_id.startswith("mx_"):
        return ("MX", "host", cy_id[3:])
    if cy_id.startswith("ns_"):
        return ("NS", "host", cy_id[3:])
    if cy_id.startswith("cert_"):
        return ("Certificate", "host", cy_id[5:])
    if cy_id.startswith("technology_"):
        return ("Technology", "name", cy_id[11:].replace("_", " "))
    return (None, None, None)


def add_enricher_result_to_investigation(
    investigation_id: str,
    source_entity_type: str,
    source_entity_value: str,
    enricher_name: str,
    new_nodes: List[Dict[str, Any]],
    new_edges: List[Dict[str, Any]],
) -> bool:
    """
    Add enricher output to investigation graph in Neo4j.
    new_nodes: [{"type": "ip", "value": "1.2.3.4", "metadata": {...}}, ...]
    new_edges: [{"source": "domain_example.com", "target": "ip_1.2.3.4", "rel": "RESOLVES_TO"}, ...]
    """
    _require_neo4j()
    inv_id = str(investigation_id)

    try:
        for new_node in new_nodes:
            etype = new_node.get("type", "entity")
            evalue = (
                new_node.get("value")
                or new_node.get("name")
                or new_node.get("address")
                or str(new_node.get("port", ""))
            )
            meta = new_node.get("metadata") or {}
            if etype == "port":
                meta.setdefault("ip", new_node.get("ip", ""))
                meta.setdefault("port", new_node.get("port", 0))
            add_investigation_entity(inv_id, etype, evalue, meta)

        driver = _get_driver()
        if not driver:
            return False
        with driver.session() as session:
            for new_edge in new_edges:
                src = new_edge.get("source")
                tgt = new_edge.get("target")
                rel = new_edge.get("rel", "RELATES_TO")
                if not src or not tgt:
                    continue
                src_label, src_key, src_val = _cy_id_to_match(src)
                tgt_label, tgt_key, tgt_val = _cy_id_to_match(tgt)
                if not src_label or not tgt_label:
                    continue
                params: Dict[str, Any] = {"inv_id": inv_id}
                src_clause = _build_endpoint_clause("a", src_label, src_key, src_val, params, "src")
                tgt_clause = _build_endpoint_clause("b", tgt_label, tgt_key, tgt_val, params, "tgt")
                if not src_clause or not tgt_clause:
                    continue
                session.run(
                    f"MATCH {src_clause[0]} WHERE {src_clause[1]} "
                    f"MATCH {tgt_clause[0]} WHERE {tgt_clause[1]} "
                    f"MERGE (a)-[r:{rel}]->(b) RETURN r",
                    **params,
                )
        return True
    except Exception as exc:
        logger.warning("Failed to add enricher %s result to investigation %s: %s",
                       enricher_name, inv_id, exc)
        return False


def _build_endpoint_clause(
    var: str,
    label: str,
    key: Optional[str],
    value: Any,
    params: Dict[str, Any],
    prefix: str,
) -> Optional[tuple]:
    """Build (match, where) clauses for an edge endpoint and populate ``params``."""
    if key in ("name", "host", "address", "number"):
        params[f"{prefix}_val"] = value
        return f"({var}:{label})", f"{var}.{key} = ${prefix}_val AND {var}.investigation_id = $inv_id"
    if key == "ip" and isinstance(value, tuple) and len(value) >= 2:
        params[f"{prefix}_ip"] = value[0]
        params[f"{prefix}_port"] = value[1]
        return (
            f"({var}:{label})",
            f"{var}.ip = ${prefix}_ip AND {var}.port = ${prefix}_port "
            f"AND {var}.investigation_id = $inv_id",
        )
    return None


def update_investigation_node_metadata(
    investigation_id: str,
    cy_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """
    Update properties on an existing investigation node.
    Used for enrichers that add metadata (e.g. WHOIS) without creating new nodes.
    """
    _require_neo4j()
    inv_id = str(investigation_id)
    label, key, val = _cy_id_to_match(cy_id)
    if not label or not key:
        return False
    props = {k: v for k, v in metadata.items() if v is not None}
    if not props:
        return True
    try:
        driver = _get_driver()
        if not driver:
            return False
        with driver.session() as session:
            if key == "name":
                session.run(
                    f"""
                    MATCH (n:{label}) WHERE n.name = $val AND n.investigation_id = $inv_id
                    SET n += $props
                    """,
                    val=val,
                    inv_id=inv_id,
                    props=props,
                )
            elif key == "host":
                session.run(
                    f"""
                    MATCH (n:{label}) WHERE n.host = $val AND n.investigation_id = $inv_id
                    SET n += $props
                    """,
                    val=val,
                    inv_id=inv_id,
                    props=props,
                )
            elif key == "address":
                session.run(
                    f"""
                    MATCH (n:{label}) WHERE n.address = $val AND n.investigation_id = $inv_id
                    SET n += $props
                    """,
                    val=val,
                    inv_id=inv_id,
                    props=props,
                )
            elif key == "number":
                session.run(
                    f"""
                    MATCH (n:{label}) WHERE n.number = $val AND n.investigation_id = $inv_id
                    SET n += $props
                    """,
                    val=val,
                    inv_id=inv_id,
                    props=props,
                )
            elif key == "ip" and isinstance(val, tuple) and len(val) >= 2:
                ip_val, port_val = val[0], val[1]
                session.run(
                    """
                    MATCH (n:Port) WHERE n.ip = $ip_val AND n.port = $port_val AND n.investigation_id = $inv_id
                    SET n += $props
                    """,
                    ip_val=ip_val,
                    port_val=port_val,
                    inv_id=inv_id,
                    props=props,
                )
            else:
                return False
        return True
    except Exception as exc:
        logger.warning("Failed to update node %s metadata in investigation %s: %s",
                       cy_id, inv_id, exc)
        return False


def delete_investigation_graph(investigation_id: str) -> bool:
    """Delete all nodes for an investigation from Neo4j."""
    _require_neo4j()
    inv_id = str(investigation_id)
    try:
        driver = _get_driver()
        if not driver:
            return False
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.investigation_id = $inv_id DETACH DELETE n",
                inv_id=inv_id,
            )
        return True
    except Exception as exc:
        logger.warning("Failed to delete investigation graph %s: %s", inv_id, exc)
        return False
