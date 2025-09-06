#!/usr/bin/env python3
"""
OrKa Emergency Cleanup Tool
===========================

This script provides comprehensive cleanup of OrKa services and Docker containers
when normal shutdown fails or OrKa crashes, leaving containers in a bad state.

Usage:
    python orka_cleanup.py [--force] [--redis-only] [--kafka-only]

Options:
    --force      Force removal of containers even if they appear healthy
    --redis-only Only clean up Redis containers
    --kafka-only Only clean up Kafka containers
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_command(
    cmd: list[str], check: bool = False, capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
        return result
    except subprocess.CalledProcessError as e:
        if not check:
            return e
        raise


def stop_orka_processes():
    """Stop any running OrKa processes."""
    logger.info("🔍 Looking for OrKa processes...")

    # Find OrKa processes
    try:
        result = run_command(["pgrep", "-f", "orka"], capture_output=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    logger.info(f"🛑 Stopping OrKa process {pid}")
                    run_command(["kill", "-TERM", pid])
                    time.sleep(2)
                    # Force kill if still running
                    result = run_command(["kill", "-0", pid])
                    if result.returncode == 0:
                        logger.warning(f"⚠️ Force killing process {pid}")
                        run_command(["kill", "-KILL", pid])
    except Exception as e:
        logger.warning(f"Error stopping processes: {e}")


def cleanup_docker_containers(service_filter: str = None, force: bool = False):
    """Clean up OrKa Docker containers."""
    logger.info("🐳 Cleaning up Docker containers...")

    # Get OrKa project directory
    orka_dir = Path(__file__).parent
    docker_dir = orka_dir / "orka" / "docker"
    compose_file = docker_dir / "docker-compose.yml"

    if not compose_file.exists():
        logger.error(f"❌ Docker compose file not found: {compose_file}")
        return

    # Services to clean up
    services = ["redis", "kafka", "zookeeper", "schema-registry", "schema-registry-ui"]

    if service_filter == "redis":
        services = ["redis"]
    elif service_filter == "kafka":
        services = ["kafka", "zookeeper", "schema-registry", "schema-registry-ui"]

    for service in services:
        logger.info(f"🛑 Stopping {service} container...")

        # Stop the service
        run_command(["docker-compose", "-f", str(compose_file), "stop", service])

        # Remove the container
        run_command(["docker-compose", "-f", str(compose_file), "rm", "-f", service])

    # If force cleanup, also remove volumes and networks
    if force:
        logger.info("🧹 Force cleanup - removing volumes and networks...")

        # Remove volumes
        run_command(["docker-compose", "-f", str(compose_file), "down", "--volumes"])

        # Remove OrKa networks
        networks = [
            "orka-redis-network",
            "orka-kafka-network",
            "docker_orka-redis-network",
            "docker_orka-kafka-network",
        ]
        for network in networks:
            result = run_command(["docker", "network", "rm", network])
            if result.returncode == 0:
                logger.info(f"✅ Removed network: {network}")


def cleanup_redis_data(force: bool = False):
    """Clean up Redis data if needed."""
    if force:
        logger.info("🗑️ Cleaning Redis data...")
        try:
            # Try to connect and flush
            import redis

            client = redis.Redis(host="localhost", port=6380, decode_responses=True)
            client.flushall()
            logger.info("✅ Redis data flushed")
        except Exception as e:
            logger.warning(f"⚠️ Could not flush Redis data: {e}")


def check_port_usage():
    """Check if OrKa ports are still in use."""
    logger.info("🔍 Checking port usage...")

    ports = [6380, 9092, 2181, 8081, 8082, 8001]
    for port in ports:
        result = run_command(["netstat", "-an"], capture_output=True)
        if result.returncode == 0 and f":{port}" in result.stdout:
            logger.warning(f"⚠️ Port {port} still in use")
        else:
            logger.info(f"✅ Port {port} is free")


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="OrKa Emergency Cleanup Tool")
    parser.add_argument("--force", action="store_true", help="Force cleanup including data")
    parser.add_argument("--redis-only", action="store_true", help="Only clean Redis")
    parser.add_argument("--kafka-only", action="store_true", help="Only clean Kafka")

    args = parser.parse_args()

    logger.info("🚀 Starting OrKa cleanup...")

    # Determine service filter
    service_filter = None
    if args.redis_only:
        service_filter = "redis"
    elif args.kafka_only:
        service_filter = "kafka"

    try:
        # Step 1: Stop OrKa processes
        stop_orka_processes()

        # Step 2: Clean up Docker containers
        cleanup_docker_containers(service_filter, args.force)

        # Step 3: Clean up Redis data if force mode
        if args.force and (not args.kafka_only):
            cleanup_redis_data(args.force)

        # Step 4: Check port usage
        check_port_usage()

        logger.info("🎉 Cleanup completed successfully!")
        logger.info("💡 You can now restart OrKa with: orka-start")

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

