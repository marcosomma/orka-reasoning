# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Unit tests for OrKa startup orchestrator.

These tests verify the main orchestration logic including:
- Infrastructure startup
- Backend server startup
- UI container startup integration
- Service lifecycle management
- Error handling and cleanup
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.startup.orchestrator import main, run_startup, start_infrastructure


class TestStartInfrastructure:
    """Test suite for infrastructure startup."""

    @patch("orka.startup.orchestrator.start_native_redis")
    def test_start_redis_backend(self, mock_start_redis):
        """Test starting infrastructure with Redis backend."""
        mock_redis_proc = Mock()
        mock_start_redis.return_value = mock_redis_proc

        processes = start_infrastructure("redis")

        assert "redis" in processes
        assert processes["redis"] == mock_redis_proc
        mock_start_redis.assert_called_once_with(6380)

    @patch("orka.startup.orchestrator.start_native_redis")
    def test_start_redisstack_backend(self, mock_start_redis):
        """Test starting infrastructure with RedisStack backend."""
        mock_redis_proc = Mock()
        mock_start_redis.return_value = mock_redis_proc

        processes = start_infrastructure("redisstack")

        assert "redis" in processes
        assert processes["redis"] == mock_redis_proc
        mock_start_redis.assert_called_once_with(6380)

    @patch("orka.startup.orchestrator.start_native_redis")
    def test_start_redis_returns_none(self, mock_start_redis):
        """Test when Redis is already running via Docker (returns None)."""
        mock_start_redis.return_value = None

        processes = start_infrastructure("redis")

        # Empty dict when Redis is managed by Docker
        assert processes == {}

    @patch("orka.startup.orchestrator.start_native_redis")
    def test_start_unknown_backend(self, mock_start_redis):
        """Test starting with unknown backend type."""
        processes = start_infrastructure("unknown")

        # Should not attempt to start Redis for unknown backend
        mock_start_redis.assert_not_called()
        assert processes == {}


