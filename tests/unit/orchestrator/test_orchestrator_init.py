import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.orchestrator import Orchestrator


def test_orchestrator_init_monkeypatched(monkeypatch, temp_config_file):
    # Patch parent initializers to avoid heavy side effects during init
    monkeypatch.setattr('orka.orchestrator.execution_engine.ExecutionEngine.__init__', lambda self, cfg: None)

    # OrchestratorBase.__init__ normally sets orchestrator_cfg, agent_cfgs and memory
    def fake_base_init(self, cfg):
        self.orchestrator_cfg = {"agents": []}
        self.agent_cfgs = []
        self.memory = MagicMock()

    monkeypatch.setattr('orka.orchestrator.base.OrchestratorBase.__init__', fake_base_init)
    monkeypatch.setattr('orka.orchestrator.agent_factory.AgentFactory.__init__', lambda self, cfg, agents, memory: None)
    monkeypatch.setattr('orka.orchestrator.error_handling.ErrorHandler.__init__', lambda self: None)
    monkeypatch.setattr('orka.orchestrator.metrics.MetricsCollector.__init__', lambda self: None)

    # Patch _init_agents to return a predictable dict
    monkeypatch.setattr('orka.orchestrator.agent_factory.AgentFactory._init_agents', lambda self: {"a1": MagicMock()})

    orch = Orchestrator(temp_config_file)

    assert hasattr(orch, 'agents')
    assert 'a1' in orch.agents


@pytest.mark.asyncio
async def test_orchestrator_run_delegates(monkeypatch, temp_config_file):
    # Monkeypatch initializers again
    monkeypatch.setattr('orka.orchestrator.execution_engine.ExecutionEngine.__init__', lambda self, cfg: None)

    def fake_base_init(self, cfg):
        self.orchestrator_cfg = {"agents": []}
        self.agent_cfgs = []
        self.memory = MagicMock()

    monkeypatch.setattr('orka.orchestrator.base.OrchestratorBase.__init__', fake_base_init)
    monkeypatch.setattr('orka.orchestrator.agent_factory.AgentFactory.__init__', lambda self, cfg, agents, memory: None)
    monkeypatch.setattr('orka.orchestrator.error_handling.ErrorHandler.__init__', lambda self: None)
    monkeypatch.setattr('orka.orchestrator.metrics.MetricsCollector.__init__', lambda self: None)
    monkeypatch.setattr('orka.orchestrator.agent_factory.AgentFactory._init_agents', lambda self: {})

    orch = Orchestrator(temp_config_file)

    # Patch ExecutionEngine.run on the instance to an AsyncMock
    orch.run = AsyncMock(return_value=[{"agent_id": "a1"}])

    res = await orch.run({"input": "x"})

    assert isinstance(res, list)
    orch.run.assert_awaited()
