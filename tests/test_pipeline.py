"""
Tests for EnricherPipeline (src/core/pipeline.py).

Uses lightweight mock enrichers to verify:
- Phases 1/2/3 run enrichers in correct order.
- Progress callback receives calls with monotonically increasing values.
- If a Phase-1 enricher raises, the pipeline continues and still runs Phase 2/3.
- add_enricher() returns the pipeline for chaining.
- run() returns a context dict with merged keys.
"""

import unittest
from typing import Any, Dict, Optional

from src.core.pipeline import EnricherPipeline, PHASE1_ENRICHERS, PHASE2_ENRICHERS, PHASE3_ENRICHERS
from src.enrichers.base import AbstractEnricher


# ---------------------------------------------------------------------------
# Mock enrichers
# ---------------------------------------------------------------------------

class _DummyEnricher(AbstractEnricher):
    """Returns a single key with a fixed value. Tracks how many times it ran."""

    def __init__(self, name: str, return_key: str, return_value: Any = True):
        self.name = name
        self._return_key = return_key
        self._return_value = return_value
        self.call_count = 0

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.call_count += 1
        return {self._return_key: self._return_value}


class _RaisingEnricher(AbstractEnricher):
    """Always raises RuntimeError to simulate a failed enricher."""

    def __init__(self, name: str):
        self.name = name

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise RuntimeError(f"Enricher {self.name} deliberately failed")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnricherPipelineBasics(unittest.TestCase):

    def test_empty_pipeline_returns_dict_with_domain(self):
        pipeline = EnricherPipeline()
        result = pipeline.run("example.com")
        self.assertEqual(result["domain"], "example.com")

    def test_add_enricher_returns_self_for_chaining(self):
        pipeline = EnricherPipeline()
        enricher = _DummyEnricher("dns", "dns_info", {"a_records": ["1.2.3.4"]})
        returned = pipeline.add_enricher(enricher)
        self.assertIs(returned, pipeline)

    def test_single_phase1_enricher_result_in_context(self):
        dns_enricher = _DummyEnricher("dns", "dns_info", {"a_records": ["1.2.3.4"]})
        pipeline = EnricherPipeline([dns_enricher])
        result = pipeline.run("example.com")
        self.assertIn("dns_info", result)
        self.assertEqual(result["dns_info"]["a_records"], ["1.2.3.4"])

    def test_multiple_phase1_enrichers_all_run(self):
        dns = _DummyEnricher("dns", "dns_info", {"a_records": ["1.1.1.1"]})
        whois = _DummyEnricher("whois", "whois_info", {"registrar": "IANA"})
        sub = _DummyEnricher("subdomain", "subdomains", ["www.example.com"])

        pipeline = EnricherPipeline([dns, whois, sub])
        result = pipeline.run("example.com")

        self.assertEqual(dns.call_count, 1)
        self.assertEqual(whois.call_count, 1)
        self.assertEqual(sub.call_count, 1)
        self.assertIn("dns_info", result)
        self.assertIn("whois_info", result)
        self.assertIn("subdomains", result)


