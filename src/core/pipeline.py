"""
Enricher Pipeline — executes enrichers in parallel phases for speed.
Phase 1 and Phase 2 overlap: Port starts when DNS completes, SSL/Tech when Subdomains completes.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Any, Callable, Dict, List, Optional, Set

from src.core.context import ScanContextData
from src.enrichers.base import AbstractEnricher


ProgressCallback = Callable[[str, int, str], None]

# Phase 1: independent (run in parallel)
PHASE1_ENRICHERS = ["dns", "whois", "subdomain"]
# Phase 2: depend on Phase 1 — Port needs dns_info, SSL/Tech need subdomains
PHASE2_ENRICHERS = ["ssl", "port", "tech"]
# Phase 3: depend on Phase 2 (external APIs, geoip)
PHASE3_ENRICHERS = ["external_apis", "geoip"]


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

    def _run_phase(self, domain: str, context: ScanContextData, enricher_names: List[str]) -> None:
        """Run a phase of enrichers in parallel."""
        phase_enrichers = [e for e in self.enrichers if e.name in enricher_names]
        if not phase_enrichers:
            return

        with ThreadPoolExecutor(max_workers=len(phase_enrichers)) as executor:
            futures = {
                executor.submit(e.enrich, domain, context.to_dict()): e
                for e in phase_enrichers
            }
            for future in as_completed(futures):
                enricher = futures[future]
                try:
                    result = future.result()
                    context.merge(result)
                    if self.on_progress:
                        self.on_progress(enricher.name, 0, f"{enricher.name} complete")
                except Exception as e:
                    if self.on_progress:
                        self.on_progress(enricher.name, 0, f"Error: {e}")

    def run(self, domain: str) -> Dict[str, Any]:
        """Run enrichers with overlapping phases for faster scanning."""
        context = ScanContextData(domain=domain)
        phase1_enrichers = [e for e in self.enrichers if e.name in PHASE1_ENRICHERS]
        phase2_enrichers = {e.name: e for e in self.enrichers if e.name in PHASE2_ENRICHERS}
        phase2_started: Set[str] = set()
        phase2_futures: Dict[Future, Any] = {}

        def maybe_start_phase2(completed_name: str) -> None:
            # Port: needs dns_info (IPs)
            if completed_name == "dns" and context.dns_info and "port" not in phase2_started:
                port_e = phase2_enrichers.get("port")
                if port_e:
                    phase2_started.add("port")
                    f = executor.submit(port_e.enrich, domain, context.to_dict())
                    phase2_futures[f] = port_e
            # SSL, Tech: need subdomains (SubdomainEnricher has completed)
            if completed_name == "subdomain" and "ssl" not in phase2_started:
                for name in ("ssl", "tech"):
                    if name not in phase2_started:
                        e = phase2_enrichers.get(name)
                        if e:
                            phase2_started.add(name)
                            f = executor.submit(e.enrich, domain, context.to_dict())
                            phase2_futures[f] = e

        max_workers = len(phase1_enrichers) + len(PHASE2_ENRICHERS)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Phase 1
            if self.on_progress:
                self.on_progress("phase1", 10, "Running DNS, WHOIS, Subdomains...")
            p1_futures = {
                executor.submit(e.enrich, domain, context.to_dict()): e
                for e in phase1_enrichers
            }
            for future in as_completed(p1_futures):
                enricher = p1_futures[future]
                try:
                    result = future.result()
                    context.merge(result)
                    maybe_start_phase2(enricher.name)
                    if self.on_progress:
                        self.on_progress(enricher.name, 0, f"{enricher.name} complete")
                except Exception as e:
                    if self.on_progress:
                        self.on_progress(enricher.name, 0, f"Error: {e}")

            # Wait for Phase 2 (may have started during Phase 1)
            if phase2_futures:
                if self.on_progress:
                    self.on_progress("phase2", 50, "Running SSL, Port, Tech...")
                for future in as_completed(phase2_futures):
                    enricher = phase2_futures[future]
                    try:
                        result = future.result()
                        context.merge(result)
                        if self.on_progress:
                            self.on_progress(enricher.name, 0, f"{enricher.name} complete")
                    except Exception as e:
                        if self.on_progress:
                            self.on_progress(enricher.name, 0, f"Error: {e}")

            # Phase 2 enrichers that weren't started by overlap (e.g. if deps not ready)
            for name in PHASE2_ENRICHERS:
                if name not in phase2_started:
                    e = phase2_enrichers.get(name)
                    if e:
                        try:
                            result = e.enrich(domain, context.to_dict())
                            context.merge(result)
                            if self.on_progress:
                                self.on_progress(e.name, 0, f"{e.name} complete")
                        except Exception as err:
                            if self.on_progress:
                                self.on_progress(e.name, 0, f"Error: {err}")

        # Phase 3
        if self.on_progress:
            self.on_progress("phase3", 85, "Running GeoIP, External APIs...")
        self._run_phase(domain, context, PHASE3_ENRICHERS)

        if self.on_progress:
            self.on_progress("done", 100, "Scan complete")
        return context.to_dict()
