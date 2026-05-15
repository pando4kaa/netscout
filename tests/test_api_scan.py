"""
Tests for scan API endpoints:
  GET  /
  GET  /health
  GET  /api/debug/neo4j
  GET  /api/debug/keys
  POST /api/scan
  GET  /api/scan/history
  GET  /api/scan/{id}
  GET  /api/scan/{id}/export/json
  GET  /api/scan/{id}/export/csv
  GET  /api/scan/compare
  GET  /api/schedules
  POST /api/schedules
  PATCH /api/schedules/{id}
  DELETE /api/schedules/{id}
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


def _make_scan_result(domain: str = "example.com"):
    """Return a minimal ScanResult-like object for mocking run_scan."""
    from src.core.models import ScanResult, ScanSummary
    result = ScanResult(
        target_domain=domain,
        scan_date=datetime.utcnow(),
        subdomains=["www.example.com"],
        summary=ScanSummary(total_subdomains=1, risk_score=10),
    )
    return result


def _seed_scan(db, scan_id: str, domain: str, user_id: int, results_dict: dict):
    from app.db.models import ScanRecord
    rec = ScanRecord(
        scan_id=scan_id,
        domain=domain,
        results=json.dumps(results_dict),
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(rec)
    db.commit()
    return rec


# ---------------------------------------------------------------------------
# Root / Health
# ---------------------------------------------------------------------------

class TestRootAndHealth:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "NetScout API"
        assert "version" in body

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------

class TestDebugEndpoints:
    def test_debug_neo4j_not_configured(self, client):
        resp = client.get("/api/debug/neo4j")
        assert resp.status_code == 200
        assert "neo4j" in resp.json()

    def test_debug_keys_requires_auth(self, client):
        resp = client.get("/api/debug/keys")
        assert resp.status_code == 401

    def test_debug_keys_with_auth(self, client, auth_headers):
        resp = client.get("/api/debug/keys", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "virustotal_api_key" in data


# ---------------------------------------------------------------------------
# POST /api/scan
# ---------------------------------------------------------------------------

class TestPostScan:
    def test_scan_anonymous(self, client):
        mock_result = _make_scan_result()
        with patch("app.api.endpoints.scan.run_scan",
                   return_value=("scan_abc123", mock_result)):
            resp = client.post("/api/scan", json={"domain": "example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["scan_id"] == "scan_abc123"
        assert data["saved"] is False
        assert data["results"]["target_domain"] == "example.com"

    def test_scan_authenticated(self, client, auth_headers):
        mock_result = _make_scan_result()
        with patch("app.api.endpoints.scan.run_scan",
                   return_value=("scan_auth456", mock_result)):
            resp = client.post("/api/scan", json={"domain": "example.com"},
                               headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["saved"] is True

    def test_scan_missing_domain(self, client):
        resp = client.post("/api/scan", json={})
        assert resp.status_code == 422

    def test_scan_service_error_returns_failure(self, client):
        with patch("app.api.endpoints.scan.run_scan",
                   side_effect=ValueError("Invalid domain")):
            resp = client.post("/api/scan", json={"domain": "bad..domain"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "error" in data


# ---------------------------------------------------------------------------
# GET /api/scan/history
# ---------------------------------------------------------------------------

class TestScanHistory:
    def test_history_empty_anonymous(self, client):
        resp = client.get("/api/scan/history")
        assert resp.status_code == 200
        assert resp.json()["scans"] == []

    def test_history_authenticated_with_records(self, client, db, auth_headers, test_user):
        results = {"target_domain": "example.com", "summary": {"risk_score": 15}}
        _seed_scan(db, "scan_h001", "example.com", test_user.id, results)

        resp = client.get("/api/scan/history", headers=auth_headers)
        assert resp.status_code == 200
        scans = resp.json()["scans"]
        assert len(scans) >= 1
        assert any(s["domain"] == "example.com" for s in scans)

    def test_history_limit_offset(self, client, auth_headers):
        resp = client.get("/api/scan/history?limit=5&offset=0", headers=auth_headers)
        assert resp.status_code == 200
        assert "scans" in resp.json()

    def test_history_domain_filter(self, client, auth_headers):
        resp = client.get("/api/scan/history?domain=example.com", headers=auth_headers)
        assert resp.status_code == 200

    def test_history_invalid_limit(self, client):
        resp = client.get("/api/scan/history?limit=999")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/scan/{scan_id}
# ---------------------------------------------------------------------------

class TestGetScan:
    def test_get_scan_not_found(self, client):
        resp = client.get("/api/scan/nonexistent_id")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"
        assert data["results"] is None

    def test_get_scan_found(self, client, db, test_user):
        results = {"target_domain": "example.com", "summary": {"risk_score": 20}}
        _seed_scan(db, "scan_get001", "example.com", test_user.id, results)

        resp = client.get("/api/scan/scan_get001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["results"]["target_domain"] == "example.com"


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

class TestExportScan:
    def _seed(self, db, test_user):
        results = {
            "target_domain": "example.com",
            "subdomains": ["www.example.com", "api.example.com"],
            "dns_info": {"a_records": ["93.184.216.34"], "aaaa_records": []},
            "summary": {"risk_score": 10},
        }
        _seed_scan(db, "scan_exp001", "example.com", test_user.id, results)

    def test_export_json(self, client, db, test_user):
        self._seed(db, test_user)
        resp = client.get("/api/scan/scan_exp001/export/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_domain"] == "example.com"

    def test_export_json_not_found(self, client):
        resp = client.get("/api/scan/doesnotexist/export/json")
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_export_csv(self, client, db, test_user):
        self._seed(db, test_user)
        resp = client.get("/api/scan/scan_exp001/export/csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        body = resp.text
        assert "example.com" in body
        assert "subdomain" in body

    def test_export_csv_not_found(self, client):
        resp = client.get("/api/scan/doesnotexist/export/csv")
        assert resp.status_code == 200
        assert "error" in resp.json()


# ---------------------------------------------------------------------------
# GET /api/scan/compare
# ---------------------------------------------------------------------------

class TestCompareScan:
    def _seed_two(self, db, test_user):
        for sid, risk in [("scan_c1", 20), ("scan_c2", 35)]:
            r = {"target_domain": "example.com", "subdomains": [],
                 "summary": {"risk_score": risk}}
            _seed_scan(db, sid, "example.com", test_user.id, r)

    def test_compare_same_domain(self, client, db, test_user):
        self._seed_two(db, test_user)
        with patch(
            "app.api.endpoints.scan.compare_scans",
            return_value=({"summary": {"risk_delta": 15}}, None),
        ):
            resp = client.get("/api/scan/compare?scan_id_1=scan_c1&scan_id_2=scan_c2")
        assert resp.status_code == 200
        data = resp.json()
        assert "comparison" in data

    def test_compare_not_found(self, client):
        resp = client.get("/api/scan/compare?scan_id_1=nope1&scan_id_2=nope2")
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_compare_missing_params(self, client):
        resp = client.get("/api/scan/compare?scan_id_1=scan_c1")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

class TestSchedules:
    def test_list_schedules_requires_auth(self, client):
        resp = client.get("/api/schedules")
        assert resp.status_code == 401

    def test_list_schedules_empty(self, client, auth_headers):
        resp = client.get("/api/schedules", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["schedules"] == []

    def test_create_schedule(self, client, auth_headers):
        resp = client.post("/api/schedules",
                           json={"domain": "example.com", "interval_hours": 12},
                           headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["schedule"]["domain"] == "example.com"
        assert data["schedule"]["interval_hours"] == 12

    def test_create_schedule_requires_auth(self, client):
        resp = client.post("/api/schedules",
                           json={"domain": "example.com", "interval_hours": 24})
        assert resp.status_code == 401

    def test_update_schedule(self, client, auth_headers):
        create = client.post("/api/schedules",
                             json={"domain": "example.com", "interval_hours": 24},
                             headers=auth_headers)
        assert create.status_code == 200
        sched_id = create.json()["schedule"]["id"]

        resp = client.patch(f"/api/schedules/{sched_id}",
                            json={"interval_hours": 48},
                            headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["schedule"]["interval_hours"] == 48

    def test_update_schedule_empty_body(self, client, auth_headers):
        resp = client.patch("/api/schedules/1", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_delete_schedule(self, client, auth_headers):
        create = client.post("/api/schedules",
                             json={"domain": "example.com", "interval_hours": 24},
                             headers=auth_headers)
        assert create.status_code == 200
        sched_id = create.json()["schedule"]["id"]

        resp = client.delete(f"/api/schedules/{sched_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_schedule_not_found(self, client, auth_headers):
        resp = client.delete("/api/schedules/99999", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is False
