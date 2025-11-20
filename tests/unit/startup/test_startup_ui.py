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
Unit tests for OrKa UI container management.

These tests verify the UI container lifecycle management including:
- Container status checking
- Container starting and stopping
- Docker image pulling
- Environment variable handling
- Error handling for missing Docker
"""

import subprocess
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock torch before importing orka to avoid conflicts
sys.modules['torch'] = MagicMock()
sys.modules['torch.cuda'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

from orka.startup.ui import (
    cleanup_ui_container,
    is_ui_container_running,
    start_ui_container,
    stop_ui_container,
)


class TestIsUIContainerRunning:
    """Test suite for checking if UI container is running."""

    @patch("orka.startup.ui.subprocess.run")
    def test_container_is_running(self, mock_run):
        """Test detection when container is running."""
        mock_run.return_value = Mock(stdout="orka-ui\n", returncode=0)

        result = is_ui_container_running()

        assert result is True
        mock_run.assert_called_once_with(
            ["docker", "ps", "--filter", "name=orka-ui", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("orka.startup.ui.subprocess.run")
    def test_container_not_running(self, mock_run):
        """Test detection when container is not running."""
        mock_run.return_value = Mock(stdout="", returncode=0)

        result = is_ui_container_running()

        assert result is False

    @patch("orka.startup.ui.subprocess.run")
    def test_container_check_with_other_containers(self, mock_run):
        """Test detection with other containers running."""
        mock_run.return_value = Mock(stdout="other-container\nanother-one\n", returncode=0)

        result = is_ui_container_running()

        assert result is False

    @patch("orka.startup.ui.subprocess.run")
    def test_docker_command_fails(self, mock_run):
        """Test handling when docker command fails."""
        mock_run.side_effect = Exception("Docker not available")

        result = is_ui_container_running()

        assert result is False

    @patch("orka.startup.ui.subprocess.run")
    def test_subprocess_error(self, mock_run):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        result = is_ui_container_running()

        assert result is False


class TestStopUIContainer:
    """Test suite for stopping UI container."""

    @patch("orka.startup.ui.subprocess.run")
    def test_stop_running_container(self, mock_run):
        """Test stopping a running container."""
        mock_run.return_value = Mock(returncode=0)

        stop_ui_container()

        # Should call docker stop and docker rm
        assert mock_run.call_count == 2
        calls = mock_run.call_args_list

        # First call: stop
        assert calls[0][0][0] == ["docker", "stop", "orka-ui"]
        assert calls[0][1]["capture_output"] is True
        assert calls[0][1]["check"] is False

        # Second call: rm
        assert calls[1][0][0] == ["docker", "rm", "orka-ui"]

    @patch("orka.startup.ui.subprocess.run")
    def test_stop_nonexistent_container(self, mock_run):
        """Test stopping when container doesn't exist (should not raise error)."""
        mock_run.return_value = Mock(returncode=1)

        # Should not raise exception
        stop_ui_container()

        assert mock_run.call_count == 2

    @patch("orka.startup.ui.subprocess.run")
    def test_stop_container_exception_handling(self, mock_run):
        """Test exception handling during container stop."""
        mock_run.side_effect = Exception("Docker error")

        # Should not raise exception
        stop_ui_container()


