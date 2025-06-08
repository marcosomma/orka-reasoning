# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orka.orka_start import (
    get_docker_dir,
    get_memory_backend,
    main,
    start_backend,
    start_infrastructure,
)


@pytest.fixture
def mock_docker_dir(tmp_path):
    """Create a temporary docker directory with docker-compose.yml"""
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    compose_file = docker_dir / "docker-compose.yml"
    compose_file.write_text(
        "version: '3'\nservices:\n  redis:\n    image: redis:latest",
    )
    return str(docker_dir)


def test_get_docker_dir_found_in_package(monkeypatch):
    """Test finding docker directory in installed package"""
    mock_package_path = Path("/fake/package/path")
    mock_docker_dir = mock_package_path / "docker"

    # Mock the orka package
    mock_orka = MagicMock()
    mock_orka.__file__ = str(mock_package_path / "__init__.py")
    monkeypatch.setitem(sys.modules, "orka", mock_orka)

    # Mock Path.exists to return True for docker directory
    with patch("pathlib.Path.exists", return_value=True):
        result = get_docker_dir()
        assert result == str(mock_docker_dir)


def test_get_docker_dir_not_found(monkeypatch):
    """Test error when docker directory is not found"""
    # Mock Path.exists to return False
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Could not find docker directory"):
            get_docker_dir()


def test_get_memory_backend():
    """Test memory backend detection"""
    # Test default backend
    with patch.dict("os.environ", {}, clear=True):
        assert get_memory_backend() == "redis"

    # Test redis backend
    with patch.dict("os.environ", {"ORKA_MEMORY_BACKEND": "redis"}):
        assert get_memory_backend() == "redis"

    # Test kafka backend
    with patch.dict("os.environ", {"ORKA_MEMORY_BACKEND": "kafka"}):
        assert get_memory_backend() == "kafka"

    # Test dual backend
    with patch.dict("os.environ", {"ORKA_MEMORY_BACKEND": "dual"}):
        assert get_memory_backend() == "dual"

    # Test invalid backend defaults to redis
    with patch.dict("os.environ", {"ORKA_MEMORY_BACKEND": "invalid"}):
        assert get_memory_backend() == "redis"


def test_start_infrastructure_redis(mock_docker_dir):
    """Test Redis infrastructure startup"""
    with (
        patch("subprocess.run") as mock_run,
        patch("orka.orka_start.get_docker_dir", return_value=mock_docker_dir),
        patch("time.sleep"),
    ):  # Mock sleep to speed up tests
        # Mock successful subprocess runs
        mock_run.return_value = MagicMock(returncode=0)

        start_infrastructure("redis")

        # Verify docker-compose commands were called in correct order
        assert mock_run.call_count >= 3
        calls = mock_run.call_args_list

        # Check that docker-compose down was called
        down_calls = [call for call in calls if "down" in str(call)]
        assert len(down_calls) > 0

        # Check that redis service was started
        up_calls = [call for call in calls if "up" in str(call)]
        assert len(up_calls) > 0


def test_start_infrastructure_failure(mock_docker_dir):
    """Test infrastructure startup failure handling"""
    with (
        patch("subprocess.run") as mock_run,
        patch("orka.orka_start.get_docker_dir", return_value=mock_docker_dir),
        patch("time.sleep"),
    ):
        # Mock failed subprocess run for the critical step
        def side_effect(*args, **kwargs):
            # Fail on the docker-compose up command
            if "up" in str(args[0]):
                raise subprocess.CalledProcessError(1, "docker-compose")
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        with pytest.raises(subprocess.CalledProcessError):
            start_infrastructure("redis")


def test_start_backend():
    """Test backend startup"""
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        result = start_backend("redis")

        assert result == mock_process
        # Check that Popen was called with the correct command and env parameter
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        assert call_args[0][0] == [sys.executable, "-m", "orka.server"]
        assert "env" in call_args[1]
        assert call_args[1]["env"]["ORKA_MEMORY_BACKEND"] == "redis"


def test_start_backend_failure():
    """Test backend startup failure"""
    with patch("subprocess.Popen", side_effect=Exception("Failed to start")):
        with pytest.raises(Exception, match="Failed to start"):
            start_backend("redis")


@pytest.mark.asyncio
async def test_main_success(monkeypatch):
    """Test successful main execution"""
    # Mock the required functions
    monkeypatch.setattr("orka.orka_start.start_infrastructure", MagicMock())
    monkeypatch.setattr("orka.orka_start.wait_for_services", MagicMock())
    monkeypatch.setattr(
        "orka.orka_start.start_backend",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr("orka.orka_start.cleanup_services", MagicMock())

    # Mock asyncio.sleep to raise KeyboardInterrupt immediately
    with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
        try:
            await main()
        except KeyboardInterrupt:
            pass  # Expected exception


@pytest.mark.asyncio
async def test_main_backend_failure(monkeypatch):
    """Test main execution with backend failure"""
    # Mock the required functions
    monkeypatch.setattr("orka.orka_start.start_infrastructure", MagicMock())
    monkeypatch.setattr("orka.orka_start.wait_for_services", MagicMock())
    mock_backend = MagicMock()
    mock_backend.poll.return_value = 1  # Simulate backend process exit
    monkeypatch.setattr(
        "orka.orka_start.start_backend",
        MagicMock(return_value=mock_backend),
    )
    monkeypatch.setattr("orka.orka_start.cleanup_services", MagicMock())

    # Mock asyncio.sleep to avoid actual waiting
    with patch("asyncio.sleep"):
        await main()
        # Verify backend was checked
        assert mock_backend.poll.called


@pytest.mark.asyncio
async def test_main_cleanup(monkeypatch):
    """Test cleanup on keyboard interrupt"""
    # Mock the required functions
    monkeypatch.setattr("orka.orka_start.start_infrastructure", MagicMock())
    monkeypatch.setattr("orka.orka_start.wait_for_services", MagicMock())
    mock_backend = MagicMock()
    monkeypatch.setattr(
        "orka.orka_start.start_backend",
        MagicMock(return_value=mock_backend),
    )
    mock_cleanup = MagicMock()
    monkeypatch.setattr("orka.orka_start.cleanup_services", mock_cleanup)

    # Mock asyncio.sleep to raise KeyboardInterrupt immediately
    with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
        try:
            await main()
        except KeyboardInterrupt:
            pass  # Expected exception

        # Verify cleanup was performed
        assert mock_backend.terminate.called
        assert mock_backend.wait.called
        assert mock_cleanup.called
