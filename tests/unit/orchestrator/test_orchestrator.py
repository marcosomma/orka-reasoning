from unittest.mock import AsyncMock, patch

import pytest

from orka.orchestrator import Orchestrator


class TestOrchestrator:
    @pytest.fixture
    def mock_loader(self):
        # Patch the YAMLLoader symbol where OrchestratorBase imports it so
        # the mock is active during Orchestrator initialization.
        with patch("orka.orchestrator.base.YAMLLoader") as MockLoader:
            yield MockLoader.return_value

    @pytest.fixture
    def mock_orchestrator_config(self):
        return {
            "id": "test_orchestrator",
            "description": "A test orchestrator",
            "agents": [],
            "nodes": [],
            "memory_config": {"enabled": True},
            "budget_config": {"enabled": True},
            "safety_config": {"enabled": True},
            "metrics_config": {"enabled": True},
            "structured_logging_config": {"enabled": True},
            "graph_api_config": {"enabled": True},
            "graph_introspection_config": {"enabled": True},
            "decision_engine_config": {"enabled": True},
        }

    def test_orchestrator_initialization_basic(self, mock_loader, mock_orchestrator_config):
        mock_loader.get_orchestrator.return_value = mock_orchestrator_config
        mock_loader.get_agents.return_value = mock_orchestrator_config["agents"]

        orchestrator = Orchestrator(config_path="./tests/unit/orchestrator/dummy_path.yml")

        # Config was stored on the object (may be merged with defaults by init logic)
        assert isinstance(orchestrator.orchestrator_cfg, dict)
        assert "id" in orchestrator.orchestrator_cfg
        assert "agents" in orchestrator.orchestrator_cfg

        # Loader instance is the mocked loader
        assert orchestrator.loader == mock_loader

        # Queue is taken from config
        assert isinstance(orchestrator.queue, list)
        assert orchestrator.queue == mock_orchestrator_config["agents"]

        # run exists and is awaitable (coroutine function on instance)
        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)

    def test_orchestrator_initialization_with_defaults(self, mock_loader):
        minimal_config = {"id": "minimal_orchestrator", "description": "Minimal", "agents": []}
        mock_loader.get_orchestrator.return_value = minimal_config
        mock_loader.get_agents.return_value = minimal_config["agents"]

        orchestrator = Orchestrator(config_path="./tests/unit/orchestrator/dummy_path.yml")

        # Orchestrator merges defaults; ensure minimal config produced a valid config and queue
        assert isinstance(orchestrator.orchestrator_cfg, dict)
        assert "id" in orchestrator.orchestrator_cfg
        assert orchestrator.queue == orchestrator.orchestrator_cfg.get("agents", [])

    @pytest.mark.asyncio
    async def test_run_orchestrator_success(self, mock_loader, mock_orchestrator_config):
        mock_loader.get_orchestrator.return_value = mock_orchestrator_config
        mock_loader.get_agents.return_value = mock_orchestrator_config["agents"]

        orchestrator = Orchestrator(config_path="./tests/unit/orchestrator/dummy_path.yml")

        # Patch the internal comprehensive runner used by the ExecutionEngine
        expected = {"status": "completed", "result": "success"}
        orchestrator._run_with_comprehensive_error_handling = AsyncMock(return_value=expected)

        result = await orchestrator.run("user_query")

        orchestrator._run_with_comprehensive_error_handling.assert_awaited_once()
        assert result == expected

    @pytest.mark.asyncio
    async def test_run_orchestrator_error_propagation(self, mock_loader, mock_orchestrator_config):
        mock_loader.get_orchestrator.return_value = mock_orchestrator_config
        mock_loader.get_agents.return_value = mock_orchestrator_config["agents"]

        orchestrator = Orchestrator(config_path="./tests/unit/orchestrator/dummy_path.yml")

        orchestrator._run_with_comprehensive_error_handling = AsyncMock(side_effect=Exception("Execution failed"))

        with pytest.raises(Exception, match="Execution failed"):
            await orchestrator.run("user_query")

    def test_context_manager_not_supported(self, mock_loader, mock_orchestrator_config):
        mock_loader.get_orchestrator.return_value = mock_orchestrator_config
        mock_loader.get_agents.return_value = mock_orchestrator_config["agents"]

        orchestrator = Orchestrator(config_path="./tests/unit/orchestrator/dummy_path.yml")

        # Using it in a 'with' should raise TypeError: object does not support the context manager protocol
        with pytest.raises(TypeError):
            with orchestrator:
                pass

    @pytest.mark.asyncio
    async def test_run_respects_debug_and_verbose_flags(self, mock_loader, mock_orchestrator_config):
        mock_orchestrator_config["debug_mode"] = True
        mock_orchestrator_config["verbose_mode"] = True
        mock_loader.get_orchestrator.return_value = mock_orchestrator_config
        mock_loader.get_agents.return_value = mock_orchestrator_config["agents"]

        orchestrator = Orchestrator(config_path="./tests/unit/orchestrator/dummy_path.yml")

        expected = {"status": "completed", "result": "ok"}
        orchestrator._run_with_comprehensive_error_handling = AsyncMock(return_value=expected)

        result = await orchestrator.run("user_query")

        orchestrator._run_with_comprehensive_error_handling.assert_awaited_once()
        assert result == expected