# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
OrKa Service Runner
==================

This module provides functionality to start and manage the OrKa infrastructure services.
It handles the initialization and lifecycle of Redis and the OrKa backend server,
ensuring they are properly configured and running before allowing user workflows
to execute.

Key Features:
-----------
1. Infrastructure Management: Automates the startup and shutdown of required services
2. Docker Integration: Manages Redis containers via Docker Compose
3. Process Management: Starts and monitors the OrKa backend server process
4. Graceful Shutdown: Ensures clean teardown of services on exit
5. Path Discovery: Locates configuration files in development and production environments

This module serves as the main entry point for running the complete OrKa service stack.
It can be executed directly to start all necessary services:

```bash
python -m orka.orka_start
```

Once started, the services will run until interrupted (e.g., Ctrl+C), at which point
they will be gracefully shut down.
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_docker_dir() -> str:
    """
    Get the path to the docker directory containing Docker Compose configuration.

    This function attempts to locate the docker directory in both development and
    production environments by checking multiple possible locations.

    Returns:
        str: Absolute path to the docker directory

    Raises:
        FileNotFoundError: If the docker directory cannot be found in any of the
            expected locations
    """
    # Try to find the docker directory in the installed package
    try:
        import orka

        package_path: Path = Path(orka.__file__).parent
        docker_dir: Path = package_path / "docker"
        if docker_dir.exists():
            return str(docker_dir)
    except ImportError:
        pass

    # Fall back to local project structure
    current_dir: Path = Path(__file__).parent
    docker_dir = current_dir / "docker"
    if docker_dir.exists():
        return str(docker_dir)

    raise FileNotFoundError("Could not find docker directory")


def start_redis() -> None:
    """
    Start the Redis container using Docker Compose.

    This function performs the following steps:
    1. Locates the Docker Compose configuration
    2. Stops any existing containers
    3. Pulls the latest Redis image
    4. Starts the Redis container in detached mode

    Raises:
        subprocess.CalledProcessError: If any of the Docker Compose commands fail
        FileNotFoundError: If the docker directory cannot be found
    """
    docker_dir: str = get_docker_dir()
    print(f"Using Docker directory: {docker_dir}")

    # Stop any existing containers
    print("Stopping any existing containers...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            os.path.join(docker_dir, "docker-compose.yml"),
            "down",
        ],
        check=False,
    )

    # Pull latest images
    print("Pulling latest images...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            os.path.join(docker_dir, "docker-compose.yml"),
            "pull",
        ],
        check=True,
    )

    # Start Redis
    logger.info("Starting containers...")
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            os.path.join(docker_dir, "docker-compose.yml"),
            "up",
            "-d",
            "redis",
        ],
        check=True,
    )
    logger.info("Redis started.")


def start_backend() -> subprocess.Popen:
    """
    Start the OrKa backend server as a separate process.

    This function launches the OrKa server module in a subprocess,
    allowing it to run independently while still being monitored by
    this parent process.

    Returns:
        subprocess.Popen: The process object representing the running backend

    Raises:
        Exception: If the backend fails to start for any reason
    """
    logger.info("Starting Orka backend...")
    try:
        # Start the backend server
        backend_proc: subprocess.Popen = subprocess.Popen(
            [sys.executable, "-m", "orka.server"]
        )
        logger.info("Orka backend started.")
        return backend_proc
    except Exception as e:
        logger.info(f"Error starting Orka backend: {e}")
        raise


async def main() -> None:
    """
    Main entry point for starting and managing OrKa services.

    This asynchronous function:
    1. Starts the Redis container
    2. Launches the OrKa backend server
    3. Monitors the backend process to ensure it's running
    4. Handles graceful shutdown on keyboard interrupt

    The function runs until interrupted (e.g., via Ctrl+C), at which point
    it cleans up all started processes and containers.
    """
    start_redis()
    backend_proc: subprocess.Popen = start_backend()
    logger.info("All services started. Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(1)
            # Check if backend process is still running
            if backend_proc.poll() is not None:
                logger.info("Orka backend stopped unexpectedly!")
                break
    except KeyboardInterrupt:
        logger.info("\nStopping services...")
        backend_proc.terminate()
        backend_proc.wait()
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                os.path.join(get_docker_dir(), "docker-compose.yml"),
                "down",
            ],
            check=False,
        )
        logger.info("Services stopped.")


if __name__ == "__main__":
    asyncio.run(main())
