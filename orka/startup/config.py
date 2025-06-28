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
Startup Configuration
====================

This module handles configuration management and path discovery for OrKa startup services.
"""

import logging
import os
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
    current_dir: Path = Path(__file__).parent.parent
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


def get_service_endpoints(backend: str) -> dict:
    """
    Get service endpoint configuration for the specified backend.

    Args:
        backend: The backend type ('redis', 'redisstack', 'kafka', or 'dual')

    Returns:
        dict: Dictionary containing service endpoint information
    """
    endpoints = {
        "orka_api": "http://localhost:8000",
        "redis": "localhost:6380",
    }

    if backend in ["redis", "redisstack"]:
        endpoints.update(
            {
                "orka_api": "http://localhost:8000",
                "redis": "localhost:6380 (native)",
            },
        )
    elif backend == "kafka":
        endpoints.update(
            {
                "orka_api": "http://localhost:8001",
                "kafka": "localhost:9092",
                "redis": "localhost:6380 (native)",
                "zookeeper": "localhost:2181",
                "schema_registry": "http://localhost:8081",
                "schema_ui": "http://localhost:8082",
            },
        )
    elif backend == "dual":
        endpoints.update(
            {
                "orka_api": "http://localhost:8002",
                "redis": "localhost:6380 (native)",
                "kafka": "localhost:9092",
                "zookeeper": "localhost:2181",
                "schema_registry": "http://localhost:8081",
                "schema_ui": "http://localhost:8082",
            },
        )

    return endpoints


def configure_backend_environment(backend: str) -> dict:
    """
    Configure environment variables for backend process.

    Args:
        backend: The backend type ('redis', 'kafka', or 'dual')

    Returns:
        dict: Environment variables dictionary
    """
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

    return env