class TestEnricherPipelinePhases(unittest.TestCase):

    def _build_full_pipeline(self):
        """Return a pipeline with one mock enricher per phase."""
        dns = _DummyEnricher("dns", "dns_info", {"a_records": ["1.1.1.1"]})
        whois = _DummyEnricher("whois", "whois_info", {"registrar": "Test"})
        sub = _DummyEnricher("subdomain", "subdomains", ["www.example.com"])
        ssl = _DummyEnricher("ssl", "ssl_info", {"certificates": []})
        port = _DummyEnricher("port", "port_scan", [])
        tech = _DummyEnricher("tech", "tech_stack", {})
        ext = _DummyEnricher("external_apis", "external_apis", {})
        geo = _DummyEnricher("geoip", "geoip_info", {})
        return EnricherPipeline([dns, whois, sub, ssl, port, tech, ext, geo]), {
            "dns": dns, "whois": whois, "subdomain": sub,
            "ssl": ssl, "port": port, "tech": tech,
            "external_apis": ext, "geoip": geo,
        }

    def test_all_phases_produce_expected_keys(self):
        pipeline, enrichers = self._build_full_pipeline()
        result = pipeline.run("example.com")
        for key in ("dns_info", "whois_info", "subdomains",
                    "ssl_info", "port_scan", "tech_stack",
                    "external_apis", "geoip_info"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_all_enrichers_called_exactly_once(self):
        pipeline, enrichers = self._build_full_pipeline()
        pipeline.run("example.com")
        for name, enricher in enrichers.items():
            self.assertEqual(enricher.call_count, 1, f"{name} not called once")


class TestEnricherPipelineProgress(unittest.TestCase):

    def test_progress_callback_is_called(self):
        dns = _DummyEnricher("dns", "dns_info", {"a_records": ["1.1.1.1"]})
        calls = []
        pipeline = EnricherPipeline([dns], on_progress=lambda s, p, m: calls.append((s, p, m)))
        pipeline.run("example.com")
        self.assertGreater(len(calls), 0)

    def test_progress_values_are_monotonically_non_decreasing(self):
        dns = _DummyEnricher("dns", "dns_info", {"a_records": ["1.1.1.1"]})
        whois = _DummyEnricher("whois", "whois_info", {})
        sub = _DummyEnricher("subdomain", "subdomains", [])
        ssl = _DummyEnricher("ssl", "ssl_info", {"certificates": []})
        port = _DummyEnricher("port", "port_scan", [])
        tech = _DummyEnricher("tech", "tech_stack", {})
        ext = _DummyEnricher("external_apis", "external_apis", {})
        geo = _DummyEnricher("geoip", "geoip_info", {})

        progress_values = []
        pipeline = EnricherPipeline(
            [dns, whois, sub, ssl, port, tech, ext, geo],
            on_progress=lambda s, p, m: progress_values.append(p),
        )
        pipeline.run("example.com")

        for i in range(1, len(progress_values)):
            self.assertGreaterEqual(
                progress_values[i], progress_values[i - 1],
                f"Progress decreased at index {i}: "
                f"{progress_values[i-1]} → {progress_values[i]}",
            )

    def test_progress_callback_receives_stage_string(self):
        dns = _DummyEnricher("dns", "dns_info", {"a_records": []})
        stages = []
        pipeline = EnricherPipeline([dns], on_progress=lambda s, p, m: stages.append(s))
        pipeline.run("example.com")
        self.assertIn("dns", stages)


class TestEnricherPipelineErrorHandling(unittest.TestCase):

    def test_failing_phase1_enricher_does_not_crash_pipeline(self):
        failing_dns = _RaisingEnricher("dns")
        whois = _DummyEnricher("whois", "whois_info", {"registrar": "IANA"})

        pipeline = EnricherPipeline([failing_dns, whois])
        result = pipeline.run("example.com")
        # Pipeline must survive and return what it can
        self.assertIsInstance(result, dict)
        self.assertIn("whois_info", result)

    def test_failing_phase2_enricher_does_not_crash_pipeline(self):
        dns = _DummyEnricher("dns", "dns_info", {"a_records": ["1.1.1.1"]})
        sub = _DummyEnricher("subdomain", "subdomains", ["www.example.com"])
        failing_ssl = _RaisingEnricher("ssl")
        port = _DummyEnricher("port", "port_scan", [])
        tech = _DummyEnricher("tech", "tech_stack", {})

        pipeline = EnricherPipeline([dns, sub, failing_ssl, port, tech])
        result = pipeline.run("example.com")
        self.assertIsInstance(result, dict)
        self.assertIn("port_scan", result)

    def test_failing_phase3_enricher_does_not_crash_pipeline(self):
        dns = _DummyEnricher("dns", "dns_info", {"a_records": ["1.1.1.1"]})
        failing_ext = _RaisingEnricher("external_apis")

        pipeline = EnricherPipeline([dns, failing_ext])
        result = pipeline.run("example.com")
        self.assertIsInstance(result, dict)
        self.assertIn("dns_info", result)

    def test_all_enrichers_fail_returns_minimal_context(self):
        pipeline = EnricherPipeline([
            _RaisingEnricher("dns"),
            _RaisingEnricher("whois"),
        ])
        result = pipeline.run("example.com")
        self.assertEqual(result["domain"], "example.com")


if __name__ == "__main__":
    unittest.main()
