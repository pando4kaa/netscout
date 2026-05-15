"""
Tests for notifications API endpoints:
  GET   /api/notifications
  GET   /api/notifications/unread-count
  PATCH /api/notifications/{id}/read
  PATCH /api/notifications/read-all
  GET   /api/notifications/{id}/report
  GET   /api/notifications/{id}/export/json
"""

import pytest
from unittest.mock import patch

_NOTIF_EP = "app.api.endpoints.notifications"

_SAMPLE_NOTIFICATION = {
    "id": 1,
    "domain": "example.com",
    "scan_id": "scan_new001",
    "scan_id_prev": "scan_old001",
    "type": "subdomain_added",
    "title": "New subdomains: +3",
    "message": "Added 3 subdomain(s): www, api, mail...",
    "details": {"added": ["www.example.com", "api.example.com", "mail.example.com"]},
    "severity": "info",
    "read_at": None,
    "created_at": "2026-05-01T10:00:00",
}


def _patch_notif(method: str, **kwargs):
    return patch(f"{_NOTIF_EP}.{method}", **kwargs)


# ---------------------------------------------------------------------------
# List notifications
# ---------------------------------------------------------------------------

class TestListNotifications:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 401

    def test_list_empty(self, client, auth_headers):
        with (
            _patch_notif("list_notifications", return_value=[]),
            _patch_notif("get_unread_count", return_value=0),
        ):
            resp = client.get("/api/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    def test_list_with_items(self, client, auth_headers):
        with (
            _patch_notif("list_notifications", return_value=[_SAMPLE_NOTIFICATION]),
            _patch_notif("get_unread_count", return_value=1),
        ):
            resp = client.get("/api/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1
        assert data["notifications"][0]["domain"] == "example.com"

    def test_list_unread_only_filter(self, client, auth_headers):
        with (
            _patch_notif("list_notifications", return_value=[_SAMPLE_NOTIFICATION]),
            _patch_notif("get_unread_count", return_value=1),
        ):
            resp = client.get("/api/notifications?unread_only=true",
                              headers=auth_headers)
        assert resp.status_code == 200

    def test_list_domain_filter(self, client, auth_headers):
        with (
            _patch_notif("list_notifications", return_value=[_SAMPLE_NOTIFICATION]),
            _patch_notif("get_unread_count", return_value=1),
        ):
            resp = client.get("/api/notifications?domain=example.com",
                              headers=auth_headers)
        assert resp.status_code == 200

    def test_list_invalid_limit(self, client, auth_headers):
        resp = client.get("/api/notifications?limit=999", headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Unread count
# ---------------------------------------------------------------------------

class TestUnreadCount:
    def test_unread_count_requires_auth(self, client):
        resp = client.get("/api/notifications/unread-count")
        assert resp.status_code == 401

    def test_unread_count_zero(self, client, auth_headers):
        with _patch_notif("get_unread_count", return_value=0):
            resp = client.get("/api/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_unread_count_nonzero(self, client, auth_headers):
        with _patch_notif("get_unread_count", return_value=5):
            resp = client.get("/api/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 5


# ---------------------------------------------------------------------------
# Mark single notification as read
# ---------------------------------------------------------------------------

class TestMarkRead:
    def test_mark_read_requires_auth(self, client):
        resp = client.patch("/api/notifications/1/read")
        assert resp.status_code == 401

    def test_mark_read_success(self, client, auth_headers):
        with _patch_notif("mark_read", return_value=True):
            resp = client.patch("/api/notifications/1/read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_mark_read_not_found(self, client, auth_headers):
        with _patch_notif("mark_read", return_value=False):
            resp = client.patch("/api/notifications/99999/read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# Mark all read
# ---------------------------------------------------------------------------

class TestMarkAllRead:
    def test_mark_all_requires_auth(self, client):
        resp = client.patch("/api/notifications/read-all")
        assert resp.status_code == 401

    def test_mark_all_success(self, client, auth_headers):
        with _patch_notif("mark_all_read", return_value=3):
            resp = client.patch("/api/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["updated"] == 3

    def test_mark_all_no_unread(self, client, auth_headers):
        with _patch_notif("mark_all_read", return_value=0):
            resp = client.patch("/api/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_SAMPLE_REPORT = {
    "notification": {
        "id": 1,
        "domain": "example.com",
        "type": "subdomain_added",
        "title": "New subdomains: +3",
        "message": "Added 3 subdomain(s).",
        "created_at": "2026-05-01T10:00:00",
    },
    "comparison": {
        "summary": {"risk_1": 20, "risk_2": 35, "risk_delta": 15},
        "subdomains": {"only_in_2": ["api.example.com"], "only_in_1": []},
    },
}


class TestNotificationReport:
    def test_report_requires_auth(self, client):
        resp = client.get("/api/notifications/1/report")
        assert resp.status_code == 401

    def test_report_success(self, client, auth_headers):
        with _patch_notif("get_notification_report", return_value=_SAMPLE_REPORT):
            resp = client.get("/api/notifications/1/report", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "notification" in data
        assert "comparison" in data
        assert data["notification"]["domain"] == "example.com"

    def test_report_not_found(self, client, auth_headers):
        with _patch_notif("get_notification_report", return_value=None):
            resp = client.get("/api/notifications/99999/report", headers=auth_headers)
        assert resp.status_code == 200
        assert "error" in resp.json()


# ---------------------------------------------------------------------------
# Export notification report as JSON
# ---------------------------------------------------------------------------

class TestExportNotificationReport:
    def test_export_requires_auth(self, client):
        resp = client.get("/api/notifications/1/export/json")
        assert resp.status_code == 401

    def test_export_success(self, client, auth_headers):
        with _patch_notif("get_notification_report", return_value=_SAMPLE_REPORT):
            resp = client.get("/api/notifications/1/export/json", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        assert "Content-Disposition" in resp.headers
        assert "attachment" in resp.headers["Content-Disposition"]
        data = resp.json()
        assert "notification" in data

    def test_export_not_found(self, client, auth_headers):
        with _patch_notif("get_notification_report", return_value=None):
            resp = client.get("/api/notifications/99999/export/json",
                              headers=auth_headers)
        assert resp.status_code == 200
        assert "error" in resp.json()
