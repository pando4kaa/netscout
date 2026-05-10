"""
Verify each building block of Risk Scoring V3 (factors, enrichment, aggregation).

Uses mocks for EPSS/KEV HTTP clients so tests stay deterministic offline.
"""

import unittest
from unittest.mock import patch

from src.analysis.risk_scoring_v3 import (
    compute_overall_risk,
    compute_risk_v3,
    enrich_group_cves,
    group_alerts,
    score_group,
)
from src.core.models import Alert, RiskLevel


def _likelihood_names(group_result: dict) -> set:
    return {f["name"] for f in group_result["factors"]["likelihood"]}


def _impact_names(group_result: dict) -> set:
    return {f["name"] for f in group_result["factors"]["impact"]}


class TestV3FactorPresence(unittest.TestCase):
    """Every likelihood/impact factor emitted by score_group must stay present."""

    EXPECTED_LIKELIHOOD = {
        "public_exposure",
        "known_vulnerability",
        "exploit_maturity",
        "ease_of_discovery",
        "ease_of_exploit",
        "environment",
        "repeatability",
    }
    EXPECTED_IMPACT = {
        "technical_severity",
        "asset_criticality",
        "cia_impact",
        "reputation_impact",
        "service_role",
        "blast_radius",
    }

    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    @patch("src.analysis.risk_scoring_v3.get_epss_scores", return_value={})
    def test_outdated_tech_has_all_factor_slots(self, _epss, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="test",
                target="https://api.example.com",
                details={
                    "software": "nginx",
                    "version": "1.18.0",
                    "cves": [{"id": "CVE-2022-41741", "cvss": 7.1}],
                },
            )
        ]
        groups = group_alerts(alerts, "example.com")
        enrich_group_cves(groups)
        scored = score_group(groups[0], "example.com")

        self.assertEqual(_likelihood_names(scored), self.EXPECTED_LIKELIHOOD)
        self.assertEqual(_impact_names(scored), self.EXPECTED_IMPACT)
        self.assertEqual(len(scored["factors"]["confidence"]), 1)
        self.assertEqual(scored["factors"]["confidence"][0]["name"], "confidence")


class TestSeverityPaths(unittest.TestCase):
    def test_cvss_used_when_cves_have_cvss(self):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target="https://x.example.com",
                details={"software": "x", "version": "1", "cves": [{"id": "CVE-1", "cvss": 6.5}]},
            )
        ]
        groups = group_alerts(alerts, "example.com")
        scored = score_group(groups[0], "example.com")
        self.assertEqual(scored["severity_source"], "cvss")
        self.assertEqual(scored["severity"], 6.5)

    def test_legacy_when_no_cvss_numeric(self):
        alerts = [
            Alert(
                type="missing_dmarc",
                level=RiskLevel.MEDIUM,
                message="no dmarc",
                target="example.com",
                details={},
            )
        ]
        groups = group_alerts(alerts, "example.com")
        scored = score_group(groups[0], "example.com")
        self.assertEqual(scored["severity_source"], "legacy")
        self.assertEqual(scored["severity"], 5.0)


