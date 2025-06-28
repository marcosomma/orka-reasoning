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
from typing import Dict, Optional

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
    """Get the configured memory backend, defaulting to RedisStack."""
    backend = os.getenv("ORKA_MEMORY_BACKEND", "redisstack").lower()
    if backend not in ["redis", "redisstack", "kafka", "dual"]:
        logger.warning(f"Unknown backend '{backend}', defaulting to RedisStack")
        return "redisstack"
    return backend


def start_infrastructure(backend: str) -> Dict[str, subprocess.Popen]:
    """
    Start the infrastructure services natively.

    Redis will be started as a native process on port 6380.
    Kafka services will still use Docker when needed.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')

    Returns:
        Dict[str, subprocess.Popen]: Dictionary of started processes

    Raises:
        RuntimeError: If Redis Stack is not available or fails to start
        subprocess.CalledProcessError: If Kafka Docker services fail to start
    """
    processes = {}

    print(f"Starting {backend.upper()} backend...")

    # Always start Redis natively for all backends (except when explicitly using Docker)
    if backend in ["redis", "redisstack", "kafka", "dual"]:
        redis_proc = start_native_redis(6380)
        if redis_proc is not None:
            processes["redis"] = redis_proc
        # If redis_proc is None, Redis is running via Docker and managed by Docker daemon

    # Start Kafka services via Docker only when needed
    if backend in ["kafka", "dual"]:
        start_kafka_docker()

    return processes


