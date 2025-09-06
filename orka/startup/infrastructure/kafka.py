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
Kafka Infrastructure Management
==============================

This module handles Kafka Docker services management including orchestration
and schema registry initialization.
"""

import logging
import os
import subprocess
import time

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

    logger.info("🔧 Starting Kafka services via Docker...")

    # Stop any existing Kafka containers (but not Redis)
    logger.info("Stopping any existing Kafka containers...")

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
    logger.info("Starting Zookeeper...")
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

    logger.info("Starting Kafka...")
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

    logger.info("Starting Schema Registry...")
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

    logger.info("Starting Schema Registry UI...")
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

    logger.info("✅ Kafka services started via Docker")


def wait_for_kafka_services() -> None:
    """
    Wait for Kafka services to be ready and responsive.

    Raises:
        RuntimeError: If Kafka services fail to become ready
    """
    logger.info("⏳ Waiting for Kafka services to be ready...")
    docker_dir: str = get_docker_dir()
    compose_file = os.path.join(docker_dir, "docker-compose.yml")

    # Wait for Kafka to be ready
    logger.info("⏳ Waiting for Kafka to be ready...")
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
            logger.info("✅ Kafka is ready!")
            break
        except subprocess.CalledProcessError:
            if attempt < 9:
                logger.info(f"Kafka not ready yet, waiting... (attempt {attempt + 1}/10)")
                time.sleep(3)
            else:
                logger.error("Kafka failed to start properly")
                raise RuntimeError("Kafka startup timeout")

    # Wait for Schema Registry to be ready
    logger.info("⏳ Waiting for Schema Registry to be ready...")

    # Check if Schema Registry container is running
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=docker-schema-registry-1",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"📦 Schema Registry container status: {result.stdout.strip()}")
        else:
            logger.warning("⚠️ Schema Registry container may not be running properly")
    except Exception as e:
        logger.debug(f"Could not check Schema Registry container status: {e}")

    # Give Schema Registry more time to initialize
    time.sleep(10)  # Initial wait for Schema Registry to start

    # Try Docker health check first (more reliable on Windows)
    docker_check_success = False
    try:
        for attempt in range(10):
            try:
                # Use curl inside the container to bypass Windows Docker networking issues
                health_result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "docker-schema-registry-1",
                        "curl",
                        "-s",
                        "http://localhost:8081/subjects",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )

                if health_result.returncode == 0:
                    logger.info("✅ Schema Registry is ready! (verified via Docker)")
                    docker_check_success = True
                    break

            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass

            if attempt < 9:
                logger.info(
                    f"Schema Registry not ready yet, waiting... (Docker check attempt {attempt + 1}/10)"
                )
                time.sleep(3)
            else:
                logger.warning("Docker health check failed, trying host connection...")
                break
    except Exception:
        pass

    # Fallback to host connection test if Docker check failed
    if not docker_check_success:
        for attempt in range(15):  # Increased attempts from 10 to 15
            try:
                import requests

                response = requests.get(
                    "http://localhost:8081/subjects", timeout=10
                )  # Increased timeout
                if response.status_code == 200:
                    logger.info("✅ Schema Registry is ready!")
                    break
            except Exception as e:
                if attempt < 14:
                    wait_time = 3 if attempt < 5 else 5  # Progressive backoff
                    logger.info(
                        f"Schema Registry not ready yet, waiting... (host check attempt {attempt + 1}/15)"
                    )
                    time.sleep(wait_time)
                else:
                    logger.warning("Schema Registry may not be fully ready, but continuing...")
                    logger.debug(f"Last Schema Registry error: {e}")
                    break


def initialize_schema_registry() -> None:
    """
    Initialize schema registry by creating a temporary KafkaMemoryLogger.
    This ensures schemas are registered at startup time.
    """
    try:
        logger.info("🔧 Initializing Schema Registry schemas...")

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
        if hasattr(memory_logger, "_producer") and hasattr(memory_logger._producer, "close"):
            memory_logger._producer.close()
        elif hasattr(memory_logger, "close"):
            memory_logger.close()

        logger.info("✅ Schema Registry schemas initialized successfully!")

    except Exception as e:
        logger.warning(f"Schema Registry initialization failed: {e}")
        logger.warning("Schemas will be registered on first use instead")


def cleanup_kafka_docker() -> None:
    """Clean up Kafka Docker services with enhanced reliability."""
    try:
        docker_dir: str = get_docker_dir()
        compose_file = os.path.join(docker_dir, "docker-compose.yml")

        logger.info("🛑 Stopping Kafka Docker services...")

        # Stop services individually for better control
        kafka_services = ["schema-registry-ui", "schema-registry", "kafka", "zookeeper"]

        for service in kafka_services:
            logger.info(f"🛑 Stopping {service}...")
            subprocess.run(
                ["docker-compose", "-f", compose_file, "stop", service],
                check=False,
                capture_output=True,
                timeout=30,
            )

            subprocess.run(
                ["docker-compose", "-f", compose_file, "rm", "-f", service],
                check=False,
                capture_output=True,
            )

        # Also try profile-based cleanup as fallback
        subprocess.run(
            ["docker-compose", "-f", compose_file, "--profile", "kafka", "down"],
            check=False,
            capture_output=True,
            timeout=30,
        )

        logger.info("✅ Kafka Docker services stopped")
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ Kafka cleanup timed out, forcing container removal...")
        # Force kill containers if they don't stop gracefully
        containers = [
            "docker-schema-registry-ui-1",
            "docker-schema-registry-1",
            "docker-kafka-1",
            "docker-zookeeper-1",
        ]
        for container in containers:
            subprocess.run(["docker", "kill", container], check=False, capture_output=True)
            subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True)
    except Exception as e:
        logger.warning(f"⚠️ Error stopping Kafka Docker services: {e}")


def get_kafka_services() -> list[str]:
    """
    Get the list of Kafka service names.

    Returns:
        List[str]: List of Kafka service names
    """
    return ["kafka", "zookeeper", "schema-registry", "schema-registry-ui"]
