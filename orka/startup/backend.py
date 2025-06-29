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

"""
Backend Server Management
========================

This module handles OrKa backend server startup and management.
"""

import logging
import subprocess
import sys

from .config import configure_backend_environment

logger = logging.getLogger(__name__)


def start_backend(backend: str) -> subprocess.Popen:
    """
    Start the OrKa backend server as a separate process.

    This function launches the OrKa server module in a subprocess,
    allowing it to run independently while still being monitored by
    this parent process.

    Args:
        backend: The backend type ('redis', 'kafka', or 'dual')

    Returns:
        subprocess.Popen: The process object representing the running backend

    Raises:
        Exception: If the backend fails to start for any reason
    """
    logger.info("Starting Orka backend...")
    try:
        # Prepare environment variables for the backend process
        env = configure_backend_environment(backend)

        # Start the backend server with configured environment
        backend_proc: subprocess.Popen = subprocess.Popen(
            [sys.executable, "-m", "orka.server"],
            env=env,
        )
        logger.info("Orka backend started.")
        return backend_proc
    except Exception as e:
        logger.error(f"Error starting Orka backend: {e}")
        raise


def terminate_backend_process(backend_proc: subprocess.Popen) -> None:
    """
    Gracefully terminate the backend process.

    Args:
        backend_proc: The backend process to terminate
    """
    if backend_proc and backend_proc.poll() is None:  # Process is still running
        print("🛑 Stopping backend process...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
            print("✅ Backend stopped gracefully")
        except subprocess.TimeoutExpired:
            print("⚠️ Force killing backend process...")
            backend_proc.kill()
            backend_proc.wait()


def is_backend_running(backend_proc: subprocess.Popen) -> bool:
    """
    Check if the backend process is still running.

    Args:
        backend_proc: The backend process to check

    Returns:
        bool: True if the process is running, False otherwise
    """
    return backend_proc and backend_proc.poll() is None
