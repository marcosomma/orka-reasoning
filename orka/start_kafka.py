#!/usr/bin/env python3
"""
OrKa Kafka Backend Starter
==========================

Simple script to start OrKa with Kafka backend for event streaming
and Redis for memory operations.

This provides the best of both worlds:
- Kafka for persistent event streaming and audit trails
- Redis for fast memory operations and fork/join coordination

This is equivalent to running:
    ORKA_MEMORY_BACKEND=kafka REDIS_URL=redis://localhost:6380/0 python -m orka.orka_start
"""

import os
import sys
from pathlib import Path

# Set Kafka backend (hybrid with Redis for memory)
os.environ["ORKA_MEMORY_BACKEND"] = "kafka"

# Ensure Redis is configured for memory operations
if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = "redis://localhost:6380/0"

# Set default Kafka configuration if not already set
if "KAFKA_BOOTSTRAP_SERVERS" not in os.environ:
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

if "KAFKA_TOPIC_PREFIX" not in os.environ:
    os.environ["KAFKA_TOPIC_PREFIX"] = "orka-memory"

print("🚀 Starting OrKa with Kafka + Redis Hybrid Backend...")
print("📋 Configuration:")
print(f"   • Memory Backend: {os.environ['ORKA_MEMORY_BACKEND']}")
print(f"   • Kafka Servers: {os.environ['KAFKA_BOOTSTRAP_SERVERS']}")
print(f"   • Kafka Topic Prefix: {os.environ['KAFKA_TOPIC_PREFIX']}")
print(f"   • Redis URL: {os.environ['REDIS_URL']}")
print()

# Import and run the main function
if __name__ == "__main__":
    import asyncio

    from orka.orka_start import main

    asyncio.run(main())
