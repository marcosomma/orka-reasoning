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
from typing import Any, Dict, List, Union

from orka.orchestrator import Orchestrator

from .types import Event

logger = logging.getLogger(__name__)


async def run_cli_entrypoint(
    config_path: str,
    input_text: str,
    log_to_file: bool = False,
) -> Union[Dict[str, Any], List[Event], str]:
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
