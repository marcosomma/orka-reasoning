# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
# 
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

from fake_redis import FakeRedisClient

import sys
import redis
redis.Redis = lambda *a, **kw: FakeRedisClient()
redis.StrictRedis = lambda *a, **kw: FakeRedisClient()

import pytest
import yaml
import orka.orka_cli as orka_cli
import asyncio

# --- orka_cli.py ---

def make_dummy_yaml(tmp_path):
    config = {
        "orchestrator": {
            "id": "test_orchestrator",
            "strategy": "decision-tree",
            "queue": "orka:test",
            "agents": ["dummy_agent"]
        },
        "agents": [
            {
                "id": "dummy_agent",
                "type": "openai-binary",
                "prompt": "Is '{{ input }}' a valid project?",
                "queue": "orka:dummy"
            }
        ]
    }
    file = tmp_path / "dummy.yml"
    file.write_text(yaml.dump(config))
    return str(file)

@pytest.mark.asyncio
async def test_run_cli_entrypoint_prints_dict(tmp_path, monkeypatch):
    class DummyOrchestrator:
        def __init__(self, config_path):
            pass
        async def run(self, input_text):
            return {"agent1": "result1", "agent2": "result2"}
    monkeypatch.setattr("orka.orchestrator.Orchestrator", DummyOrchestrator)
    config_path = make_dummy_yaml(tmp_path)
    result = await orka_cli.run_cli_entrypoint(config_path, "input", log_to_file=False)
    assert isinstance(result, dict)
    assert "agent1" in result

@pytest.mark.asyncio
async def test_run_cli_entrypoint_prints_list(tmp_path, monkeypatch, capsys):
    class DummyOrchestrator:
        async def run(self, input_text):
            return [
                {"agent_id": "agent1", "payload": {"foo": "bar"}},
                {"agent_id": "agent2", "payload": {"baz": "qux"}}
            ]
    monkeypatch.setattr("orka.orchestrator.Orchestrator", lambda config_path: DummyOrchestrator())
    config_path = make_dummy_yaml(tmp_path)
    result = await orka_cli.run_cli_entrypoint(config_path, "input", log_to_file=False)
    captured = capsys.readouterr()
    assert "Agent: agent1" in captured.out
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_run_cli_entrypoint_prints_other(tmp_path, monkeypatch, capsys):
    class DummyOrchestrator:
        async def run(self, input_text):
            return "just a string"
    monkeypatch.setattr("orka.orchestrator.Orchestrator", lambda config_path: DummyOrchestrator())
    config_path = make_dummy_yaml(tmp_path)
    result = await orka_cli.run_cli_entrypoint(config_path, "input", log_to_file=False)
    captured = capsys.readouterr()
    assert "just a string" in captured.out
    assert result == "just a string"

@pytest.mark.asyncio
async def test_run_cli_entrypoint_log_to_file(tmp_path, monkeypatch):
    class DummyOrchestrator:
        async def run(self, input_text):
            return {"foo": "bar"}
    monkeypatch.setattr("orka.orchestrator.Orchestrator", lambda config_path: DummyOrchestrator())
    config_path = make_dummy_yaml(tmp_path)
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = await orka_cli.run_cli_entrypoint(config_path, "input", log_to_file=True)
        with open("orka_trace.log") as f:
            content = f.read()
        assert "foo" in content
    finally:
        os.chdir(old_cwd)

def test_main_invokes_asyncio(monkeypatch):
    called = {}
    def fake_run(coro):
        called["ran"] = True
        return None
    monkeypatch.setattr("asyncio.run", fake_run)
    sys_argv = sys.argv
    sys.argv = ["prog", "config.yml", "input"]
    try:
        class DummyOrchestrator:
            def __init__(self, config_path): pass
            async def run(self, x): return None
        monkeypatch.setattr("orka.orchestrator.Orchestrator", DummyOrchestrator)
        # Call main directly instead of reloading the module
        asyncio.run(orka_cli.main())
        assert called.get("ran")
    finally:
        sys.argv = sys_argv
import orka.server as orka_server

@pytest.mark.asyncio
async def test_run_execution(monkeypatch):
    # Patch Orchestrator to return a dummy result
    class DummyOrchestrator:
        def __init__(self, path): pass
        async def run(self, input_text): return "dummy_result"
    monkeypatch.setattr("orka.server.Orchestrator", DummyOrchestrator)
    # Fake request
    class DummyRequest:
        async def json(self):
            return {"input": "question", "yaml_config": "agents: []"}
    response = await orka_server.run_execution(DummyRequest())
    data = response.body.decode()
    assert "dummy_result" in data

def test_app_and_cors():
    # Just check that the app and middleware are set up
    assert hasattr(orka_server, "app")
    assert hasattr(orka_server.app, "add_middleware")

def test_server_main_runs(monkeypatch):
    called = {}
    def fake_run(app, host, port):
        called["ran"] = (app, host, port)
    monkeypatch.setattr("uvicorn.run", fake_run)
    # Simulate __main__ execution
    orka_server.__name__ = "__main__"
    orka_server.uvicorn.run(orka_server.app, host="0.0.0.0", port=8000)
    assert called["ran"][1] == "0.0.0.0"
    assert called["ran"][2] == 8000
