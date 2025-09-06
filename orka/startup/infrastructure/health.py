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
Health Checking
===============

This module provides health checking functionality for infrastructure services.
"""

import asyncio
import logging
import subprocess
from typing import Dict

logger = logging.getLogger(__name__)


def wait_for_services(backend: str) -> None:
    """
    Wait for infrastructure services to be ready.

    Args:
        backend: The backend type ('redis' or 'redisstack')
    """
    # Redis is already checked during native startup in start_native_redis()
    # No additional waiting needed for Redis
    pass


async def monitor_backend_process(backend_proc: subprocess.Popen) -> None:
    """
    Monitor the backend process and detect if it stops unexpectedly.

    Args:
        backend_proc: The backend process to monitor

    Raises:
        RuntimeError: If the backend process stops unexpectedly
    """
    while True:
        try:
            await asyncio.sleep(1)
            # Check if backend process is still running
            if backend_proc.poll() is not None:
                logger.error("Orka backend stopped unexpectedly!")
                raise RuntimeError("Backend process terminated")
        except asyncio.CancelledError:
            # This happens when Ctrl+C is pressed, break out of the loop
            break


def display_service_endpoints(backend: str) -> None:
    """
    Display service endpoints for the configured backend.

    Args:
        backend: The backend type ('redis' or 'redisstack')
    """
    logger.info(f"🚀 Starting OrKa with {backend.upper()} backend...")
    logger.info("=" * 80)

    logger.info("📍 Service Endpoints:")
    logger.info("   • Orka API: http://localhost:8000")
    logger.info("   • Redis:    localhost:6380 (native)")

    logger.info("=" * 80)


def display_startup_success() -> None:
    """Display successful startup message."""
    logger.info("")
    logger.info("✅ All services started successfully!")
    logger.info("📝 Press Ctrl+C to stop all services")
    logger.info("")


def display_shutdown_message() -> None:
    """Display graceful shutdown message."""
    logger.info("\n🛑 Shutting down services...")


def display_shutdown_complete() -> None:
    """Display shutdown complete message."""
    logger.info("✅ All services stopped.")


def display_error(error: Exception) -> None:
    """
    Display error message during startup.

    Args:
        error: The exception that occurred
    """
    logger.error(f"Error during startup: {error}")


def check_process_health(processes: Dict[str, subprocess.Popen]) -> bool:
    """
    Check the health of all managed processes.

    Args:
        processes: Dictionary of process name to process object

    Returns:
        bool: True if all processes are healthy, False otherwise
    """
    for name, proc in processes.items():
        if proc and proc.poll() is not None:
            logger.warning(f"Process {name} has terminated unexpectedly")
            return False
    return True
