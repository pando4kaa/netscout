"""
Enricher Pipeline - executes enrichers in parallel phases for speed.

Phase 1 and Phase 2 overlap: Port starts as soon as DNS completes,
SSL/Tech start as soon as subdomain discovery completes.
"""

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set

from src.core.context import ScanContextData
from src.enrichers.base import AbstractEnricher

ProgressCallback = Callable[[str, int, str], None]
ReportFn = Callable[[str, str, int], None]

# Phase 1: independent (run in parallel)
PHASE1_ENRICHERS = ["dns", "whois", "subdomain"]
# Phase 2: depend on Phase 1 - port needs dns_info, ssl/tech need subdomains
PHASE2_ENRICHERS = ["ssl", "port", "tech"]
# Phase 3: depend on Phase 2 (external APIs, geoip)
PHASE3_ENRICHERS = ["external_apis", "geoip"]

# Monotonic WebSocket/UI progress (0-90 in pipeline; orchestrator uses 92-97;
# API sends 100 on done).
ENRICH_COMPLETE_PROGRESS = {
    "dns": 14,
    "whois": 22,
    "subdomain": 32,
    "port": 48,
    "ssl": 58,
    "tech": 68,
    "external_apis": 84,
    "geoip": 88,
}

_FALLBACK_PROGRESS = 88


class EnricherPipeline:
    """Executes enrichers in parallel phases. Phase 2 starts as soon as its deps are ready."""

    def __init__(
        self,
        enrichers: Optional[List[AbstractEnricher]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ):
        self.enrichers = enrichers or []
        self.on_progress = on_progress

    def add_enricher(self, enricher: AbstractEnricher) -> "EnricherPipeline":
        self.enrichers.append(enricher)
        return self

    def _collect_future(
        self,
        future: Future,
        enricher: AbstractEnricher,
        context: ScanContextData,
        report: Optional[ReportFn],
    ) -> None:
        """Drain one future into the context, reporting progress or error."""
        target = ENRICH_COMPLETE_PROGRESS.get(enricher.name, _FALLBACK_PROGRESS)
        try:
            context.merge(future.result())
            if report:
                report(enricher.name, f"{enricher.name} complete", target)
        except Exception as exc:
            if report:
                report(enricher.name, f"Error: {exc}", target)

    def _run_phase(
        self,
        domain: str,
        context: ScanContextData,
        enricher_names: List[str],
        report: Optional[ReportFn],
    ) -> None:
        """Run a phase of enrichers in parallel."""
        phase_enrichers = [e for e in self.enrichers if e.name in enricher_names]
        if not phase_enrichers:
            return

        with ThreadPoolExecutor(max_workers=len(phase_enrichers)) as executor:
            futures = {
                executor.submit(enr.enrich, domain, context.to_dict()): enr
                for enr in phase_enrichers
            }
            for future in as_completed(futures):
                self._collect_future(future, futures[future], context, report)

    def run(self, domain: str) -> Dict[str, Any]:
        """Run enrichers with overlapping phases for faster scanning."""
        context = ScanContextData(domain=domain)
        phase1_enrichers = [e for e in self.enrichers if e.name in PHASE1_ENRICHERS]
        phase2_enrichers = {e.name: e for e in self.enrichers if e.name in PHASE2_ENRICHERS}
        phase2_started: Set[str] = set()
        phase2_futures: Dict[Future, AbstractEnricher] = {}

        progress_floor = 0

        def report(stage: str, message: str, target: int) -> None:
            """Emit monotonic progress (never decreases) for WebSocket/UI."""
            nonlocal progress_floor
            clamped = max(target, progress_floor)
            progress_floor = clamped
            if self.on_progress:
                self.on_progress(stage, clamped, message)

        max_workers = len(phase1_enrichers) + len(PHASE2_ENRICHERS)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            def maybe_start_phase2(completed_name: str) -> None:
                """Schedule Phase 2 enrichers as soon as their dependencies arrive."""
                if completed_name == "dns" and context.dns_info and "port" not in phase2_started:
                    port_enr = phase2_enrichers.get("port")
                    if port_enr:
                        phase2_started.add("port")
                        fut = executor.submit(port_enr.enrich, domain, context.to_dict())
                        phase2_futures[fut] = port_enr
                if completed_name == "subdomain":
                    for name in ("ssl", "tech"):
                        if name in phase2_started:
                            continue
                        enr = phase2_enrichers.get(name)
                        if enr:
                            phase2_started.add(name)
                            fut = executor.submit(enr.enrich, domain, context.to_dict())
                            phase2_futures[fut] = enr

            report("phase1", "Running DNS, WHOIS, Subdomains...", 5)
            p1_futures = {
                executor.submit(enr.enrich, domain, context.to_dict()): enr
                for enr in phase1_enrichers
            }
            for future in as_completed(p1_futures):
                enricher = p1_futures[future]
                target = ENRICH_COMPLETE_PROGRESS.get(enricher.name, progress_floor + 1)
                try:
                    context.merge(future.result())
                    maybe_start_phase2(enricher.name)
                    report(enricher.name, f"{enricher.name} complete", target)
                except Exception as exc:
                    report(enricher.name, f"Error: {exc}", target)

            if phase2_futures:
                report("phase2", "Running SSL, Port, Tech...", 36)
                for future in as_completed(phase2_futures):
                    self._collect_future(future, phase2_futures[future], context, report)

            for name in PHASE2_ENRICHERS:
                if name in phase2_started:
                    continue
                enricher = phase2_enrichers.get(name)
                if not enricher:
                    continue
                target = ENRICH_COMPLETE_PROGRESS.get(name, progress_floor + 1)
                try:
                    context.merge(enricher.enrich(domain, context.to_dict()))
                    report(name, f"{name} complete", target)
                except Exception as exc:
                    report(name, f"Error: {exc}", target)

        report("phase3", "Running GeoIP, External APIs...", 72)
        self._run_phase(domain, context, PHASE3_ENRICHERS, report)

        report("pipeline", "Enrichment complete", 90)
        return context.to_dict()