class TestEpssBranches(unittest.TestCase):
    """EPSS tiers drive exploit_maturity rationale."""

    def _exploit_factor(self, scored):
        for f in scored["factors"]["likelihood"]:
            if f["name"] == "exploit_maturity":
                return f
        raise AssertionError("exploit_maturity missing")

    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    def test_epss_low_branch(self, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target="https://a.example.com",
                details={
                    "software": "nginx",
                    "version": "1.18.0",
                    "cves": [{"id": "CVE-A", "cvss": 7.0}],
                },
            )
        ]
        groups = group_alerts(alerts, "example.com")
        with patch(
            "src.analysis.risk_scoring_v3.get_epss_scores",
            return_value={"CVE-A": {"epss": 0.02, "percentile": 0.5, "date": "2026-05-03"}},
        ):
            enrich_group_cves(groups)
        scored = score_group(groups[0], "example.com")
        self.assertIn("low", self._exploit_factor(scored)["rationale"].lower())

    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    def test_epss_elevated_branch(self, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target="https://a.example.com",
                details={
                    "software": "nginx",
                    "version": "1.18.0",
                    "cves": [{"id": "CVE-B", "cvss": 7.0}],
                },
            )
        ]
        groups = group_alerts(alerts, "example.com")
        with patch(
            "src.analysis.risk_scoring_v3.get_epss_scores",
            return_value={"CVE-B": {"epss": 0.15, "percentile": 0.9, "date": "2026-05-03"}},
        ):
            enrich_group_cves(groups)
        scored = score_group(groups[0], "example.com")
        self.assertIn("elevated", self._exploit_factor(scored)["rationale"].lower())

    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    def test_epss_high_branch(self, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target="https://a.example.com",
                details={
                    "software": "nginx",
                    "version": "1.18.0",
                    "cves": [{"id": "CVE-C", "cvss": 7.0}],
                },
            )
        ]
        groups = group_alerts(alerts, "example.com")
        with patch(
            "src.analysis.risk_scoring_v3.get_epss_scores",
            return_value={"CVE-C": {"epss": 0.55, "percentile": 0.99, "date": "2026-05-03"}},
        ):
            enrich_group_cves(groups)
        scored = score_group(groups[0], "example.com")
        self.assertIn("high", self._exploit_factor(scored)["rationale"].lower())


class TestKevOverrides(unittest.TestCase):
    @patch(
        "src.analysis.risk_scoring_v3.get_kev_entries",
        return_value={
            "CVE-KEV-1": {"cve": "CVE-KEV-1", "product": "Test"},
        },
    )
    @patch(
        "src.analysis.risk_scoring_v3.get_epss_scores",
        return_value={"CVE-KEV-1": {"epss": 0.001, "percentile": 0.1, "date": "2026-05-03"}},
    )
    def test_kev_sets_flag_and_high_exploit_maturity(self, _epss, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.HIGH,
                message="m",
                target="https://api.example.com",
                details={
                    "software": "app",
                    "version": "1",
                    "cves": [{"id": "CVE-KEV-1", "cvss": 8.0}],
                },
            )
        ]
        groups = group_alerts(alerts, "example.com")
        enrich_group_cves(groups)
        self.assertTrue(groups[0]["cves"][0].get("kev"))
        scored = score_group(groups[0], "example.com")
        for f in scored["factors"]["likelihood"]:
            if f["name"] == "exploit_maturity":
                self.assertIn("KEV", f["rationale"])
                break
        else:
            self.fail("exploit_maturity not found")
        self.assertEqual(scored["confidence"], "high")


class TestEnrichGroupCves(unittest.TestCase):
    def test_enrich_merges_epss_and_kev_into_cve_dict(self):
        groups = [
            {
                "group_id": "x",
                "type": "outdated_tech",
                "alerts": [],
                "targets": ["a.example.com"],
                "cves": [{"id": "CVE-2021-44228", "cvss": 10.0}],
                "details": {},
            }
        ]
        with patch(
            "src.analysis.risk_scoring_v3.get_epss_scores",
            return_value={"CVE-2021-44228": {"epss": 0.9, "percentile": 0.99, "date": "2026-05-03"}},
        ), patch(
            "src.analysis.risk_scoring_v3.get_kev_entries",
            return_value={
                "CVE-2021-44228": {"cve": "CVE-2021-44228", "product": "Log4j2"},
            },
        ):
            enrich_group_cves(groups)
        cve = groups[0]["cves"][0]
        self.assertEqual(cve["epss"], 0.9)
        self.assertTrue(cve.get("kev"))
        self.assertIn("kev_details", cve)


