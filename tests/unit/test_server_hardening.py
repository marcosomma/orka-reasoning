"""POC ⑤: behavioral tests for the hardened FastAPI server.

These exercise the access-control / input-bound guards on /api/run, which return
before any orchestration runs (so no Redis/LLM needed), plus the CORS default.
"""

from __future__ import annotations

import importlib

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

import orka.server as server  # noqa: E402


@pytest.fixture
def client():
    return TestClient(server.app)


def test_cors_defaults_to_localhost_not_wildcard():
    # Default CORS must be the local UI origins, not "*"+credentials.
    assert server._cors_origins != ["*"]
    assert any("localhost" in o or "127.0.0.1" in o for o in server._cors_origins)
    assert server._cors_credentials is True


def test_run_requires_yaml_config(client):
    r = client.post("/api/run", json={"input": "hi"})  # no yaml_config
    assert r.status_code == 400
    assert "yaml_config" in r.json().get("error", "")


def test_run_rejects_oversized_body(client, monkeypatch):
    monkeypatch.setenv("ORKA_MAX_REQUEST_BYTES", "32")
    r = client.post("/api/run", json={"input": "x" * 500, "yaml_config": "y" * 500})
    assert r.status_code == 413
    assert "exceeds" in r.json().get("error", "")


def test_run_api_key_gate_blocks_without_key(client, monkeypatch):
    monkeypatch.setenv("ORKA_API_KEY", "s3cret")
    r = client.post("/api/run", json={"input": "hi", "yaml_config": "x: 1"})
    assert r.status_code == 401


def test_run_api_key_gate_allows_with_key(client, monkeypatch):
    monkeypatch.setenv("ORKA_API_KEY", "s3cret")
    # Correct key passes the gate; we send no yaml_config so it stops at validation (400),
    # proving the request got PAST the 401 gate without needing a live orchestrator.
    r = client.post("/api/run", json={"input": "hi"}, headers={"X-API-Key": "s3cret"})
    assert r.status_code == 400  # not 401


def test_health_endpoint_exists(client):
    r = client.get("/health")
    assert r.status_code in (200, 503)  # 503 if Redis down — endpoint itself works
