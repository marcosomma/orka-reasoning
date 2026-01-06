# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Service Orchestrator
===================

This module handles the main orchestration of OrKa services including startup,
monitoring, and shutdown coordination.
"""

import asyncio
import logging
import os
import subprocess
import sys

from .backend import start_backend
from .cleanup import cleanup_services
from .config import get_memory_backend
from .infrastructure.health import (
    display_error,
    display_final_banner,
    display_service_endpoints,
    display_shutdown_complete,
    display_shutdown_message,
    display_startup_success,
    monitor_backend_process,
    wait_for_services,
)
from .infrastructure.redis import start_native_redis
from .ui import start_ui_container

logger = logging.getLogger(__name__)


def start_infrastructure(backend: str) -> dict[str, subprocess.Popen]:
    """
    Start the infrastructure services natively.

    Redis will be started as a native process on port 6380.

    Args:
        backend: The backend type ('redis' or 'redisstack')

    Returns:
        Dict[str, subprocess.Popen]: Dictionary of started processes

    Raises:
        RuntimeError: If Redis Stack is not available or fails to start
    """
    processes = {}

    logger.info(f"Starting {backend.upper()} backend...")

    # Recommended: start Redis locally for native backends (unless explicitly using Docker); validate for your environment
    if backend in ["redis", "redisstack"]:
        redis_proc = start_native_redis(6380)
        if redis_proc is not None:
            processes["redis"] = redis_proc
        # If redis_proc is None, Redis is running via Docker and managed by Docker daemon

    return processes


async def main() -> None:
    """
    Main entry point for starting and managing OrKa services.

    This asynchronous function:
    1. Determines which backend to use (Redis or RedisStack)
    2. Starts the appropriate infrastructure services (Redis natively)
    3. Waits for services to be ready
    4. Launches the OrKa backend server
    5. Starts the OrKa UI container (if Docker is available)
    6. Monitors the backend process to ensure it's running
    7. Handles graceful shutdown on keyboard interrupt

    The function runs until interrupted (e.g., via Ctrl+C), at which point
    it cleans up all started processes and containers.
    """
    # Determine backend type
    backend = get_memory_backend()

    # Display startup information
    display_service_endpoints(backend)

    # Track all processes for cleanup
    processes = {}
    backend_proc = None
    ui_started = False

    try:
        # Start infrastructure
        processes = start_infrastructure(backend)

        # Wait for services to be ready
        wait_for_services(backend)

        # Start Orka backend
        backend_proc = start_backend(backend)
        processes["backend"] = backend_proc

        display_startup_success()

        # Start OrKa UI container (optional - won't fail if Docker is not available)
        # Check if UI should be disabled via environment variable
        if os.getenv("ORKA_DISABLE_UI", "").lower() not in ("true", "1", "yes"):
            ui_started = start_ui_container()
            if ui_started:
                logger.info("[WEB] OrKa UI is ready at http://localhost:8080")

        # Display banner just before Uvicorn logs - stays visible in terminal
        display_final_banner()

        # Monitor processes
        await monitor_backend_process(backend_proc)

    except KeyboardInterrupt:
        display_shutdown_message()
    except Exception as e:
        display_error(e)
    finally:
        # Always cleanup processes
        cleanup_services(backend, processes)
        display_shutdown_complete()


def run_startup() -> None:
    """
    Run the startup process with proper error handling.

    This function serves as the main entry point and handles
    keyboard interrupts and unexpected errors gracefully.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle any remaining KeyboardInterrupt that might bubble up
        logger.warning("[STOP] Shutdown complete.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
