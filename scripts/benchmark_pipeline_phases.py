#!/usr/bin/env python3
"""
Compare parallel EnricherPipeline.run() vs fully sequential enricher execution.

Usage (from repo root):
  python scripts/benchmark_pipeline_phases.py example.com

Prints JSON with wall-clock seconds. Sequential mode runs enrichers in dependency
order on a single thread (no phase-1/2 overlap).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.core.context import ScanContextData
from src.core.orchestrator import _build_pipeline


def _parallel_with_marks(domain: str) -> tuple[float, dict, int]:
    marks: dict[str, float] = {}
    t0 = time.perf_counter()

    def on_progress(stage: str, pct: int, msg: str) -> None:
        elapsed = time.perf_counter() - t0
        if stage == "phase1" and "phase1" not in marks:
            marks["phase1"] = elapsed
        elif stage == "phase2" and "phase2" not in marks:
            marks["phase2"] = elapsed
        elif stage == "phase3" and "phase3" not in marks:
            marks["phase3"] = elapsed
        elif stage == "analysis":
            marks.setdefault("analysis", elapsed)

    pipe = _build_pipeline(on_progress=on_progress)
    t_run = time.perf_counter()
    data = pipe.run(domain)
    wall = time.perf_counter() - t_run
    subs = len(data.get("subdomains") or [])
    return wall, marks, subs


def _sequential(domain: str) -> tuple[float, dict[str, float], int]:
    """Strict order: dns -> whois -> subdomain -> port -> ssl -> tech -> external_apis -> geoip."""
    pipe = _build_pipeline()
    order = [
        "dns",
        "whois",
        "subdomain",
        "port",
        "ssl",
        "tech",
        "external_apis",
        "geoip",
    ]
    per: dict[str, float] = {}
    ctx = ScanContextData(domain=domain)
    t0 = time.perf_counter()
    for name in order:
        enr = next((e for e in pipe.enrichers if e.name == name), None)
        if not enr:
            continue
        t1 = time.perf_counter()
        ctx.merge(enr.enrich(domain, ctx.to_dict()))
        per[name] = round(time.perf_counter() - t1, 3)
    total = time.perf_counter() - t0
    subs = len(ctx.to_dict().get("subdomains") or [])
    return total, per, subs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", nargs="?", default="example.com")
    ap.add_argument(
        "--mode",
        choices=("both", "parallel", "sequential"),
        default="both",
        help="parallel: overlapping pipeline only; sequential: strict one-by-one enrichers; both (default).",
    )
    args = ap.parse_args()
    domain = args.domain.lower().strip()

    out: dict = {"domain": domain}

    if args.mode in ("both", "parallel"):
        t_par, marks, subs_p = _parallel_with_marks(domain)
        out["parallel"] = {
            "wall_seconds": round(t_par, 3),
            "phase_markers_seconds_from_start": {k: round(v, 3) for k, v in sorted(marks.items())},
            "subdomain_count": subs_p,
        }

    if args.mode in ("both", "sequential"):
        t_seq, per, subs_s = _sequential(domain)
        sum_seq_parts = round(sum(per.values()), 3)
        out["sequential"] = {
            "wall_seconds": round(t_seq, 3),
            "per_enrich_seconds": per,
            "sum_of_enrichers_seconds": sum_seq_parts,
            "subdomain_count": subs_s,
        }

    if args.mode == "both" and "parallel" in out and "sequential" in out:
        overlap_gain = round(out["sequential"]["wall_seconds"] - out["parallel"]["wall_seconds"], 3)
        out["comparison"] = {
            "sequential_minus_parallel_seconds": overlap_gain,
            "interpretation": (
                "Positive value means parallel pipeline finished faster than "
                "strict sequential execution (overlap saves wall-clock time)."
            ),
        }

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
