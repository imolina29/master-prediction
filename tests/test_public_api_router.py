import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.public.router import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health(client):
    r = client.get("/api/public/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upcoming(client):
    r = client.get("/api/public/predictions/upcoming")
    assert r.status_code == 200
    assert "predictions" in r.json()


def test_stats(client):
    r = client.get("/api/public/predictions/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "accuracy" in data
    assert "by_confidence" in data


def test_track_record_paginated(client):
    r = client.get("/api/public/predictions/track-record?page=1&per_page=10")
    assert r.status_code == 200
    data = r.json()
    assert "predictions" in data
    assert "page" in data


def test_league_upcoming(client):
    r = client.get("/api/public/league/la-liga/upcoming")
    assert r.status_code == 200
    data = r.json()
    assert "league" in data
    assert "predictions" in data


def test_league_invalid_slug(client):
    r = client.get("/api/public/league/invalid-league/upcoming")
    assert r.status_code == 404