def start_native_redis(port: int = 6380) -> Optional[subprocess.Popen]:
    """
    Start Redis Stack natively on the specified port, with Docker fallback.

    Args:
        port: Port to start Redis on (default: 6380)

    Returns:
        subprocess.Popen: The Redis process, or None if using Docker

    Raises:
        RuntimeError: If both native and Docker Redis fail to start
    """
    try:
        # Check if Redis Stack is available natively
        print("🔍 Checking Redis Stack availability...")
        result = subprocess.run(
            ["redis-stack-server", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print(f"🔧 Starting Redis Stack natively on port {port}...")

            # Create data directory if it doesn't exist
            data_dir = Path("./redis-data")
            data_dir.mkdir(exist_ok=True)

            # Start Redis Stack with vector capabilities and persistence
            redis_proc = subprocess.Popen(
                [
                    "redis-stack-server",
                    "--port",
                    str(port),
                    "--appendonly",
                    "yes",
                    "--dir",
                    str(data_dir),
                    "--save",
                    "900 1",  # Save if at least 1 key changed in 900 seconds
                    "--save",
                    "300 10",  # Save if at least 10 keys changed in 300 seconds
                    "--save",
                    "60 10000",  # Save if at least 10000 keys changed in 60 seconds
                    "--maxmemory-policy",
                    "allkeys-lru",  # LRU eviction policy
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for Redis to be ready
            _wait_for_redis(port)

            print(f"✅ Redis Stack running natively on port {port}")
            return redis_proc
        else:
            raise FileNotFoundError("Redis Stack not found in PATH")

    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Redis Stack not found natively.")
        print("🐳 Falling back to Docker Redis Stack...")

        try:
            # Use Docker fallback
            return start_redis_docker(port)

        except Exception as docker_error:
            print(f"❌ Docker fallback also failed: {docker_error}")
            print("📦 To fix this, install Redis Stack:")
            print("   • Windows: Download from https://redis.io/download")
            print("   • macOS: brew install redis-stack")
            print("   • Ubuntu: sudo apt install redis-stack-server")
            print("   • Or ensure Docker is available for fallback")
            raise RuntimeError("Both native and Docker Redis Stack unavailable")

    except Exception as e:
        print(f"❌ Failed to start native Redis: {e}")
        raise RuntimeError(f"Redis startup failed: {e}")


def start_redis_docker(port: int = 6380) -> None:
    """
    Start Redis Stack using Docker as a fallback.

    Args:
        port: Port to start Redis on

    Returns:
        None: Docker process is managed by Docker daemon

    Raises:
        RuntimeError: If Docker Redis fails to start
    """
    try:
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        print(f"🔧 Starting Redis Stack via Docker on port {port}...")

        # Stop any existing Redis containers
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "down",
                "redis",
            ],
            check=False,
            capture_output=True,
        )

        # Start Redis Stack via Docker
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

        # Wait for Redis to be ready
        _wait_for_redis(port)

        print(f"✅ Redis Stack running via Docker on port {port}")
        return None  # Docker process managed by daemon

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to start Redis via Docker: {e}")
    except Exception as e:
        raise RuntimeError(f"Docker Redis startup error: {e}")


def _wait_for_redis(port: int, max_attempts: int = 30) -> None:
    """
    Wait for Redis to be ready and responsive (works for both native and Docker).

    Args:
        port: Redis port to check
        max_attempts: Maximum number of connection attempts

    Raises:
        RuntimeError: If Redis doesn't become ready within the timeout
    """
    import time

    print(f"⏳ Waiting for Redis to be ready on port {port}...")

    for attempt in range(max_attempts):
        try:
            # Try to connect using redis-cli first (if available)
            try:
                result = subprocess.run(
                    ["redis-cli", "-p", str(port), "ping"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                if result.returncode == 0 and "PONG" in result.stdout:
                    print(f"✅ Redis is ready on port {port}!")
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass  # redis-cli not available, try alternative

            # Fallback to socket + Redis library check
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                # Additional check with Redis ping
                try:
                    import redis

                    client = redis.Redis(host="localhost", port=port, decode_responses=True)
                    if client.ping():
                        print(f"✅ Redis is ready on port {port}!")
                        return
                except Exception:
                    pass  # Continue trying

        except Exception:
            pass

        if attempt < max_attempts - 1:
            print(f"Redis not ready yet, waiting... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(2)
        else:
            raise RuntimeError(
                f"Redis failed to start on port {port} after {max_attempts} attempts",
            )


def start_kafka_docker() -> None:
    """
    Start Kafka services using Docker Compose.

    Raises:
        subprocess.CalledProcessError: If Docker Compose commands fail
        FileNotFoundError: If docker directory cannot be found
    """
    docker_dir: str = get_docker_dir()
    compose_file = os.path.join(docker_dir, "docker-compose.yml")

    print("🔧 Starting Kafka services via Docker...")

    # Stop any existing Kafka containers (but not Redis)
    print("Stopping any existing Kafka containers...")

    # Stop specific Kafka services instead of using profile to avoid affecting Redis
    kafka_services = ["kafka", "zookeeper", "schema-registry", "schema-registry-ui"]
    for service in kafka_services:
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "stop",
                service,
            ],
            check=False,
            capture_output=True,  # Suppress output for services that might not exist
        )

    # Remove stopped Kafka containers
    for service in kafka_services:
        subprocess.run(
            [
                "docker-compose",
                "-f",
                compose_file,
                "rm",
                "-f",
                service,
            ],
            check=False,
            capture_output=True,  # Suppress output for services that might not exist
        )

    # Wait for cleanup
    import time

    time.sleep(3)

    # Start Kafka services step by step
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

    print("✅ Kafka services started via Docker")


def wait_for_services(backend: str) -> None:
    """
    Wait for infrastructure services to be ready.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
    """
    # Redis is already checked during native startup in start_native_redis()
    # No additional waiting needed for Redis

    if backend in ["kafka", "dual"]:
        print("⏳ Waiting for Kafka services to be ready...")
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        # Wait for Kafka to be ready
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

        # Wait for Schema Registry to be ready
        print("⏳ Waiting for Schema Registry to be ready...")
        for attempt in range(10):
            try:
                import requests

                response = requests.get("http://localhost:8081/subjects", timeout=5)
                if response.status_code == 200:
                    print("✅ Schema Registry is ready!")
                    break
            except Exception:
                if attempt < 9:
                    print(f"Schema Registry not ready yet, waiting... (attempt {attempt + 1}/10)")
                    time.sleep(2)
                else:
                    logger.warning("Schema Registry may not be fully ready, but continuing...")
                    break

        # Initialize Schema Registry schemas at startup
        if backend in ["kafka", "dual"]:
            _initialize_schema_registry()


def _initialize_schema_registry() -> None:
    """
    Initialize schema registry by creating a temporary KafkaMemoryLogger.
    This ensures schemas are registered at startup time.
    """
    try:
        print("🔧 Initializing Schema Registry schemas...")

        # Set environment variables for schema registry
        os.environ["KAFKA_USE_SCHEMA_REGISTRY"] = "true"
        os.environ["KAFKA_SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

        # Import here to avoid circular imports
        from orka.memory_logger import create_memory_logger

        # Create a temporary Kafka memory logger to trigger schema registration
        memory_logger = create_memory_logger(
            backend="kafka",
            bootstrap_servers="localhost:9092",
        )

        # Close the logger immediately since we only needed it for initialization
        if hasattr(memory_logger, "close"):
            memory_logger.close()

        print("✅ Schema Registry schemas initialized successfully!")

    except Exception as e:
        logger.warning(f"Schema Registry initialization failed: {e}")
        logger.warning("Schemas will be registered on first use instead")


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
        env = os.environ.copy()

        # Set backend-specific environment variables
        env["ORKA_MEMORY_BACKEND"] = backend

        if backend in ["kafka", "dual"]:
            # Configure Kafka with Schema Registry
            env["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
            env["KAFKA_SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
            env["KAFKA_USE_SCHEMA_REGISTRY"] = "true"
            env["KAFKA_TOPIC_PREFIX"] = "orka-memory"
            logger.info("🔧 Schema Registry enabled for Kafka backend")

        if backend in ["redis", "kafka", "dual"]:
            # Configure Redis (now required for all backends including Kafka for memory operations)
            env["REDIS_URL"] = "redis://localhost:6380/0"

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


def cleanup_services(backend: str, processes: Dict[str, subprocess.Popen] = None) -> None:
    """
    Clean up and stop services for the specified backend.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')
        processes: Dictionary of running processes to terminate
    """
    try:
        # Terminate native processes
        if processes:
            for name, proc in processes.items():
                if proc and proc.poll() is None:  # Process is still running
                    print(f"🛑 Stopping {name} process...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        print(f"✅ {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"⚠️ Force killing {name} process...")
                        proc.kill()
                        proc.wait()

        # Stop Docker services for Kafka if needed
        if backend in ["kafka", "dual"]:
            docker_dir: str = get_docker_dir()
            compose_file = os.path.join(docker_dir, "docker-compose.yml")

            logger.info("Stopping Kafka Docker services...")
            subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    compose_file,
                    "--profile",
                    "kafka",
                    "down",
                ],
                check=False,
            )
            print("✅ Kafka Docker services stopped")

        logger.info("All services stopped.")
    except Exception as e:
        logger.error(f"Error stopping services: {e}")


async def main() -> None:
    """
    Main entry point for starting and managing OrKa services.

    This asynchronous function:
    1. Determines which backend to use (Redis, Kafka, or dual)
    2. Starts the appropriate infrastructure services (Redis natively, Kafka via Docker)
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

    if backend in ["redis", "redisstack"]:
        print("📍 Service Endpoints:")
        print("   • Orka API: http://localhost:8000")
        print("   • Redis:    localhost:6380 (native)")
    elif backend == "kafka":
        print("📍 Service Endpoints (Hybrid Kafka + Redis):")
        print("   • Orka API:         http://localhost:8001")
        print("   • Kafka (Events):   localhost:9092")
        print("   • Redis (Memory):   localhost:6380 (native)")
        print("   • Zookeeper:        localhost:2181")
        print("   • Schema Registry:  http://localhost:8081")
        print("   • Schema UI:        http://localhost:8082")
    elif backend == "dual":
        print("📍 Service Endpoints:")
        print("   • Orka API (Dual):  http://localhost:8002")
        print("   • Redis:            localhost:6380 (native)")
        print("   • Kafka:            localhost:9092")
        print("   • Zookeeper:        localhost:2181")
        print("   • Schema Registry:  http://localhost:8081")
        print("   • Schema UI:        http://localhost:8082")

    print("=" * 80)

    # Track all processes for cleanup
    processes = {}
    backend_proc = None

    try:
        # Start infrastructure
        processes = start_infrastructure(backend)

        # Wait for services to be ready
        wait_for_services(backend)

        # Start Orka backend
        backend_proc = start_backend(backend)
        processes["backend"] = backend_proc

        print("")
        print("✅ All services started successfully!")
        print("📝 Press Ctrl+C to stop all services")
        print("")

        # Monitor processes
        while True:
            try:
                await asyncio.sleep(1)
                # Check if backend process is still running
                if backend_proc.poll() is not None:
                    logger.error("Orka backend stopped unexpectedly!")
                    break
            except asyncio.CancelledError:
                # This happens when Ctrl+C is pressed, break out of the loop
                break

    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        print(f"\n❌ Startup failed: {e}")
    finally:
        # Always cleanup processes
        cleanup_services(backend, processes)
        print("✅ All services stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle any remaining KeyboardInterrupt that might bubble up
        print("\n🛑 Shutdown complete.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
