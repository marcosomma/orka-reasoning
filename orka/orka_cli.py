# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

import argparse
import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict, Union

from orka.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class EventPayload(TypedDict):
    """Type definition for event payload."""

    message: str
    status: str
    data: Optional[Dict[str, Any]]


class Event(TypedDict):
    """Type definition for event structure."""

    agent_id: str
    event_type: str
    timestamp: str
    payload: EventPayload
    run_id: Optional[str]
    step: Optional[int]


async def main() -> None:
    """
    Main entry point for the OrKa CLI.
    Parses command-line arguments, initializes the orchestrator, and runs it with the provided input.
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

    Args:
        config_path: Path to the YAML configuration file.
        input_text: Input question or statement for the orchestrator.
        log_to_file: If True, save the orchestration trace to a log file.

    Returns:
        The result of the orchestration run.
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
