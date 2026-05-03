"""
OWASP-adapted grouped risk scoring for NetScout.
"""

import hashlib
import math
from typing import Any, Dict, Iterable, List, Tuple

from src.analysis.asset_weight import asset_context, normalize_asset_host
from src.core.models import Alert, RiskLevel
from src.integrations.cisa_kev_client import get_kev_entries
from src.integrations.epss_client import get_epss_scores


RISK_WEIGHTS = {RiskLevel.HIGH: 10.0, RiskLevel.MEDIUM: 5.0, RiskLevel.LOW: 1.0}


def _level_value(level: Any) -> str:
    if hasattr(level, "value"):
        return str(level.value)
    return str(level)


def _legacy_severity(alert: Alert) -> float:
    return RISK_WEIGHTS.get(alert.level, 1.0)


def _cve_ids(cves: Iterable[Dict[str, Any]]) -> List[str]:
    return sorted({str(cve.get("id") or cve.get("cve") or "").upper() for cve in cves if cve.get("id") or cve.get("cve")})


def _alert_cves(alert: Alert) -> List[Dict[str, Any]]:
    details = alert.details or {}
    cves = details.get("cves")
    return cves if isinstance(cves, list) else []


def _group_key(alert: Alert, apex_domain: str) -> str:
    details = alert.details or {}
    target = normalize_asset_host(alert.target or apex_domain)

    if alert.type == "outdated_tech":
        software = str(details.get("software") or "").lower()
        version = str(details.get("version") or "").lower()
        cves = ",".join(_cve_ids(_alert_cves(alert)))
        return f"{alert.type}:{software}:{version}:{cves}"

    if alert.type == "open_port":
        return f"{alert.type}:{details.get('port')}:{details.get('service')}:{target}"

    if alert.type == "missing_dmarc":
        return f"{alert.type}:{apex_domain}"

    if alert.type == "missing_security_headers":
        missing = ",".join(sorted(details.get("missing") or []))
        return f"{alert.type}:{missing}:{target}"

    if alert.type == "expired_ssl":
        return f"{alert.type}:{target}"

    if alert.type == "subdomain_takeover":
        cname = details.get("cname") or details.get("provider") or ""
        return f"{alert.type}:{cname}:{target}"

    indicator = target or apex_domain
    source = details.get("source") or alert.type
    return f"{alert.type}:{source}:{indicator}"


def group_alerts(alerts: List[Alert], apex_domain: str) -> List[Dict[str, Any]]:
    """Group repeated findings so identical issues are scored once."""
    groups: Dict[str, Dict[str, Any]] = {}

    for alert in alerts:
        key = _group_key(alert, apex_domain)
        target = normalize_asset_host(alert.target or apex_domain)
        if not target:
            target = apex_domain

        if key not in groups:
            group_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
            groups[key] = {
                "group_id": group_id,
                "group_key": key,
                "type": alert.type,
                "alerts": [],
                "targets": [],
                "levels": [],
                "cves": [],
                "details": alert.details or {},
            }

        group = groups[key]
        group["alerts"].append(alert)
        group["levels"].append(alert.level)
        if target not in group["targets"]:
            group["targets"].append(target)
        for cve in _alert_cves(alert):
            cve_id = str(cve.get("id") or cve.get("cve") or "").upper()
            if cve_id and all(str(existing.get("id") or existing.get("cve") or "").upper() != cve_id for existing in group["cves"]):
                group["cves"].append(dict(cve))

    return list(groups.values())