class TestMainOrchestrator:
    """Test suite for main orchestration function."""

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_full_startup_success(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test successful full startup sequence."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {"redis": Mock()}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_start_ui.return_value = True
        # Simulate KeyboardInterrupt during monitoring
        mock_monitor.side_effect = KeyboardInterrupt()

        await main()

        # Verify startup sequence
        mock_get_backend.assert_called_once()
        mock_display_endpoints.assert_called_once_with("redis")
        mock_start_infra.assert_called_once_with("redis")
        mock_wait_services.assert_called_once_with("redis")
        mock_start_backend.assert_called_once_with("redis")
        mock_start_ui.assert_called_once()
        mock_monitor.assert_called_once_with(mock_backend_proc)
        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    @patch.dict("os.environ", {"ORKA_DISABLE_UI": "true"})
    async def test_main_with_ui_disabled(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test startup with UI disabled via environment variable."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {"redis": Mock()}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_monitor.side_effect = KeyboardInterrupt()

        await main()

        # UI should not be started
        mock_start_ui.assert_not_called()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    @patch.dict("os.environ", {"ORKA_DISABLE_UI": "1"})
    async def test_main_with_ui_disabled_numeric(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test UI disabled with numeric environment variable."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_monitor.side_effect = KeyboardInterrupt()

        await main()

        mock_start_ui.assert_not_called()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_ui_start_fails_gracefully(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test that UI startup failure doesn't crash the system."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_start_ui.return_value = False  # UI fails to start
        mock_monitor.side_effect = KeyboardInterrupt()

        await main()

        # System should continue despite UI failure
        mock_monitor.assert_called_once_with(mock_backend_proc)
        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.display_error")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_infrastructure_failure(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_display_error,
        mock_cleanup,
    ):
        """Test handling of infrastructure startup failure."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.side_effect = RuntimeError("Redis failed to start")

        await main()

        mock_display_error.assert_called_once()
        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_backend_startup_failure(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_cleanup,
    ):
        """Test handling of backend startup failure."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {}
        mock_start_backend.side_effect = Exception("Backend failed")

        await main()

        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.display_shutdown_message")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_keyboard_interrupt_handling(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_display_shutdown,
        mock_cleanup,
    ):
        """Test graceful handling of keyboard interrupt."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {"redis": Mock()}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_start_ui.return_value = True
        mock_monitor.side_effect = KeyboardInterrupt()

        await main()

        mock_display_shutdown.assert_called_once()
        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_with_redisstack_backend(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test startup with RedisStack backend."""
        mock_get_backend.return_value = "redisstack"
        mock_start_infra.return_value = {"redis": Mock()}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_start_ui.return_value = True
        mock_monitor.side_effect = KeyboardInterrupt()

        await main()

        mock_start_infra.assert_called_once_with("redisstack")
        mock_wait_services.assert_called_once_with("redisstack")
        mock_start_backend.assert_called_once_with("redisstack")

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_main_cleanup_always_runs(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test that cleanup always runs even on unexpected errors."""
        mock_get_backend.return_value = "redis"
        mock_start_infra.return_value = {"redis": Mock()}
        mock_backend_proc = Mock()
        mock_start_backend.return_value = mock_backend_proc
        mock_start_ui.return_value = True
        mock_monitor.side_effect = RuntimeError("Unexpected error")

        await main()

        # Cleanup should be called despite the error
        mock_cleanup.assert_called_once()


class TestRunStartup:
    """Test suite for run_startup wrapper function."""

    @patch("orka.startup.orchestrator.asyncio.run")
    def test_run_startup_success(self, mock_asyncio_run):
        """Test successful run_startup execution."""
        mock_asyncio_run.return_value = None

        run_startup()

        mock_asyncio_run.assert_called_once()

    @patch("orka.startup.orchestrator.asyncio.run")
    def test_run_startup_keyboard_interrupt(self, mock_asyncio_run):
        """Test run_startup handles KeyboardInterrupt."""
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        # Should not raise exception
        run_startup()

        mock_asyncio_run.assert_called_once()

    @patch("orka.startup.orchestrator.asyncio.run")
    def test_run_startup_unexpected_error(self, mock_asyncio_run):
        """Test run_startup handles unexpected errors."""
        mock_asyncio_run.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(SystemExit) as exc_info:
            run_startup()

        assert exc_info.value.code == 1
        mock_asyncio_run.assert_called_once()


class TestIntegrationScenarios:
    """Integration test scenarios for orchestrator."""

    @pytest.mark.asyncio
    @patch("orka.startup.orchestrator.cleanup_services")
    @patch("orka.startup.orchestrator.monitor_backend_process")
    @patch("orka.startup.orchestrator.start_ui_container")
    @patch("orka.startup.orchestrator.start_backend")
    @patch("orka.startup.orchestrator.wait_for_services")
    @patch("orka.startup.orchestrator.start_infrastructure")
    @patch("orka.startup.orchestrator.display_service_endpoints")
    @patch("orka.startup.orchestrator.get_memory_backend")
    async def test_full_startup_sequence_with_ui(
        self,
        mock_get_backend,
        mock_display_endpoints,
        mock_start_infra,
        mock_wait_services,
        mock_start_backend,
        mock_start_ui,
        mock_monitor,
        mock_cleanup,
    ):
        """Test complete startup sequence including UI."""
        # Setup
        mock_get_backend.return_value = "redisstack"
        redis_proc = Mock()
        mock_start_infra.return_value = {"redis": redis_proc}
        backend_proc = Mock()
        mock_start_backend.return_value = backend_proc
        mock_start_ui.return_value = True
        mock_monitor.side_effect = KeyboardInterrupt()

        # Execute
        await main()

        # Verify complete sequence
        assert mock_get_backend.called
        assert mock_display_endpoints.called
        assert mock_start_infra.called
        assert mock_wait_services.called
        assert mock_start_backend.called
        assert mock_start_ui.called
        assert mock_monitor.called

        # Verify cleanup with correct parameters
        mock_cleanup.assert_called_once()
        cleanup_call = mock_cleanup.call_args
        assert cleanup_call[0][0] == "redisstack"  # backend
        assert "redis" in cleanup_call[0][1]  # processes dict
        assert "backend" in cleanup_call[0][1]
