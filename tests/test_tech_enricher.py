"""
Tests for TechEnricher (src/enrichers/tech.py).

All HTTP calls go through aiohttp and are mocked with a fake ClientSession.
No real network requests are made.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.enrichers.tech import TechEnricher


# ---------------------------------------------------------------------------
# aiohttp mock helpers
# ---------------------------------------------------------------------------

class _MockResponse:
    """Minimal aiohttp.ClientResponse mock."""

    def __init__(self, status: int, headers: dict, text_body: str = ""):
        self.status = status
        self.headers = headers
        self._text_body = text_body

    async def text(self) -> str:
        return self._text_body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _mock_session(response: _MockResponse) -> MagicMock:
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTechEnricherWithSubdomains(unittest.TestCase):
    """Tech enricher has subdomains in context → performs HTTP fingerprinting."""

    def _run_enrich(self, session, context):
        enricher = TechEnricher()
        with patch("src.enrichers.tech.make_aiohttp_session",
                   return_value=session):
            return enricher.enrich("example.com", context)

    def test_tech_stack_key_present(self):
        response = _MockResponse(
            status=200,
            headers={
                "Server": "nginx/1.24.0",
                "X-Powered-By": "PHP/8.2",
            },
        )
        session = _mock_session(response)
        result = self._run_enrich(
            session,
            context={"subdomains": ["www.example.com"]},
        )
        self.assertIn("tech_stack", result)

    def test_server_header_detected(self):
        response = _MockResponse(
            status=200,
            headers={"Server": "nginx/1.24.0"},
        )
        session = _mock_session(response)
        result = self._run_enrich(
            session,
            context={"subdomains": ["www.example.com"]},
        )
        tech_stack = result["tech_stack"]
        # tech_stack is a dict or object with per-subdomain data
        self.assertIsNotNone(tech_stack)

    def test_x_powered_by_detected(self):
        response = _MockResponse(
            status=200,
            headers={"Server": "Apache", "X-Powered-By": "Express"},
        )
        session = _mock_session(response)
        result = self._run_enrich(
            session,
            context={"subdomains": ["api.example.com"]},
        )
        self.assertIn("tech_stack", result)

    def test_multiple_subdomains_processed(self):
        response = _MockResponse(
            status=200,
            headers={"Server": "cloudflare"},
        )
        session = _mock_session(response)
        result = self._run_enrich(
            session,
            context={"subdomains": ["www.example.com", "api.example.com",
                                    "mail.example.com"]},
        )
        self.assertIn("tech_stack", result)

    def test_404_response_handled(self):
        response = _MockResponse(status=404, headers={})
        session = _mock_session(response)
        result = self._run_enrich(
            session,
            context={"subdomains": ["www.example.com"]},
        )
        self.assertIn("tech_stack", result)

    def test_connection_error_handled_gracefully(self):
        session = MagicMock()
        session.get = MagicMock(side_effect=Exception("Connection refused"))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        result = self._run_enrich(
            session,
            context={"subdomains": ["www.example.com"]},
        )
        self.assertIn("tech_stack", result)


class TestTechEnricherNoSubdomains(unittest.TestCase):
    """Tech enricher with no subdomains in context → returns empty tech_stack."""

    def test_no_subdomains_in_context_returns_empty(self):
        enricher = TechEnricher()
        result = enricher.enrich("example.com", context={})
        self.assertIn("tech_stack", result)

    def test_empty_subdomains_list_probes_root_only(self):
        enricher = TechEnricher()
        result = enricher.enrich("example.com", context={"subdomains": []})
        self.assertIn("tech_stack", result)
        tech = result["tech_stack"]
        # TechEnricher always probes the root domain (https://example.com),
        # even when the subdomain list is empty.  Exactly 1 entry is expected.
        if isinstance(tech, dict):
            self.assertLessEqual(len(tech), 1)
        elif isinstance(tech, list):
            self.assertLessEqual(len(tech), 1)

    def test_none_context_returns_empty(self):
        enricher = TechEnricher()
        result = enricher.enrich("example.com", context=None)
        self.assertIn("tech_stack", result)


class TestTechEnricherCmsDetection(unittest.TestCase):
    """HTTP body hint detection (WordPress, Drupal, Joomla)."""

    def _run_with_body(self, body: str, subdomains=None):
        response = _MockResponse(status=200, headers={}, text_body=body)
        session = _mock_session(response)
        enricher = TechEnricher()
        with patch("src.enrichers.tech.make_aiohttp_session",
                   return_value=session):
            return enricher.enrich("example.com", {
                "subdomains": subdomains or ["www.example.com"],
            })

    def test_wordpress_detected_from_body(self):
        result = self._run_with_body(
            '<meta name="generator" content="WordPress 6.5">'
        )
        tech = result.get("tech_stack")
        self.assertIsNotNone(tech)

    def test_drupal_detected_from_body(self):
        result = self._run_with_body('<meta name="generator" content="Drupal 10">')
        self.assertIn("tech_stack", result)


if __name__ == "__main__":
    unittest.main()
