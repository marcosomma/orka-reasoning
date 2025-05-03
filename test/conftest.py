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
import sys
import os
import pytest

from unittest.mock import patch
from fake_redis import FakeRedisClient

@pytest.fixture(autouse=True, scope="session")
def patch_redis_globally():
    with patch("orka.memory_logger.redis.from_url", return_value=FakeRedisClient()):
        yield

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_remove_group_keyerror():
    mgr = ForkGroupManager()
    with pytest.raises(KeyError):
        mgr.remove_group("nonexistent")

def test_main_invokes_asyncio(monkeypatch):
    called = {}
    def fake_run(coro):
        called["ran"] = True
    monkeypatch.setattr("asyncio.run", fake_run)
    sys_argv = sys.argv
    sys.argv = ["prog", "config.yml", "input"]
    try:
        monkeypatch.setattr("orka.orchestrator.Orchestrator", lambda config_path: type("DummyOrchestrator", (), {"run": lambda self, x: None})())
        import importlib
        importlib.reload(orka_cli)
        assert called.get("ran")
    finally:
        sys.argv = sys_argv
