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
OrKa CLI Interface
================

This module provides a command-line interface (CLI) for the OrKa orchestration framework,
allowing users to run OrKa workflows directly from the terminal. It handles command-line
argument parsing, workflow initialization, and result presentation.

Usage:
-----
```bash
python -m orka.orka_cli path/to/config.yml "Your input query"
```

Command-line arguments:
---------------------
- config: Path to the YAML configuration file (required)
- input: Query or input text to process (required)
- --log-to-file: Save execution trace to a JSON log file (optional)

The CLI supports both direct console usage and programmatic invocation through the
`run_cli_entrypoint` function, which can be used by other applications to embed
OrKa functionality.

Example:
-------
```python
import asyncio
from orka.orka_cli import run_cli_entrypoint

async def run_workflow():
    result = await run_cli_entrypoint(
        "workflows/qa_pipeline.yml",
        "What is the capital of France?",
        log_to_file=True
    )
    print(result)

asyncio.run(run_workflow())
```
"""

import argparse
import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict, Union

from orka.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class EventPayload(TypedDict):
    """
    Type definition for event payload.

    Attributes:
        message: Human-readable message about the event
        status: Status of the event (e.g., "success", "error", "in_progress")
        data: Optional structured data associated with the event
    """

    message: str
    status: str
    data: Optional[Dict[str, Any]]


class Event(TypedDict):
    """
    Type definition for event structure.

    Represents a complete event record in the orchestration system.

    Attributes:
        agent_id: Identifier of the agent that generated the event
        event_type: Type of event (e.g., "start", "end", "error")
        timestamp: ISO-format timestamp for when the event occurred
        payload: Structured event payload with message, status, and data
        run_id: Optional identifier for the orchestration run
        step: Optional step number in the orchestration sequence
    """

    agent_id: str
    event_type: str
    timestamp: str
    payload: EventPayload
    run_id: Optional[str]
    step: Optional[int]


async def main() -> None:
    """
    Main entry point for the OrKa CLI.

    Parses command-line arguments, initializes the orchestrator with the specified
    configuration file, and runs it with the provided input text. Results are
    displayed in the console unless the log-to-file option is specified.

    Command-line arguments:
        config: Path to the YAML configuration file
        input: Input question or statement for the orchestrator
        --log-to-file: Flag to save output to a log file instead of console
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Run OrKa with a YAML configuration."
    )
    parser.add_argument("config", help="Path to the YAML configuration file.")
    parser.add_argument(
        "input", help="Input question or statement for the orchestrator."
    )
    parser.add_argument(
        "--log-to-file",
        action="store_true",
        help="Save the orchestration trace to a JSON log file.",
    )
    args: argparse.Namespace = parser.parse_args()

    orchestrator = Orchestrator(config_path=args.config)
    await orchestrator.run(args.input)


async def run_cli_entrypoint(
    config_path: str, input_text: str, log_to_file: bool = False
) -> Union[Dict[str, Any], List[Event], str]:
    """
    Run the OrKa orchestrator with the given configuration and input.

    This function serves as the primary programmatic entry point for running
    OrKa workflows from other applications. It initializes the orchestrator,
    runs the workflow, and handles result formatting and logging.

    Args:
        config_path: Path to the YAML configuration file
        input_text: Input question or statement for the orchestrator
        log_to_file: If True, save the orchestration trace to a log file

    Returns:
        The result of the orchestration run, which can be:
        - A dictionary mapping agent IDs to their outputs
        - A list of event records from the execution
        - A simple string output for basic workflows

    Example:
        ```python
        result = await run_cli_entrypoint(
            "configs/qa_workflow.yml",
            "Who was the first person on the moon?",
            log_to_file=True
        )
        ```
    """
    from orka.orchestrator import Orchestrator

    orchestrator = Orchestrator(config_path)
    result = await orchestrator.run(input_text)

    if log_to_file:
        with open("orka_trace.log", "w") as f:
            f.write(str(result))
    else:
        if isinstance(result, dict):
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


if __name__ == "__main__":
    asyncio.run(main())
