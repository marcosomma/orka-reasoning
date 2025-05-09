import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orka.orka_start import get_docker_dir, main, start_backend, start_redis


@pytest.fixture
def mock_docker_dir(tmp_path):
    """Create a temporary docker directory with docker-compose.yml"""
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    compose_file = docker_dir / "docker-compose.yml"
    compose_file.write_text(
        "version: '3'\nservices:\n  redis:\n    image: redis:latest"
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


def test_start_redis(mock_docker_dir):
    """Test Redis startup sequence"""
    with patch("subprocess.run") as mock_run:
        # Mock successful subprocess runs
        mock_run.return_value = MagicMock(returncode=0)

        start_redis()

        # Verify docker-compose commands were called in correct order
        assert mock_run.call_count == 3
        calls = mock_run.call_args_list

        # Check docker-compose down
        assert "down" in calls[0][0][0]
        # Check docker-compose pull
        assert "pull" in calls[1][0][0]
        # Check docker-compose up
        assert "up" in calls[2][0][0]
        assert "-d" in calls[2][0][0]
        assert "redis" in calls[2][0][0]


def test_start_redis_failure(mock_docker_dir):
    """Test Redis startup failure handling"""
    with patch("subprocess.run") as mock_run:
        # Mock failed subprocess run
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker-compose")

        with pytest.raises(subprocess.CalledProcessError):
            start_redis()


def test_start_backend():
    """Test backend startup"""
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        result = start_backend()

        assert result == mock_process
        mock_popen.assert_called_once_with([sys.executable, "-m", "orka.server"])


def test_start_backend_failure():
    """Test backend startup failure"""
    with patch("subprocess.Popen", side_effect=Exception("Failed to start")):
        with pytest.raises(Exception, match="Failed to start"):
            start_backend()


@pytest.mark.asyncio
async def test_main_success(monkeypatch):
    """Test successful main execution"""
    # Mock the required functions
    monkeypatch.setattr("orka.orka_start.start_redis", MagicMock())
    monkeypatch.setattr(
        "orka.orka_start.start_backend", MagicMock(return_value=MagicMock())
    )

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
    monkeypatch.setattr("orka.orka_start.start_redis", MagicMock())
    mock_backend = MagicMock()
    mock_backend.poll.return_value = 1  # Simulate backend process exit
    monkeypatch.setattr(
        "orka.orka_start.start_backend", MagicMock(return_value=mock_backend)
    )

    # Mock asyncio.sleep to avoid actual waiting
    with patch("asyncio.sleep"):
        await main()
        # Verify backend was checked
        assert mock_backend.poll.called


@pytest.mark.asyncio
async def test_main_cleanup(monkeypatch):
    """Test cleanup on keyboard interrupt"""
    # Mock the required functions
    monkeypatch.setattr("orka.orka_start.start_redis", MagicMock())
    mock_backend = MagicMock()
    monkeypatch.setattr(
        "orka.orka_start.start_backend", MagicMock(return_value=mock_backend)
    )

    # Mock subprocess.run for cleanup
    with patch("subprocess.run") as mock_run:
        # Mock asyncio.sleep to raise KeyboardInterrupt immediately
        with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
            try:
                await main()
            except KeyboardInterrupt:
                pass  # Expected exception

            # Verify cleanup was performed
            assert mock_backend.terminate.called
            assert mock_backend.wait.called
            assert mock_run.called  # docker-compose down
