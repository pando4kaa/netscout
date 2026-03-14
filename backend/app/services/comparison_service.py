"""
Comparison service — detailed comparison of two scan results.
Produces structured diff for subdomains, DNS, WHOIS, SSL, ports, tech stack, alerts.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


def _to_set(items: List[Any]) -> Set[str]:
    """Normalize items to set of strings for comparison."""
    return set(str(x) for x in (items or []) if x is not None)


def _compare_sets(s1: Set[str], s2: Set[str]) -> Dict[str, List[str]]:
    return {
        "only_in_1": sorted(s1 - s2),
        "only_in_2": sorted(s2 - s1),
        "in_both": sorted(s1 & s2),
    }


def _compare_dns_records(r1: Dict, r2: Dict, key: str) -> Optional[Dict[str, List]]:
    """Compare simple list DNS records (A, AAAA, NS, TXT, CNAME)."""
    list1 = r1.get(key) or []
    list2 = r2.get(key) or []
    if list1 and isinstance(list1[0], dict):
        return None  # MX has structure
    s1, s2 = _to_set(list1), _to_set(list2)
    if not s1 and not s2:
        return None
    return _compare_sets(s1, s2)


def _compare_mx(mx1: List, mx2: List) -> Dict[str, List]:
    """Compare MX records by host string."""
    hosts1 = _to_set([m.get("host", m) for m in (mx1 or []) if m])
    hosts2 = _to_set([m.get("host", m) for m in (mx2 or []) if m])
    return _compare_sets(hosts1, hosts2)


def _compare_whois(w1: Dict, w2: Dict) -> Dict[str, Any]:
    """Compare WHOIS data."""
    if not w1 and not w2:
        return {}
    w1 = w1 or {}
    w2 = w2 or {}
    ns1 = _to_set(w1.get("name_servers") or [])
    ns2 = _to_set(w2.get("name_servers") or [])
    return {
        "registrar": {
            "value_1": w1.get("registrar"),
            "value_2": w2.get("registrar"),
            "changed": (w1.get("registrar") or "") != (w2.get("registrar") or ""),
        },
        "creation_date": {
            "value_1": w1.get("creation_date"),
            "value_2": w2.get("creation_date"),
            "changed": str(w1.get("creation_date") or "") != str(w2.get("creation_date") or ""),
        },
        "expiration_date": {
            "value_1": w1.get("expiration_date"),
            "value_2": w2.get("expiration_date"),
            "changed": str(w1.get("expiration_date") or "") != str(w2.get("expiration_date") or ""),
        },
        "name_servers": _compare_sets(ns1, ns2),
        "emails": _compare_sets(
            _to_set(w1.get("emails") or []),
            _to_set(w2.get("emails") or []),
        ),
    }


def _compare_ssl(ssl1: Dict, ssl2: Dict) -> Dict[str, Any]:
    """Compare SSL certificates by host."""
    certs1 = {c.get("host", ""): c for c in (ssl1.get("certificates") or []) if c.get("host")}
    certs2 = {c.get("host", ""): c for c in (ssl2.get("certificates") or []) if c.get("host")}
    hosts1 = set(certs1.keys())
    hosts2 = set(certs2.keys())
    hosts_both = hosts1 & hosts2
    expired_changes = []
    for h in hosts_both:
        exp1 = certs1.get(h, {}).get("is_expired", False)
        exp2 = certs2.get(h, {}).get("is_expired", False)
        if exp1 != exp2:
            expired_changes.append({
                "host": h,
                "was_expired_1": exp1,
                "is_expired_2": exp2,
            })
    return {
        "hosts_only_in_1": sorted(hosts1 - hosts2),
        "hosts_only_in_2": sorted(hosts2 - hosts1),
        "hosts_in_both": sorted(hosts_both),
        "expired_changes": expired_changes,
        "count_1": len(hosts1),
        "count_2": len(hosts2),
    }


def _get_ports_by_ip(port_scan: List[Dict]) -> Dict[str, Set[int]]:
    """Extract open ports per IP from port_scan results."""
    result: Dict[str, Set[int]] = {}
    for item in port_scan or []:
        ip = item.get("ip", "")
        if not ip:
            continue
        ports = set()
        for p in item.get("open_ports") or []:
            port = p.get("port") if isinstance(p, dict) else p
            if port is not None:
                ports.add(int(port))
        result[ip] = ports
    return result


def _compare_ports(port1: List[Dict], port2: List[Dict]) -> Dict[str, Any]:
    """Compare port scan results."""
    by_ip1 = _get_ports_by_ip(port1)
    by_ip2 = _get_ports_by_ip(port2)
    all_ips = set(by_ip1.keys()) | set(by_ip2.keys())
    by_ip = {}
    new_ports_total = 0
    closed_ports_total = 0
    for ip in sorted(all_ips):
        p1 = by_ip1.get(ip, set())
        p2 = by_ip2.get(ip, set())
        diff = _compare_sets(set(str(x) for x in p1), set(str(x) for x in p2))
        if diff["only_in_1"] or diff["only_in_2"]:
            by_ip[ip] = {
                "only_in_1": diff["only_in_1"],
                "only_in_2": diff["only_in_2"],
                "in_both": diff["in_both"],
            }
            new_ports_total += len(diff["only_in_2"])
            closed_ports_total += len(diff["only_in_1"])
    return {
        "by_ip": by_ip,
        "new_ports_count": new_ports_total,
        "closed_ports_count": closed_ports_total,
        "ips_with_changes": len(by_ip),
    }


def _compare_tech_stack(t1: Dict, t2: Dict) -> Dict[str, Any]:
    """Compare tech stack (flat keys)."""
    keys1 = set((t1 or {}).keys())
    keys2 = set((t2 or {}).keys())
    only_1 = sorted(keys1 - keys2)
    only_2 = sorted(keys2 - keys1)
    in_both = sorted(keys1 & keys2)
    # For in_both, check if values differ
    value_changes = []
    for k in in_both:
        v1 = t1.get(k)
        v2 = t2.get(k)
        if str(v1 or "") != str(v2 or ""):
            value_changes.append({"tech": k, "value_1": v1, "value_2": v2})
    return {
        "only_in_1": only_1,
        "only_in_2": only_2,
        "in_both": in_both,
        "value_changes": value_changes,
    }


def _compare_alerts(a1: List[Dict], a2: List[Dict]) -> Dict[str, Any]:
    """Compare alerts by type+message+target."""
    def key(a: Dict) -> str:
        return f"{a.get('type', '')}|{a.get('message', '')}|{a.get('target', '')}"

    set1 = {key(a): a for a in (a1 or [])}
    set2 = {key(a): a for a in (a2 or [])}
    keys1 = set(set1.keys())
    keys2 = set(set2.keys())
    only_1 = [set1[k] for k in sorted(keys1 - keys2)]
    only_2 = [set2[k] for k in sorted(keys2 - keys1)]
    in_both = [set1[k] for k in sorted(keys1 & keys2)]
    return {
        "only_in_1": only_1,
        "only_in_2": only_2,
        "in_both": in_both,
        "count_1": len(a1 or []),
        "count_2": len(a2 or []),
    }


def build_comparison(r1: Dict[str, Any], r2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build detailed comparison of two scan results.
    Both must be for the same domain.
    """
    dns1 = r1.get("dns_info") or {}
    dns2 = r2.get("dns_info") or {}
    sub1 = _to_set(r1.get("subdomains") or [])
    sub2 = _to_set(r2.get("subdomains") or [])
    ips1 = set()
    ips2 = set()
    for ip in dns1.get("a_records") or []:
        ips1.add(str(ip))
    for ip in dns1.get("aaaa_records") or []:
        ips1.add(str(ip))
    for ip in dns2.get("a_records") or []:
        ips2.add(str(ip))
    for ip in dns2.get("aaaa_records") or []:
        ips2.add(str(ip))

    summary1 = r1.get("summary") or {}
    summary2 = r2.get("summary") or {}
    risk1 = summary1.get("risk_score", 0)
    risk2 = summary2.get("risk_score", 0)
    alerts1 = r1.get("alerts") or []
    alerts2 = r2.get("alerts") or []

    dns_compare = {}
    for key in ["a_records", "aaaa_records", "ns_records", "txt_records", "cname_records"]:
        diff = _compare_dns_records(dns1, dns2, key)
        if diff and (diff["only_in_1"] or diff["only_in_2"] or diff["in_both"]):
            dns_compare[key] = diff
    mx_diff = _compare_mx(dns1.get("mx_records"), dns2.get("mx_records"))
    if mx_diff["only_in_1"] or mx_diff["only_in_2"] or mx_diff["in_both"]:
        dns_compare["mx_records"] = mx_diff

    whois_compare = _compare_whois(r1.get("whois_info"), r2.get("whois_info"))
    ssl_compare = _compare_ssl(r1.get("ssl_info") or {}, r2.get("ssl_info") or {})
    ports_compare = _compare_ports(r1.get("port_scan") or [], r2.get("port_scan") or [])
    tech_compare = _compare_tech_stack(r1.get("tech_stack") or {}, r2.get("tech_stack") or {})
    alerts_compare = _compare_alerts(alerts1, alerts2)

    return {
        "scan_1": {
            "scan_id": r1.get("scan_id"),
            "domain": r1.get("target_domain"),
            "date": r1.get("scan_date"),
            "risk_score": risk1,
            "subdomains_count": len(sub1),
            "ips_count": len(ips1),
            "alerts_count": len(alerts1),
        },
        "scan_2": {
            "scan_id": r2.get("scan_id"),
            "domain": r2.get("target_domain"),
            "date": r2.get("scan_date"),
            "risk_score": risk2,
            "subdomains_count": len(sub2),
            "ips_count": len(ips2),
            "alerts_count": len(alerts2),
        },
        "summary": {
            "risk_1": risk1,
            "risk_2": risk2,
            "risk_delta": risk2 - risk1,
            "alerts_1": len(alerts1),
            "alerts_2": len(alerts2),
            "subdomains_count_1": len(sub1),
            "subdomains_count_2": len(sub2),
            "subdomains_added": len(sub2 - sub1),
            "subdomains_removed": len(sub1 - sub2),
            "ips_count_1": len(ips1),
            "ips_count_2": len(ips2),
            "ips_added": len(ips2 - ips1),
            "ips_removed": len(ips1 - ips2),
        },
        "subdomains": {
            "only_in_1": sorted(sub1 - sub2),
            "only_in_2": sorted(sub2 - sub1),
            "in_both": sorted(sub1 & sub2),
            "count_1": len(sub1),
            "count_2": len(sub2),
        },
        "ips": {
            "only_in_1": sorted(ips1 - ips2),
            "only_in_2": sorted(ips2 - ips1),
            "in_both": sorted(ips1 & ips2),
        },
        "dns": dns_compare,
        "whois": whois_compare,
        "ssl": ssl_compare,
        "ports": ports_compare,
        "tech_stack": tech_compare,
        "alerts": alerts_compare,
    }
