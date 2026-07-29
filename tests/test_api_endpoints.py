"""Tests for the FastAPI backend API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create test client with mocked API key."""
    with patch.dict("os.environ", {"API_KEY_WEBAPP": "test-key-123"}):
        import backend.api.auth as auth_mod

        auth_mod.API_KEYS.clear()
        auth_mod._load_keys()

        from backend.api.app import create_app

        app = create_app()
        yield TestClient(app)
        auth_mod.API_KEYS.clear()


HEADERS = {"X-API-Key": "test-key-123"}


class TestChatEndpoint:
    def test_chat_returns_response(self, api_client):
        with (
            patch("backend.advisor.engine.get_response") as mock_resp,
            patch("backend.db.client.get_supabase") as mock_sb,
        ):
            mock_resp.return_value = (
                "Hola! Argentina juega manana.",
                {"last_team": "Argentina"},
            )
            mock_sb.return_value = None
            resp = api_client.post(
                "/api/chat",
                json={"message": "Argentina", "history": [], "context": {}},
                headers=HEADERS,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "Hola! Argentina juega manana."
        assert data["context"]["last_team"] == "Argentina"

    def test_chat_requires_api_key(self, api_client):
        resp = api_client.post(
            "/api/chat",
            json={"message": "test", "history": [], "context": {}},
        )
        assert resp.status_code in (401, 422)

    def test_chat_rejects_bad_key(self, api_client):
        resp = api_client.post(
            "/api/chat",
            json={"message": "test", "history": [], "context": {}},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401


class TestPerformanceEndpoint:
    def test_performance_returns_metrics(self, api_client):
        picks = [
            {"result": "win", "profit": 0.9, "stake": 1.0, "market": "1x2_home"},
            {"result": "loss", "profit": -1.0, "stake": 1.0, "market": "1x2_away"},
            {"result": "win", "profit": 0.8, "stake": 1.0, "market": "1x2_home"},
        ]
        resp = api_client.post(
            "/api/performance",
            json={"resolved_picks": picks},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_picks"] == 3
        assert data["wins"] == 2

    def test_performance_empty_picks(self, api_client):
        resp = api_client.post(
            "/api/performance",
            json={"resolved_picks": []},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["total_picks"] == 0

    def test_performance_requires_auth(self, api_client):
        resp = api_client.post(
            "/api/performance",
            json={"resolved_picks": []},
        )
        assert resp.status_code in (401, 422)