class TestExposureNonlinear(unittest.TestCase):
    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    @patch("src.analysis.risk_scoring_v3.get_epss_scores", return_value={})
    def test_multiplier_increases_with_asset_count(self, _epss, _kev):
        base = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target=f"https://h{i}.example.com",
                details={"software": "nginx", "version": "1.18.0", "cves": [{"id": "CVE-X", "cvss": 7.0}]},
            )
            for i in range(5)
        ]
        g5 = group_alerts(base, "example.com")
        enrich_group_cves(g5)
        s5 = score_group(g5[0], "example.com")

        many = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target=f"https://h{i}.example.com",
                details={"software": "nginx", "version": "1.18.0", "cves": [{"id": "CVE-X", "cvss": 7.0}]},
            )
            for i in range(25)
        ]
        g25 = group_alerts(many, "example.com")
        enrich_group_cves(g25)
        s25 = score_group(g25[0], "example.com")

        self.assertGreater(s25["exposure_multiplier"], s5["exposure_multiplier"])
        self.assertGreater(s25["exposure_score"], s5["exposure_score"])


class TestOverallAggregation(unittest.TestCase):
    def test_weighted_top_groups_formula(self):
        risk_groups = [
            {"risk_score": 50.0, "severity": 7.0, "exposure_score": 8.0, "confidence": "medium"},
            {"risk_score": 10.0, "severity": 1.0, "exposure_score": 2.0, "confidence": "high"},
            {"risk_score": 5.0, "severity": 5.0, "exposure_score": 2.0, "confidence": "low"},
        ]
        summary = compute_overall_risk(
            [
                {**risk_groups[0], "type": "a", "title": "t1", "likelihood": 1, "impact": 1, "group_id": "1"},
                {**risk_groups[1], "type": "b", "title": "t2", "likelihood": 1, "impact": 1, "group_id": "2"},
                {**risk_groups[2], "type": "c", "title": "t3", "likelihood": 1, "impact": 1, "group_id": "3"},
            ]
        )
        expected = 50.0 + 0.35 * 10.0 + 0.20 * 5.0
        self.assertEqual(summary["risk_overall"], round(expected, 2))


class TestDistinctGroupTypes(unittest.TestCase):
    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    @patch("src.analysis.risk_scoring_v3.get_epss_scores", return_value={})
    def test_dmarc_headers_port_produce_separate_groups(self, _epss, _kev):
        alerts = [
            Alert(
                type="missing_dmarc",
                level=RiskLevel.MEDIUM,
                message="DMARC missing",
                target="example.com",
                details={},
            ),
            Alert(
                type="missing_security_headers",
                level=RiskLevel.LOW,
                message="Missing headers",
                target="https://example.com",
                details={"missing": ["HSTS", "X-Frame-Options"]},
            ),
            Alert(
                type="open_port",
                level=RiskLevel.LOW,
                message="SSH",
                target="192.0.2.1",
                details={"port": 22, "service": "SSH"},
            ),
        ]
        summary = compute_risk_v3(alerts, "example.com")
        types = {g["type"] for g in summary["risk_groups"]}
        self.assertEqual(types, {"missing_dmarc", "missing_security_headers", "open_port"})


class TestEnvironmentRationale(unittest.TestCase):
    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    @patch("src.analysis.risk_scoring_v3.get_epss_scores", return_value={})
    def test_environment_mix_of_stage_and_prod(self, _epss, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target="https://accounts.smart-stage.example.com",
                details={"software": "nginx", "version": "1.18.0", "cves": [{"id": "CVE-X", "cvss": 7.0}]},
            ),
            Alert(
                type="outdated_tech",
                level=RiskLevel.MEDIUM,
                message="m",
                target="https://www.example.com",
                details={"software": "nginx", "version": "1.18.0", "cves": [{"id": "CVE-X", "cvss": 7.0}]},
            ),
        ]
        summary = compute_risk_v3(alerts, "example.com")
        env_factor = next(
            f for f in summary["risk_groups"][0]["factors"]["likelihood"] if f["name"] == "environment"
        )
        self.assertIn("mix", env_factor["rationale"].lower())


if __name__ == "__main__":
    unittest.main()