def _all_cve_ids(groups: List[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []
    for group in groups:
        ids.extend(_cve_ids(group.get("cves") or []))
    return sorted(set(ids))


def enrich_group_cves(groups: List[Dict[str, Any]]) -> None:
    """Attach EPSS and CISA KEV data to group CVE entries when available."""
    cve_ids = _all_cve_ids(groups)
    if not cve_ids:
        return

    epss = get_epss_scores(cve_ids)
    kev = get_kev_entries(cve_ids)

    for group in groups:
        for cve in group.get("cves") or []:
            cve_id = str(cve.get("id") or cve.get("cve") or "").upper()
            if not cve_id:
                continue
            if cve_id in epss:
                cve.update(epss[cve_id])
            if cve_id in kev:
                cve["kev"] = True
                cve["kev_details"] = kev[cve_id]
            else:
                cve.setdefault("kev", False)


def _severity(group: Dict[str, Any]) -> Tuple[float, str]:
    cvss_values = [float(cve["cvss"]) for cve in group.get("cves") or [] if isinstance(cve.get("cvss"), (int, float))]
    if cvss_values:
        return max(cvss_values), "cvss"
    legacy_values = [_legacy_severity(alert) for alert in group.get("alerts") or []]
    return max(legacy_values or [1.0]), "legacy"


def _weighted_average(factors: List[Dict[str, Any]]) -> float:
    total_weight = sum(float(factor.get("weight", 1.0)) for factor in factors)
    if total_weight <= 0:
        return 0.0
    score = sum(float(factor["score"]) * float(factor.get("weight", 1.0)) for factor in factors) / total_weight
    return round(score, 2)


def _factor(name: str, score: float, weight: float, rationale: str) -> Dict[str, Any]:
    score = max(0.0, min(10.0, float(score)))
    weight = float(weight)
    return {
        "name": name,
        "score": round(score, 2),
        "weight": weight,
        "weighted_score": round(score * weight, 2),
        "rationale": rationale,
    }


def _max_epss(group: Dict[str, Any]) -> float | None:
    values = [float(cve["epss"]) for cve in group.get("cves") or [] if isinstance(cve.get("epss"), (int, float))]
    return max(values) if values else None


def _has_kev(group: Dict[str, Any]) -> bool:
    return any(bool(cve.get("kev")) for cve in group.get("cves") or [])


def _asset_contexts(group: Dict[str, Any], apex_domain: str) -> List[Dict[str, Any]]:
    return [asset_context(target, apex_domain) for target in group.get("targets") or []]


def _environment_score(contexts: List[Dict[str, Any]]) -> Tuple[float, str]:
    if not contexts:
        return 5.0, "Asset environment is unknown"
    non_prod = sum(1 for ctx in contexts if ctx.get("environment") == "non_production")
    ratio = non_prod / len(contexts)
    if ratio >= 0.75:
        return 3.5, "Most affected assets look like non-production environments"
    if ratio > 0:
        return 5.5, "Affected assets include a mix of production and non-production names"
    return 7.0, "Affected assets look production-facing from hostname context"


def _exposure_score(count: int) -> float:
    if count <= 1:
        return 2.0
    if count <= 3:
        return 4.0
    if count <= 10:
        return 6.0
    if count <= 30:
        return 8.0
    return 9.0


def _exposure_multiplier(count: int) -> float:
    if count <= 1:
        return 1.0
    return round(min(1.5, 1 + math.log2(count) / 10), 2)


def _asset_impact_score(contexts: List[Dict[str, Any]]) -> Tuple[float, str]:
    class_scores = {
        "apex": 7.5,
        "critical_service": 8.0,
        "auxiliary_service": 5.5,
        "subdomain": 5.0,
        "ip": 5.5,
        "lower_criticality": 3.0,
        "external_or_unknown": 4.0,
        "unknown": 4.0,
    }
    if not contexts:
        return 4.0, "Asset criticality is unknown"
    scores = []
    for ctx in contexts:
        score = class_scores.get(ctx.get("asset_class"), 4.0)
        if ctx.get("environment") == "non_production":
            score *= 0.75
        scores.append(score)
    max_score = max(scores)
    return round(max_score, 2), "Highest impacted asset role is used for conservative prioritization"


def _cia_impact_score(group_type: str, severity: float) -> Tuple[float, str]:
    scores = {
        "outdated_tech": max(5.0, severity),
        "open_port": 7.0,
        "subdomain_takeover": 7.5,
        "expired_ssl": 4.5,
        "weak_tls": 5.0,
        "missing_dmarc": 4.0,
        "missing_security_headers": 3.0,
        "abuseipdb": 4.5,
        "criminalip": 5.0,
        "pulsedive": 5.0,
        "phishtank": 7.0,
    }
    return scores.get(group_type, 5.0), "Estimated technical CIA impact for this finding type"


def _reputation_impact_score(group_type: str) -> Tuple[float, str]:
    scores = {
        "missing_dmarc": 7.0,
        "phishtank": 8.0,
        "abuseipdb": 6.0,
        "criminalip": 6.0,
        "pulsedive": 6.0,
        "subdomain_takeover": 6.0,
    }
    return scores.get(group_type, 2.0), "Reputation/phishing impact estimated from finding type"


def _service_role_score(contexts: List[Dict[str, Any]]) -> Tuple[float, str]:
    role_scores = {
        "auth": 8.5,
        "login": 8.5,
        "sso": 8.5,
        "vpn": 8.5,
        "admin": 8.0,
        "api": 7.5,
        "account": 7.5,
        "accounts": 7.5,
        "storage": 7.0,
        "files": 6.5,
        "mail": 6.0,
        "smtp": 6.0,
        "main_domain": 7.0,
    }
    if not contexts:
        return 4.0, "Service role is unknown"
    scores = [role_scores.get(str(ctx.get("business_role")), 4.5) for ctx in contexts]
    return max(scores), "Most sensitive detected service role is used"


def _exploit_maturity_score(group: Dict[str, Any]) -> Tuple[float, str]:
    if _has_kev(group):
        return 9.5, "At least one CVE is listed in CISA KEV as known exploited"

    epss = _max_epss(group)
    if epss is not None:
        if epss >= 0.5:
            return 8.0, f"EPSS probability is high ({epss:.3f})"
        if epss >= 0.1:
            return 6.0, f"EPSS probability is elevated ({epss:.3f})"
        return 3.5, f"EPSS probability is low ({epss:.3f})"

    if group.get("cves"):
        return 5.0, "CVE exists, but exploit probability is unknown"
    return 3.0, "No CVE/exploitability signal is attached to this finding"


def _known_vulnerability_score(group: Dict[str, Any]) -> Tuple[float, str]:
    if _has_kev(group):
        return 10.0, "Known exploited CVE is present"
    if group.get("cves"):
        return 8.0, "At least one CVE is associated with the finding"
    if group.get("type") in {"expired_ssl", "missing_dmarc", "missing_security_headers", "open_port"}:
        return 4.5, "Rule-based security weakness without a CVE"
    return 3.0, "Heuristic finding without formal vulnerability mapping"


def _type_likelihood_scores(group_type: str) -> Tuple[float, float, str]:
    public_exposure = {
        "open_port": 9.0,
        "outdated_tech": 8.0,
        "subdomain_takeover": 8.0,
        "expired_ssl": 7.0,
        "weak_tls": 7.0,
        "missing_security_headers": 7.0,
        "missing_dmarc": 6.0,
        "phishtank": 8.0,
    }.get(group_type, 6.0)
    ease_of_exploit = {
        "open_port": 6.5,
        "outdated_tech": 5.5,
        "subdomain_takeover": 7.0,
        "expired_ssl": 3.5,
        "weak_tls": 4.5,
        "missing_security_headers": 3.5,
        "missing_dmarc": 5.0,
        "phishtank": 7.0,
    }.get(group_type, 5.0)
    return public_exposure, ease_of_exploit, "Estimated from finding type and Internet-facing OSINT evidence"


def _likelihood_factors(group: Dict[str, Any], contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    group_type = group.get("type")
    exposure, ease_exploit, type_reason = _type_likelihood_scores(group_type)
    known_vuln, known_reason = _known_vulnerability_score(group)
    exploit_maturity, exploit_reason = _exploit_maturity_score(group)
    env_score, env_reason = _environment_score(contexts)
    affected = len(group.get("targets") or [])
    repeat_score = _exposure_score(affected)

    return [
        _factor("public_exposure", exposure, 1.2, type_reason),
        _factor("known_vulnerability", known_vuln, 1.1, known_reason),
        _factor("exploit_maturity", exploit_maturity, 1.4, exploit_reason),
        _factor("ease_of_discovery", 8.0 if group_type in {"outdated_tech", "missing_security_headers", "missing_dmarc"} else 6.0, 0.7, "Finding can be discovered through automated reconnaissance"),
        _factor("ease_of_exploit", ease_exploit, 1.0, type_reason),
        _factor("environment", env_score, 0.8, env_reason),
        _factor("repeatability", repeat_score, 0.6, f"Finding affects {affected} distinct asset(s)"),
    ]


def _impact_factors(group: Dict[str, Any], contexts: List[Dict[str, Any]], severity: float) -> List[Dict[str, Any]]:
    group_type = group.get("type")
    asset_score, asset_reason = _asset_impact_score(contexts)
    cia_score, cia_reason = _cia_impact_score(group_type, severity)
    reputation_score, reputation_reason = _reputation_impact_score(group_type)
    role_score, role_reason = _service_role_score(contexts)
    affected = len(group.get("targets") or [])
    blast_radius = _exposure_score(affected)

    return [
        _factor("technical_severity", severity, 1.4, "CVSS is used when available; otherwise rule severity is used"),
        _factor("asset_criticality", asset_score, 1.2, asset_reason),
        _factor("cia_impact", cia_score, 1.0, cia_reason),
        _factor("reputation_impact", reputation_score, 0.6, reputation_reason),
        _factor("service_role", role_score, 0.8, role_reason),
        _factor("blast_radius", blast_radius, 0.7, f"Finding affects {affected} distinct asset(s)"),
    ]


def _confidence(group: Dict[str, Any]) -> Tuple[str, float, str]:
    group_type = group.get("type")
    if _has_kev(group):
        return "high", 1.0, "Known exploited CVE gives high confidence"
    if group_type in {"open_port", "expired_ssl", "phishtank", "abuseipdb", "criminalip", "pulsedive"}:
        return "high", 1.0, "Finding is based on direct service or reputation evidence"
    if group_type == "outdated_tech":
        if group.get("cves"):
            return "medium", 0.75, "Banner/version-based CVE match may require manual validation"
        return "low", 0.5, "Outdated technology is inferred from banner data only"
    if group_type in {"missing_dmarc", "missing_security_headers", "subdomain_takeover"}:
        return "medium", 0.75, "Configuration weakness is detected by deterministic checks"
    return "medium", 0.75, "Default confidence for heuristic OSINT finding"


def risk_level(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _title(group: Dict[str, Any]) -> str:
    details = group.get("details") or {}
    if group.get("type") == "outdated_tech":
        software = details.get("software") or "technology"
        version = details.get("version") or "unknown version"
        return f"Outdated {software} {version}"
    first = (group.get("alerts") or [None])[0]
    return first.message if first else str(group.get("type"))


def _recommendation(group: Dict[str, Any]) -> str:
    group_type = group.get("type")
    if group_type == "outdated_tech":
        return "Validate whether the package has vendor backported patches, then update or patch the affected service and avoid exposing exact server versions."
    if group_type == "missing_dmarc":
        return "Publish a DMARC policy, start with monitoring if needed, and progress toward quarantine or reject after validation."
    if group_type == "open_port":
        return "Verify business need for the exposed service and restrict access with firewall rules, VPN, or service hardening."
    if group_type == "missing_security_headers":
        return "Add missing security headers such as HSTS and X-Frame-Options or CSP frame-ancestors where applicable."
    if group_type == "expired_ssl":
        return "Renew the certificate and automate renewal monitoring."
    if group_type == "subdomain_takeover":
        return "Verify ownership of the referenced third-party service and remove or claim dangling DNS records."
    return "Review the finding, validate the evidence, and prioritize remediation according to affected asset criticality."


def score_group(group: Dict[str, Any], apex_domain: str) -> Dict[str, Any]:
    contexts = _asset_contexts(group, apex_domain)
    severity, severity_source = _severity(group)
    likelihood_factors = _likelihood_factors(group, contexts)
    impact_factors = _impact_factors(group, contexts, severity)
    likelihood = _weighted_average(likelihood_factors)
    impact = _weighted_average(impact_factors)
    exposure_score = _exposure_score(len(group.get("targets") or []))
    exposure_multiplier = _exposure_multiplier(len(group.get("targets") or []))
    confidence, confidence_multiplier, confidence_reason = _confidence(group)
    base_risk = likelihood * impact
    risk_score = round(min(100.0, base_risk * exposure_multiplier * confidence_multiplier), 2)

    evidence = [confidence_reason]
    if group.get("cves"):
        evidence.append(f"Associated CVEs: {', '.join(_cve_ids(group['cves']))}")
    evidence.extend([ctx.get("reason") for ctx in contexts[:3] if ctx.get("reason")])

    return {
        "group_id": group["group_id"],
        "type": group["type"],
        "title": _title(group),
        "risk_score": risk_score,
        "risk_level": risk_level(risk_score),
        "affected_assets": len(group.get("targets") or []),
        "representative_targets": (group.get("targets") or [])[:8],
        "severity": round(severity, 2),
        "severity_source": severity_source,
        "likelihood": likelihood,
        "impact": impact,
        "exposure_score": exposure_score,
        "exposure_multiplier": exposure_multiplier,
        "confidence": confidence,
        "confidence_multiplier": confidence_multiplier,
        "factors": {
            "likelihood": likelihood_factors,
            "impact": impact_factors,
            "confidence": [_factor("confidence", confidence_multiplier * 10, 1.0, confidence_reason)],
        },
        "cves": group.get("cves") or [],
        "evidence": evidence,
        "recommendation": _recommendation(group),
    }


def compute_overall_risk(risk_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    sorted_groups = sorted(risk_groups, key=lambda item: item["risk_score"], reverse=True)
    scores = [group["risk_score"] for group in sorted_groups]
    if not scores:
        return {
            "risk_overall": 0.0,
            "risk_level": "LOW",
            "max_severity": 0.0,
            "exposure_score": 0.0,
            "confidence": "unknown",
            "risk_groups": [],
        }

    overall = scores[0]
    if len(scores) > 1:
        overall += 0.35 * scores[1]
    if len(scores) > 2:
        overall += 0.20 * scores[2]
    if len(scores) > 3:
        overall += 0.10 * sum(scores[3:10])
    overall = round(min(100.0, overall), 2)

    max_severity = round(max(group["severity"] for group in sorted_groups), 2)
    exposure_score = round(max(group["exposure_score"] for group in sorted_groups), 2)
    confidence_order = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    confidence = max(
        (group["confidence"] for group in sorted_groups),
        key=lambda value: confidence_order.get(value, 0),
    )

    return {
        "risk_overall": overall,
        "risk_level": risk_level(overall),
        "max_severity": max_severity,
        "exposure_score": exposure_score,
        "confidence": confidence,
        "risk_groups": sorted_groups,
    }


def compute_risk_v3(alerts: List[Alert], apex_domain: str) -> Dict[str, Any]:
    """Compute grouped, OWASP-adapted V3 risk summary."""
    groups = group_alerts(alerts, apex_domain)
    enrich_group_cves(groups)
    risk_groups = [score_group(group, apex_domain) for group in groups]
    summary = compute_overall_risk(risk_groups)
    summary["risk_method"] = "OWASP-adapted grouped V3"
    return summary
