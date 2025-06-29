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
Kafka Infrastructure Management
==============================

This module handles Kafka Docker services management including orchestration
and schema registry initialization.
"""

import logging
import os
import subprocess
import time
from typing import List

from ..config import get_docker_dir

logger = logging.getLogger(__name__)


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


def wait_for_kafka_services() -> None:
    """
    Wait for Kafka services to be ready and responsive.

    Raises:
        RuntimeError: If Kafka services fail to become ready
    """
    print("⏳ Waiting for Kafka services to be ready...")
    docker_dir: str = get_docker_dir()
    compose_file = os.path.join(docker_dir, "docker-compose.yml")

    # Wait for Kafka to be ready
    print("⏳ Waiting for Kafka to be ready...")
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
                raise RuntimeError("Kafka startup timeout")

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


def initialize_schema_registry() -> None:
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


def cleanup_kafka_docker() -> None:
    """Clean up Kafka Docker services."""
    try:
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
    except Exception as e:
        print(f"⚠️ Error stopping Kafka Docker services: {e}")


def get_kafka_services() -> List[str]:
    """
    Get the list of Kafka service names.

    Returns:
        List[str]: List of Kafka service names
    """
    return ["kafka", "zookeeper", "schema-registry", "schema-registry-ui"]
