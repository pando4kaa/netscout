"""
Tests for investigation API endpoints.

Neo4j and investigation_service are fully mocked so no graph DB is needed.
All endpoints that call `neo4j_required` dependency or investigation_service
functions receive controlled responses via patch.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock

_FAKE_INV_ID = str(uuid.uuid4())
_FAKE_INV = {
    "id": _FAKE_INV_ID,
    "name": "Test Investigation",
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
    "graph": {"nodes": [], "edges": []},
}

_NEO4J_OK = "app.services.neo4j_service.is_neo4j_available"
_INV_EP = "app.api.endpoints.investigations"


@pytest.fixture(autouse=True)
def _neo4j_available():
    with patch(_NEO4J_OK, return_value=True), patch(
        "app.services.investigation_service.is_neo4j_available", return_value=True
    ):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_inv(method: str, return_value=None, side_effect=None):
    """Patch endpoint module symbol with a plain callable (not MagicMock).

    MagicMock is truthy, so ``if not inv`` in routes never treats it as missing
    and FastAPI JSON-encodes the mock as ``{}`` with status 200.
    """
    target = f"{_INV_EP}.{method}"
    if side_effect is not None:
        return patch(target, side_effect=side_effect)

    def _fake(*_args, **_kwargs):
        return return_value

    return patch(target, new=_fake)


# ---------------------------------------------------------------------------
# List investigations
# ---------------------------------------------------------------------------

class TestListInvestigations:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/investigations")
        assert resp.status_code == 401

    def test_list_returns_empty(self, client, auth_headers):
        with _patch_inv("list_investigations", return_value=[]):
            resp = client.get("/api/investigations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["investigations"] == []

    def test_list_returns_items(self, client, auth_headers):
        items = [{"id": _FAKE_INV_ID, "name": "Inv1",
                  "created_at": "2026-01-01T00:00:00",
                  "updated_at": "2026-01-01T00:00:00"}]
        with _patch_inv("list_investigations", return_value=items):
            resp = client.get("/api/investigations", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["investigations"]) == 1


# ---------------------------------------------------------------------------
# Create investigation
# ---------------------------------------------------------------------------

class TestCreateInvestigation:
    def test_create_requires_auth(self, client):
        resp = client.post("/api/investigations", json={"name": "My Inv"})
        assert resp.status_code == 401

    def test_create_success(self, client, auth_headers):
        with _patch_inv("create_investigation", return_value=_FAKE_INV):
            resp = client.post("/api/investigations",
                               json={"name": "My Inv"},
                               headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == _FAKE_INV_ID
        assert data["name"] == "Test Investigation"

    def test_create_default_name(self, client, auth_headers):
        inv = {**_FAKE_INV, "name": "New Investigation"}
        with _patch_inv("create_investigation", return_value=inv):
            resp = client.post("/api/investigations", json={}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Investigation"


# ---------------------------------------------------------------------------
# Get investigation by ID
# ---------------------------------------------------------------------------

class TestGetInvestigation:
    def test_get_requires_auth(self, client):
        resp = client.get(f"/api/investigations/{_FAKE_INV_ID}")
        assert resp.status_code == 401

    def test_get_not_found(self, client, auth_headers):
        with _patch_inv("get_investigation", return_value=None):
            resp = client.get(f"/api/investigations/{_FAKE_INV_ID}",
                              headers=auth_headers)
        assert resp.status_code == 404

    def test_get_success(self, client, auth_headers):
        with _patch_inv("get_investigation", return_value=_FAKE_INV):
            resp = client.get(f"/api/investigations/{_FAKE_INV_ID}",
                              headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == _FAKE_INV_ID


# ---------------------------------------------------------------------------
# Update investigation name
# ---------------------------------------------------------------------------

class TestPatchInvestigation:
    def test_patch_requires_auth(self, client):
        resp = client.patch(f"/api/investigations/{_FAKE_INV_ID}",
                            json={"name": "New Name"})
        assert resp.status_code == 401

    def test_patch_not_found(self, client, auth_headers):
        with _patch_inv("update_investigation", return_value=None):
            resp = client.patch(f"/api/investigations/{_FAKE_INV_ID}",
                                json={"name": "New Name"},
                                headers=auth_headers)
        assert resp.status_code == 404

    def test_patch_success(self, client, auth_headers):
        updated = {**_FAKE_INV, "name": "Renamed"}
        with _patch_inv("update_investigation", return_value=updated):
            resp = client.patch(f"/api/investigations/{_FAKE_INV_ID}",
                                json={"name": "Renamed"},
                                headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"


# ---------------------------------------------------------------------------
# Delete investigation
# ---------------------------------------------------------------------------

class TestDeleteInvestigation:
    def test_delete_not_found(self, client, auth_headers):
        with _patch_inv("delete_investigation", return_value=False):
            resp = client.delete(f"/api/investigations/{_FAKE_INV_ID}",
                                 headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_success(self, client, auth_headers):
        with _patch_inv("delete_investigation", return_value=True):
            resp = client.delete(f"/api/investigations/{_FAKE_INV_ID}",
                                 headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# Add entity
# ---------------------------------------------------------------------------

class TestAddEntity:
    def test_add_entity_success(self, client, auth_headers):
        node = {"id": "domain_example.com", "type": "domain", "value": "example.com"}
        with _patch_inv("add_entity", return_value=node):
            resp = client.post(
                f"/api/investigations/{_FAKE_INV_ID}/entities",
                json={"entity_type": "domain", "entity_value": "example.com"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["type"] == "domain"

    def test_add_entity_not_found(self, client, auth_headers):
        with _patch_inv("add_entity", return_value=None):
            resp = client.post(
                f"/api/investigations/{_FAKE_INV_ID}/entities",
                json={"entity_type": "ip", "entity_value": "1.2.3.4"},
                headers=auth_headers,
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update entity metadata
# ---------------------------------------------------------------------------

class TestUpdateEntityMetadata:
    def test_patch_entity_success(self, client, auth_headers):
        with _patch_inv("update_entity_metadata", return_value=True):
            resp = client.patch(
                f"/api/investigations/{_FAKE_INV_ID}/entities",
                json={"cy_id": "domain_example.com",
                      "notes": "important", "tags": ["prod"]},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_patch_entity_not_found(self, client, auth_headers):
        with _patch_inv("update_entity_metadata", return_value=False):
            resp = client.patch(
                f"/api/investigations/{_FAKE_INV_ID}/entities",
                json={"cy_id": "missing_node"},
                headers=auth_headers,
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Run enricher (sync fallback — no Celery)
# ---------------------------------------------------------------------------

class TestRunEnricher:
    def test_run_enricher_sync_fallback(self, client, auth_headers):
        svc_result = {"success": True, "new_nodes": [], "new_edges": []}
        mock_task = MagicMock()
        mock_task.delay.side_effect = Exception("Celery unavailable")
        with (
            patch("app.tasks.investigation_tasks.run_enricher_task", mock_task),
            _patch_inv("run_enricher", return_value=svc_result),
        ):
            resp = client.post(
                f"/api/investigations/{_FAKE_INV_ID}/run-enricher",
                json={"entity_type": "domain",
                      "entity_value": "example.com",
                      "enricher_name": "dns"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_run_enricher_requires_auth(self, client):
        resp = client.post(
            f"/api/investigations/{_FAKE_INV_ID}/run-enricher",
            json={"entity_type": "domain",
                  "entity_value": "example.com",
                  "enricher_name": "dns"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Share link
# ---------------------------------------------------------------------------

class TestShareLink:
    def test_create_share_link(self, client, auth_headers):
        share = {"share_token": "abc-token", "share_url": "/investigations/shared/abc-token"}
        with _patch_inv("create_share_link", return_value=share):
            resp = client.post(
                f"/api/investigations/{_FAKE_INV_ID}/share",
                json={"expires_days": 7},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert "share_token" in resp.json()

    def test_create_share_link_not_found(self, client, auth_headers):
        with _patch_inv("create_share_link", return_value=None):
            resp = client.post(
                f"/api/investigations/{_FAKE_INV_ID}/share",
                json={"expires_days": 7},
                headers=auth_headers,
            )
        assert resp.status_code == 404

    def test_get_shared_investigation(self, client):
        shared = {**_FAKE_INV, "read_only": True}
        with _patch_inv("get_investigation_by_share_token", return_value=shared):
            resp = client.get("/api/investigations/shared/abc-token")
        assert resp.status_code == 200
        assert resp.json()["read_only"] is True

    def test_get_shared_investigation_not_found(self, client):
        with _patch_inv("get_investigation_by_share_token", return_value=None):
            resp = client.get("/api/investigations/shared/bad-token")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestExportInvestigation:
    _inv_with_graph = {
        **_FAKE_INV,
        "graph": {
            "nodes": [{"data": {"id": "domain_example.com", "label": "example.com"}}],
            "edges": [{"data": {"source": "domain_example.com",
                                "target": "ip_93.184.216.34"}}],
        },
    }

    def test_export_json(self, client, auth_headers):
        with _patch_inv("get_investigation", return_value=self._inv_with_graph):
            resp = client.get(f"/api/investigations/{_FAKE_INV_ID}/export/json",
                              headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "graph" in data

    def test_export_csv(self, client, auth_headers):
        with _patch_inv("get_investigation", return_value=self._inv_with_graph):
            resp = client.get(f"/api/investigations/{_FAKE_INV_ID}/export/csv",
                              headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        body = resp.text
        assert "node" in body
        assert "edge" in body

    def test_export_json_not_found(self, client, auth_headers):
        with _patch_inv("get_investigation", return_value=None):
            resp = client.get(f"/api/investigations/{_FAKE_INV_ID}/export/json",
                              headers=auth_headers)
        assert resp.status_code == 404
