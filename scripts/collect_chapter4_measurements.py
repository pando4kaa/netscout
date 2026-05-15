#!/usr/bin/env python3
"""
Collect reproducible measurements for diploma chapter 4 (one JSON file).

From repo root:
  python scripts/collect_chapter4_measurements.py [domain]

Loads .env from project root (for optional API keys affecting external enrichers).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env before settings / enrichers read API keys
try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

import importlib.util

from src.core.orchestrator import scan_domain


def _load_benchmark_module():
    path = _ROOT / "scripts" / "benchmark_pipeline_phases.py"
    spec = importlib.util.spec_from_file_location("benchmark_pipeline_phases", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _benchmark_both(domain: str) -> dict:
    bench = _load_benchmark_module()
    _parallel_with_marks = bench._parallel_with_marks
    _sequential = bench._sequential

    out: dict = {"domain": domain}
    t_par, marks, subs_p = _parallel_with_marks(domain)
    out["parallel"] = {
        "wall_seconds": round(t_par, 3),
        "phase_markers_seconds_from_start": {k: round(v, 3) for k, v in sorted(marks.items())},
        "subdomain_count": subs_p,
    }
    t_seq, per, subs_s = _sequential(domain)
    sum_seq_parts = round(sum(per.values()), 3)
    out["sequential"] = {
        "wall_seconds": round(t_seq, 3),
        "per_enrich_seconds": per,
        "sum_of_enrichers_seconds": sum_seq_parts,
        "subdomain_count": subs_s,
    }
    gain = round(out["sequential"]["wall_seconds"] - out["parallel"]["wall_seconds"], 3)
    out["comparison"] = {
        "sequential_minus_parallel_seconds": gain,
        "parallel_faster_by_seconds": gain,
        "note": "parallel = EnricherPipeline.run() with overlapping phases; "
        "sequential = same enrichers dns→…→geoip one after another on one context.",
    }
    return out


def _load_probe_module():
    path = _ROOT / "scripts" / "probe_subdomain_sources.py"
    spec = importlib.util.spec_from_file_location("probe_subdomain_sources", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


async def _probe(domain: str) -> dict:
    mod = _load_probe_module()
    return await mod._run(domain)


def _full_scan_with_log(domain: str) -> dict:
    t0 = time.perf_counter()
    log: list[dict] = []

    def on_progress(stage: str, pct: int, msg: str) -> None:
        log.append(
            {
                "elapsed_s": round(time.perf_counter() - t0, 3),
                "stage": stage,
                "pct": pct,
                "msg": msg,
            }
        )

    result = scan_domain(domain, on_progress=on_progress)
    wall = round(time.perf_counter() - t0, 3)
    d = result.model_dump(mode="json")
    dns = d.get("dns_info") or {}
    a_records = dns.get("a_records") or []
    port_scan = d.get("port_scan") or []
    open_ports_total = 0
    for row in port_scan:
        open_ports_total += len((row or {}).get("open_ports") or [])
    ssl = d.get("ssl_info") or {}
    certs = ssl.get("certificates") or []
    summary = d.get("summary") or {}
    alerts = d.get("alerts") or []

    # First-seen timestamps per stage for phase table
    first: dict[str, float] = {}
    for row in log:
        st = row["stage"]
        if st not in first:
            first[st] = row["elapsed_s"]

    return {
        "domain": domain,
        "wall_seconds_total": wall,
        "progress_events": log,
        "first_event_elapsed_s_by_stage": first,
        "metrics": {
            "subdomain_count": len(d.get("subdomains") or []),
            "a_record_count": len(a_records),
            "unique_ips_in_summary": summary.get("total_ip_addresses"),
            "open_port_findings_total": open_ports_total,
            "ssl_certificate_rows": len(certs),
            "risk_score_legacy_int": summary.get("risk_score"),
            "risk_overall_v3": summary.get("risk_overall"),
            "risk_level_v3": summary.get("risk_level"),
            "risk_method": summary.get("risk_method"),
            "alerts_count": len(alerts),
            "total_dns_records": summary.get("total_dns_records"),
        },
    }


def _derive_phase_windows(first: dict[str, float], wall: float) -> dict:
    """Approximate wall intervals from first progress callback per stage."""
    p1 = first.get("phase1", 0.0)
    p2 = first.get("phase2", wall)
    p3 = first.get("phase3", wall)
    an = first.get("analysis", wall)
    return {
        "approx_pipeline_phase1_to_phase2_s": round(max(0.0, p2 - p1), 3),
        "approx_pipeline_phase2_to_phase3_s": round(max(0.0, p3 - p2), 3),
        "approx_pipeline_phase3_until_analysis_callback_s": round(max(0.0, an - p3), 3),
        "approx_analysis_block_s": round(max(0.0, wall - an), 3),
        "note": "Timestamps are first on_progress fire per stage; sub-steps overlap inside pipeline.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", nargs="?", default="example.com")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_ROOT / "docs" / "chapter4_measurements_latest.json",
    )
    args = ap.parse_args()
    domain = args.domain.lower().strip()

    out: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_measurement_domain": domain,
        "environment_note": "Network-dependent (DNS, CT, third-party APIs). Values vary by run.",
    }

    print("Benchmark parallel vs sequential…", flush=True)
    out["benchmark_pipeline"] = _benchmark_both(domain)

    print("Probe subdomain sources…", flush=True)
    out["subdomain_sources_probe"] = {"domain": domain, "unique_counts_by_source": asyncio.run(_probe(domain))}

    print(f"Full scan_domain({domain!r})…", flush=True)
    scan_block = _full_scan_with_log(domain)
    scan_block["phase_windows_from_progress"] = _derive_phase_windows(
        scan_block["first_event_elapsed_s_by_stage"],
        scan_block["wall_seconds_total"],
    )
    out["full_scan_orchestrator"] = scan_block

    # Second scan for minimal reproducibility check (optional block)
    t0 = time.perf_counter()
    r2 = scan_domain(domain, on_progress=None)
    t1 = round(time.perf_counter() - t0, 3)
    out["second_scan_repeatability"] = {
        "wall_seconds": t1,
        "subdomain_count": len(r2.subdomains or []),
        "alerts_count": len(r2.alerts or []),
        "risk_score": r2.summary.risk_score,
        "note": "Two in-memory scans without persistence; counts may differ slightly if remote data changes.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(args.output), "full_scan_wall_s": scan_block["wall_seconds_total"]}, indent=2))


if __name__ == "__main__":
    main()