class TestStartUIContainer:
    """Test suite for starting UI container."""

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_success(self, mock_run, mock_stop, mock_is_running, mock_sleep):
        """Test successful container start."""
        # Container not running initially, running after start
        mock_is_running.side_effect = [False, True]
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = start_ui_container()

        assert result is True
        mock_stop.assert_called_once()
        # Should call pull and run
        assert mock_run.call_count == 2

        # Verify pull command
        pull_call = mock_run.call_args_list[0]
        assert "docker" in pull_call[0][0]
        assert "pull" in pull_call[0][0]
        assert "marcosomma/orka-ui:latest" in pull_call[0][0]

        # Verify run command
        run_call = mock_run.call_args_list[1]
        run_cmd = run_call[0][0]
        assert "docker" in run_cmd
        assert "run" in run_cmd
        assert "-d" in run_cmd
        assert "--name" in run_cmd
        assert "orka-ui" in run_cmd
        assert "-p" in run_cmd
        assert "8080:80" in run_cmd

    @patch("orka.startup.ui.is_ui_container_running")
    def test_start_container_already_running(self, mock_is_running):
        """Test starting when container is already running."""
        mock_is_running.return_value = True

        result = start_ui_container()

        assert result is True
        # Should return early without attempting to start

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_custom_api_url(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test starting container with custom API URL."""
        mock_is_running.side_effect = [False, True]
        mock_run.return_value = Mock(returncode=0)

        custom_url = "http://custom-api:9000"
        result = start_ui_container(api_url=custom_url)

        assert result is True

        # Verify run command contains custom URL
        run_call = mock_run.call_args_list[1]
        run_cmd = run_call[0][0]
        env_var = f"VITE_API_URL_LOCAL={custom_url}/api/run@dist"
        assert env_var in run_cmd

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    @patch.dict("os.environ", {"ORKA_API_URL": "http://env-api:7000"})
    def test_start_container_env_api_url(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test starting container with API URL from environment."""
        mock_is_running.side_effect = [False, True]
        mock_run.return_value = Mock(returncode=0)

        result = start_ui_container()

        assert result is True

        # Verify run command contains env URL
        run_call = mock_run.call_args_list[1]
        run_cmd = run_call[0][0]
        env_var = "VITE_API_URL_LOCAL=http://env-api:7000/api/run@dist"
        assert env_var in run_cmd

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_pull_fails(self, mock_run, mock_stop, mock_is_running, mock_sleep):
        """Test starting container when image pull fails but cached image works."""
        mock_is_running.side_effect = [False, True]

        # Pull fails, but run succeeds
        def run_side_effect(cmd, **kwargs):
            if "pull" in cmd:
                return Mock(returncode=1, stderr="Pull failed")
            return Mock(returncode=0)

        mock_run.side_effect = run_side_effect

        result = start_ui_container()

        assert result is True  # Should succeed with cached image

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    @patch.dict("os.environ", {"ORKA_UI_SKIP_PULL": "true"})
    def test_start_container_skip_pull(self, mock_run, mock_stop, mock_is_running, mock_sleep):
        """Test starting container with pull skipped via environment variable."""
        mock_is_running.side_effect = [False, True]
        mock_run.return_value = Mock(returncode=0)

        result = start_ui_container()

        assert result is True
        # Should only call run, not pull
        assert mock_run.call_count == 1
        run_cmd = mock_run.call_args[0][0]
        assert "docker" in run_cmd
        assert "run" in run_cmd

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    @patch.dict("os.environ", {"ORKA_UI_SKIP_PULL": "1"})
    def test_start_container_skip_pull_numeric(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test skip pull with numeric environment variable."""
        mock_is_running.side_effect = [False, True]
        mock_run.return_value = Mock(returncode=0)

        result = start_ui_container()

        assert result is True
        assert mock_run.call_count == 1  # Only run, no pull

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_run_fails(self, mock_run, mock_stop, mock_is_running, mock_sleep):
        """Test failure when docker run command fails."""
        mock_is_running.side_effect = [False, False]  # Not running before or after

        def run_side_effect(cmd, **kwargs):
            if "pull" in cmd:
                return Mock(returncode=0)
            # Run command fails
            raise subprocess.CalledProcessError(1, cmd, stderr="Run failed")

        mock_run.side_effect = run_side_effect

        result = start_ui_container()

        assert result is False

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_docker_not_found(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test failure when Docker is not installed."""
        mock_is_running.return_value = False
        mock_run.side_effect = FileNotFoundError("docker not found")

        result = start_ui_container()

        assert result is False

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_unexpected_error(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test handling of unexpected errors."""
        mock_is_running.return_value = False
        mock_run.side_effect = Exception("Unexpected error")

        result = start_ui_container()

        assert result is False

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    def test_start_container_not_running_after_start(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test when container starts but verification shows it's not running."""
        # Not running initially or after start
        mock_is_running.side_effect = [False, False]
        mock_run.return_value = Mock(returncode=0)

        result = start_ui_container()

        assert result is False


class TestCleanupUIContainer:
    """Test suite for UI container cleanup."""

    @patch("orka.startup.ui.stop_ui_container")
    def test_cleanup_ui_container(self, mock_stop):
        """Test cleanup calls stop_ui_container."""
        cleanup_ui_container()

        mock_stop.assert_called_once()

    @patch("orka.startup.ui.stop_ui_container")
    def test_cleanup_with_exception(self, mock_stop):
        """Test cleanup handles exceptions gracefully."""
        mock_stop.side_effect = Exception("Stop failed")

        # Should not raise exception
        cleanup_ui_container()


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple functions."""

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.subprocess.run")
    def test_full_lifecycle_start_stop(self, mock_run, mock_sleep):
        """Test full container lifecycle: start -> verify -> stop."""
        # Setup: container not initially running
        def is_running_side_effect():
            # First call: check before start (not running)
            # Second call: check after start (running)
            # Third call: check after stop (not running)
            for running in [False, True, False]:
                yield running

        running_gen = is_running_side_effect()

        def mock_run_impl(cmd, **kwargs):
            if cmd == [
                "docker",
                "ps",
                "--filter",
                "name=orka-ui",
                "--format",
                "{{.Names}}",
            ]:
                is_running = next(running_gen, False)
                return Mock(stdout="orka-ui\n" if is_running else "", returncode=0)
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_run_impl

        # Start container
        with patch("orka.startup.ui.is_ui_container_running") as mock_is_running:
            mock_is_running.side_effect = [False, True]
            result = start_ui_container()
            assert result is True

        # Stop container
        stop_ui_container()

        # Verify stop was called
        stop_calls = [call for call in mock_run.call_args_list if "stop" in str(call)]
        assert len(stop_calls) > 0

    @patch("orka.startup.ui.time.sleep")
    @patch("orka.startup.ui.is_ui_container_running")
    @patch("orka.startup.ui.stop_ui_container")
    @patch("orka.startup.ui.subprocess.run")
    @patch.dict("os.environ", {"ORKA_API_URL": "http://test:8000", "ORKA_UI_SKIP_PULL": "yes"})
    def test_start_with_all_env_vars(
        self, mock_run, mock_stop, mock_is_running, mock_sleep
    ):
        """Test starting with multiple environment variables set."""
        mock_is_running.side_effect = [False, True]
        mock_run.return_value = Mock(returncode=0)

        result = start_ui_container()

        assert result is True
        # Verify only run is called (pull skipped)
        assert mock_run.call_count == 1
        # Verify custom API URL is used
        run_cmd = mock_run.call_args[0][0]
        assert "VITE_API_URL_LOCAL=http://test:8000/api/run@dist" in run_cmd
