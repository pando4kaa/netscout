"""
Tests for grouped OWASP-adapted risk scoring.
"""

import unittest
from unittest.mock import patch

from src.analysis.risk_scoring_v3 import compute_risk_v3, group_alerts
from src.core.models import Alert, RiskLevel


def outdated_nginx_alert(target: str) -> Alert:
    return Alert(
        type="outdated_tech",
        level=RiskLevel.MEDIUM,
        message=f"Outdated nginx 1.18.0 on {target}: CVE-2022-41741, CVE-2022-41742",
        target=target,
        details={
            "server": "nginx/1.18.0 (Ubuntu)",
            "software": "nginx",
            "version": "1.18.0",
            "cves": [
                {"id": "CVE-2022-41741", "cvss": 7.0},
                {"id": "CVE-2022-41742", "cvss": 7.1},
            ],
            "cvss_max": 7.1,
        },
    )


class TestRiskScoringV3(unittest.TestCase):
    def test_repeated_identical_findings_are_grouped(self):
        alerts = [outdated_nginx_alert(f"https://app{i}.smart-stage.example.com") for i in range(20)]

        groups = group_alerts(alerts, "example.com")

        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["targets"]), 20)

    @patch("src.analysis.risk_scoring_v3.get_kev_entries", return_value={})
    @patch(
        "src.analysis.risk_scoring_v3.get_epss_scores",
        return_value={
            "CVE-2022-41741": {"epss": 0.01, "percentile": 0.2, "date": "2026-05-02"},
            "CVE-2022-41742": {"epss": 0.02, "percentile": 0.3, "date": "2026-05-02"},
        },
    )
    def test_repeated_nginx_findings_do_not_become_critical(self, _epss, _kev):
        alerts = [outdated_nginx_alert(f"https://app{i}.smart-stage.example.com") for i in range(20)]

        summary = compute_risk_v3(alerts, "example.com")

        self.assertEqual(len(summary["risk_groups"]), 1)
        self.assertEqual(summary["risk_groups"][0]["affected_assets"], 20)
        self.assertEqual(summary["max_severity"], 7.1)
        self.assertLess(summary["risk_overall"], 75)
        self.assertNotEqual(summary["risk_level"], "CRITICAL")

    @patch(
        "src.analysis.risk_scoring_v3.get_kev_entries",
        return_value={
            "CVE-2024-0001": {
                "cve": "CVE-2024-0001",
                "vulnerability_name": "Example exploited vulnerability",
            }
        },
    )
    @patch(
        "src.analysis.risk_scoring_v3.get_epss_scores",
        return_value={"CVE-2024-0001": {"epss": 0.72, "percentile": 0.99, "date": "2026-05-02"}},
    )
    def test_kev_on_critical_service_is_high_priority(self, _epss, _kev):
        alerts = [
            Alert(
                type="outdated_tech",
                level=RiskLevel.HIGH,
                message="Outdated auth service with exploited CVE",
                target="https://auth.example.com",
                details={
                    "server": "example/1.0",
                    "software": "example",
                    "version": "1.0",
                    "cves": [{"id": "CVE-2024-0001", "cvss": 9.8}],
                    "cvss_max": 9.8,
                },
            )
        ]

        summary = compute_risk_v3(alerts, "example.com")

        self.assertGreaterEqual(summary["risk_overall"], 50)
        self.assertIn(summary["risk_level"], {"HIGH", "CRITICAL"})
        self.assertEqual(summary["confidence"], "high")


if __name__ == "__main__":
    unittest.main()
