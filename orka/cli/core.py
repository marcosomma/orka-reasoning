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
CLI Core Functionality
======================

This module contains the core CLI functionality including the programmatic entry point
for running OrKa workflows.
"""

import logging
from typing import Any

from orka.orchestrator import Orchestrator

from .types import Event

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging for the OrKa CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set specific loggers to DEBUG level
    kafka_logger = logging.getLogger("orka.memory.kafka_logger")
    kafka_logger.setLevel(logging.DEBUG)

    redis_logger = logging.getLogger("orka.memory.redisstack_logger")
    redis_logger.setLevel(logging.DEBUG)

    memory_logger = logging.getLogger("orka.memory_logger")
    memory_logger.setLevel(logging.DEBUG)


async def run_cli_entrypoint(
    config_path: str,
    input_text: str,
    log_to_file: bool = False,
) -> dict[str, Any] | list[Event] | str:
    """
    🚀 **Primary programmatic entry point** - run OrKa workflows from any application.

    **What makes this special:**
    - **Universal Integration**: Call OrKa from any Python application seamlessly
    - **Flexible Output**: Returns structured data perfect for further processing
    - **Production Ready**: Handles errors gracefully with comprehensive logging
    - **Development Friendly**: Optional file logging for debugging workflows

    **Integration Patterns:**

    **1. Simple Q&A Integration:**
    ```python
    result = await run_cli_entrypoint(
        "configs/qa_workflow.yml",
        "What is machine learning?",
        log_to_file=False
    )
    # Returns: {"answer_agent": "Machine learning is..."}
    ```

    **2. Complex Workflow Integration:**
    ```python
    result = await run_cli_entrypoint(
        "configs/content_moderation.yml",
        user_generated_content,
        log_to_file=True  # Debug complex workflows
    )
    # Returns: {"safety_check": True, "sentiment": "positive", "topics": ["tech"]}
    ```

    **3. Batch Processing Integration:**
    ```python
    results = []
    for item in dataset:
        result = await run_cli_entrypoint(
            "configs/classifier.yml",
            item["text"],
            log_to_file=False
        )
        results.append(result)
    ```

    **Return Value Intelligence:**
    - **Dict**: Agent outputs mapped by agent ID (most common)
    - **List**: Complete event trace for debugging complex workflows
    - **String**: Simple text output for basic workflows

    **Perfect for:**
    - Web applications needing AI capabilities
    - Data processing pipelines with AI components
    - Microservices requiring intelligent decision making
    - Research applications with custom AI workflows
    """
    setup_logging()
    orchestrator = Orchestrator(config_path)
    result = await orchestrator.run(input_text)

    if log_to_file:
        with open("orka_trace.log", "w") as f:
            f.write(str(result))
    elif isinstance(result, dict):
        for agent_id, value in result.items():
            logger.info(f"{agent_id}: {value}")
    elif isinstance(result, list):
        for event in result:
            agent_id = event.get("agent_id", "unknown")
            payload = event.get("payload", {})
            logger.info(f"Agent: {agent_id} | Payload: {payload}")
    else:
        logger.info(result)

    return result  # <--- VERY IMPORTANT for your test to receive it


def run_cli(argv: list[str]) -> int:
    """Run the CLI with the given arguments."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="OrKa CLI")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument("config", help="Path to YAML config file")
    parser.add_argument("input", help="Input text for the workflow")
    parser.add_argument("--log-to-file", action="store_true", help="Log output to file")

    args = parser.parse_args(argv)

    if args.command == "run":
        result = asyncio.run(run_cli_entrypoint(args.config, args.input, args.log_to_file))
        return 0 if result else 1

    return 1
