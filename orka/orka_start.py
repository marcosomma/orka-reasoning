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
OrKa Service Runner
==================

This module provides functionality to start and manage the OrKa infrastructure services.
It handles the initialization and lifecycle of Redis/Kafka and the OrKa backend server,
ensuring they are properly configured and running before allowing user workflows
to execute.

Key Features:
-----------
1. Multi-Backend Support: Supports both Redis and Kafka memory backends
2. Infrastructure Management: Automates the startup and shutdown of required services
3. Docker Integration: Manages containers via Docker Compose with profiles
4. Process Management: Starts and monitors the OrKa backend server process
5. Graceful Shutdown: Ensures clean teardown of services on exit
6. Path Discovery: Locates configuration files in development and production environments

This module serves as the main entry point for running the complete OrKa service stack.
It can be executed directly to start all necessary services:

```bash
# Start with Redis backend (default)
python -m orka.orka_start

# Start with Kafka backend
ORKA_MEMORY_BACKEND=kafka python -m orka.orka_start

# Start with dual backend (both Redis and Kafka)
ORKA_MEMORY_BACKEND=dual python -m orka.orka_start
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


def get_memory_backend() -> str:
    """
    Get the configured memory backend from environment variables.

    Returns:
        str: The memory backend type ('redis', 'kafka', or 'dual')
    """
    backend = os.getenv("ORKA_MEMORY_BACKEND", "redis").lower()
    if backend not in ["redis", "kafka", "dual"]:
        logger.warning(f"Unknown backend '{backend}', defaulting to Redis")
        return "redis"
    return backend


def start_infrastructure(backend: str) -> None:
    """
    Start the infrastructure services (Redis, Kafka, or both) using Docker Compose.

    This function performs the following steps:
    1. Locates the Docker Compose configuration
    2. Stops any existing containers for the specified backend
    3. Pulls the latest images
    4. Starts the appropriate containers based on the backend type

    Args:
        backend: The backend type ('redis', 'kafka', or 'dual')

    Raises:
        subprocess.CalledProcessError: If any of the Docker Compose commands fail
        FileNotFoundError: If the docker directory cannot be found
    """
    docker_dir: str = get_docker_dir()
    compose_file = os.path.join(docker_dir, "docker-compose.yml")
    print(f"Using Docker directory: {docker_dir}")
    print(f"Starting {backend.upper()} backend...")

    # Stop any existing containers for this backend
    print("Stopping any existing containers...")
    subprocess.run(
        [
            "docker-compose",
            "-f",
            compose_file,
            "--profile",
            backend,
            "down",
        ],
        check=False,
    )

    # Wait for containers to be fully removed to avoid "marked for removal" errors
    print("Waiting for containers to be fully removed...")
    import time

    time.sleep(5)

    # Ensure any remaining containers are properly cleaned up
    subprocess.run(
        ["docker", "container", "prune", "-f"],
        check=False,
    )

    # Additional wait to ensure cleanup is complete
    time.sleep(2)

    # Pull latest images
    print("Pulling latest images...")
    subprocess.run(
        [
            "docker-compose",
            "-f",
            compose_file,
            "--profile",
            backend,
            "pull",
        ],
        check=True,
    )

    # Start infrastructure services
    logger.info(f"Starting {backend} infrastructure...")
    if backend == "redis":
        # Start Redis service only
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "redis",
            ],
            check=True,
        )
        logger.info("Redis infrastructure started.")

    elif backend == "kafka":
        # Start Kafka services step by step to avoid dependency conflicts
        print("Starting Zookeeper...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "zookeeper",
            ],
            check=True,
        )

        print("Starting Kafka...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "kafka",
            ],
            check=True,
        )

        print("Starting Schema Registry...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "schema-registry",
            ],
            check=True,
        )

        print("Starting Schema Registry UI...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "schema-registry-ui",
            ],
            check=True,
        )

        logger.info("Kafka infrastructure started.")

    elif backend == "dual":
        # Start both Redis and Kafka step by step
        print("Starting Redis...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "redis",
            ],
            check=True,
        )

        print("Starting Zookeeper...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "zookeeper",
            ],
            check=True,
        )

        print("Starting Kafka...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "kafka",
            ],
            check=True,
        )

        print("Starting Schema Registry...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "schema-registry",
            ],
            check=True,
        )

        print("Starting Schema Registry UI...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "up",
                "-d",
                "schema-registry-ui",
            ],
            check=True,
        )

        logger.info("Dual infrastructure (Redis + Kafka) started.")


def wait_for_services(backend: str) -> None:
    """
    Wait for infrastructure services to be ready.

    Args:
        backend: The backend type ('redis', 'kafka', or 'dual')
    """
    docker_dir: str = get_docker_dir()
    compose_file = os.path.join(docker_dir, "docker-compose.yml")

    if backend in ["redis", "dual"]:
        print("⏳ Waiting for Redis to be ready...")
        for attempt in range(10):
            try:
                result = subprocess.run(
                    [
                        "docker-compose",
                        "-f",
                        compose_file,
                        "exec",
                        "-T",
                        "redis",
                        "redis-cli",
                        "ping",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if "PONG" in result.stdout:
                    print("✅ Redis is ready!")
                    break
            except subprocess.CalledProcessError:
                if attempt < 9:
                    print(f"Redis not ready yet, waiting... (attempt {attempt + 1}/10)")
                    import time

                    time.sleep(2)
                else:
                    logger.error("Redis failed to start properly")
                    raise

    if backend in ["kafka", "dual"]:
        print("⏳ Waiting for Kafka to be ready...")
        import time

        time.sleep(15)  # Kafka needs more time to initialize

        for attempt in range(10):
            try:
                subprocess.run(
                    [
                        "docker-compose",
                        "-f",
                        compose_file,
                        "exec",
                        "-T",
                        "kafka",
                        "kafka-topics",
                        "--bootstrap-server",
                        "localhost:29092",
                        "--list",
                    ],
                    check=True,
                    capture_output=True,
                )
                print("✅ Kafka is ready!")
                break
            except subprocess.CalledProcessError:
                if attempt < 9:
                    print(f"Kafka not ready yet, waiting... (attempt {attempt + 1}/10)")
                    time.sleep(3)
                else:
                    logger.error("Kafka failed to start properly")
                    raise


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
        logger.error(f"Error starting Orka backend: {e}")
        raise


def cleanup_services(backend: str) -> None:
    """
    Clean up and stop services for the specified backend.

    Args:
        backend: The backend type ('redis', 'kafka', or 'dual')
    """
    try:
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        logger.info(f"Stopping {backend} services...")
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "--profile",
                backend,
                "down",
            ],
            check=False,
        )
        logger.info("Services stopped.")
    except Exception as e:
        logger.error(f"Error stopping services: {e}")


async def main() -> None:
    """
    Main entry point for starting and managing OrKa services.

    This asynchronous function:
    1. Determines which backend to use (Redis, Kafka, or dual)
    2. Starts the appropriate infrastructure services
    3. Waits for services to be ready
    4. Launches the OrKa backend server
    5. Monitors the backend process to ensure it's running
    6. Handles graceful shutdown on keyboard interrupt

    The function runs until interrupted (e.g., via Ctrl+C), at which point
    it cleans up all started processes and containers.
    """
    # Determine backend type
    backend = get_memory_backend()

    # Display startup information
    print(f"🚀 Starting OrKa with {backend.upper()} backend...")
    print("=" * 80)

    if backend == "redis":
        print("📍 Service Endpoints:")
        print("   • Orka API: http://localhost:8000")
        print("   • Redis:    localhost:6379")
    elif backend == "kafka":
        print("📍 Service Endpoints:")
        print("   • Orka API:    http://localhost:8001")
        print("   • Kafka:       localhost:9092")
        print("   • Zookeeper:   localhost:2181")
    elif backend == "dual":
        print("📍 Service Endpoints:")
        print("   • Orka API (Dual): http://localhost:8002")
        print("   • Redis:           localhost:6379")
        print("   • Kafka:           localhost:9092")
        print("   • Zookeeper:       localhost:2181")

    print("=" * 80)

    # Start infrastructure
    start_infrastructure(backend)

    # Wait for services to be ready
    wait_for_services(backend)

    # Start Orka backend
    backend_proc: subprocess.Popen = start_backend()

    print("")
    print("✅ All services started successfully!")
    print("📝 Press Ctrl+C to stop all services")
    print("")

    try:
        while True:
            await asyncio.sleep(1)
            # Check if backend process is still running
            if backend_proc.poll() is not None:
                logger.error("Orka backend stopped unexpectedly!")
                break
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        backend_proc.terminate()
        backend_proc.wait()
        cleanup_services(backend)
        print("✅ All services stopped.")


if __name__ == "__main__":
    asyncio.run(main())
