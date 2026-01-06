# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
CLI Core Functionality
======================

This module contains the core CLI functionality including the programmatic entry point
for running OrKa workflows.
"""


import logging
import sys
from typing import Any
import argparse
import asyncio
import json

from orka.orchestrator import Orchestrator
from .types import Event
from .utils import setup_logging

logger = logging.getLogger(__name__)


def sanitize_for_console(text: str) -> str:
    """
    Sanitize text for Windows console output by replacing problematic Unicode characters.

    Handles characters that can't be encoded in Windows cp1252 charset.
    """
    # Replace common Unicode characters that cause issues
    replacements = {
        "\u2011": "-",  # Non-breaking hyphen -> regular hyphen
        "\u2013": "-",  # En dash -> hyphen
        "\u2014": "--",  # Em dash -> double hyphen
        "\u2018": "'",  # Left single quote -> apostrophe
        "\u2019": "'",  # Right single quote -> apostrophe
        "\u201a": ",",  # Single low quote -> comma
        "\u201c": '"',  # Left double quote -> quote
        "\u201d": '"',  # Right double quote -> quote
        "\u201e": '"',  # Double low quote -> quote
        "\u2026": "...",  # Ellipsis -> three dots
        "\u202f": " ",  # Narrow no-break space -> space
        "\u00a0": " ",  # Non-breaking space -> space
    }

    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)

    # Handle any remaining problematic characters
    try:
        # Try encoding with the console's encoding
        console_encoding = sys.stdout.encoding or "utf-8"
        text.encode(console_encoding)
        return text
    except (UnicodeEncodeError, AttributeError):
        # If still problematic, use ASCII with error handling
        return text.encode("ascii", errors="replace").decode("ascii")


def deep_sanitize_result(obj: Any) -> Any:
    """Recursively sanitize all strings in nested data structures."""
    if isinstance(obj, str):
        return sanitize_for_console(obj)
    elif isinstance(obj, dict):
        return {deep_sanitize_result(k): deep_sanitize_result(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_sanitize_result(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(deep_sanitize_result(item) for item in obj)
    else:
        return obj


async def run_cli_entrypoint(
    config_path: str,
    input_text: Any,
    log_to_file: bool = False,
    verbose: bool = False,
) -> dict[str, Any] | list[Event] | str:
    """
    [START] **Primary programmatic entry point** - run OrKa workflows from any application.

    **What makes this special:**
    - **Universal Integration**: Call OrKa from any Python application seamlessly
    - **Flexible Output**: Returns structured data perfect for further processing
    - **Production Ready**: Handles errors gracefully with comprehensive logging
    - **Development Friendly**: Optional file logging for debugging workflows

    **Integration Patterns:**

    **1. Simple Q&A Integration:**

    .. code-block:: python

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

    **3. Batch Processing Integration:**

    .. code-block:: python

        results = []
        for item in dataset:
            result = await run_cli_entrypoint(
                "configs/classifier.yml",
                item["text"],
                log_to_file=False
            )
            results.append(result)

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
    setup_logging(verbose)
    orchestrator = Orchestrator(config_path)
    raw_result = await orchestrator.run(input_text)

    if log_to_file:
        with open("orka_trace.log", "w") as f:
            f.write(str(raw_result))

    # Type check and convert result to match return type
    if isinstance(raw_result, dict):
        return raw_result  # Already a dict[str, Any]
    elif isinstance(raw_result, list):
        # Check if it's a list of Event objects by checking required fields
        if all(
            isinstance(item, dict)
            and "agent_id" in item
            and "event_type" in item
            and "timestamp" in item
            and "payload" in item
            for item in raw_result
        ):
            return raw_result  # List of Event-like dicts
    elif isinstance(raw_result, str):
        return raw_result  # Already a string

    # Convert any other type to string for safety
    result_str = str(raw_result)
    # Sanitize before returning to avoid encoding errors
    return sanitize_for_console(result_str)


def run_cli(argv: list[str] | None = None) -> int:
    """Run the CLI with the given arguments."""
    parser = argparse.ArgumentParser(description="OrKa CLI")
    parser.add_argument("command", choices=["run"], help="Command to execute")
    parser.add_argument("config", help="Path to YAML config file")
    parser.add_argument("input", help="Input text for the workflow")
    parser.add_argument("--log-to-file", action="store_true", help="Log output to file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args(argv)

    if args.command == "run":
        result = asyncio.run(
            run_cli_entrypoint(args.config, args.input, args.log_to_file, args.verbose)
        )
        # Distinguish between None (real failure) and falsy values (valid but empty)
        if result is None:
            logger.warning("Workflow returned None - check configuration")
            return 1
        try:
            # Deep sanitize the entire result structure to remove all Unicode
            result = deep_sanitize_result(result)

            # Now log the sanitized result
            if isinstance(result, dict):
                output = json.dumps(result, indent=4)
                logger.info(output)
            elif isinstance(result, list):
                for item in result:
                    output = json.dumps(item, indent=4)
                    logger.info(output)
            else:
                # Log even empty strings as valid output
                logger.info(str(result) if result else "(empty result)")
            return 0
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            # If Unicode errors still occur, just log success without details
            logger.info(
                "Workflow completed successfully (output contains unsupported characters)"
            )
            return 0
        except Exception as e:
            # For any other error, log with sanitized message
            error_msg = sanitize_for_console(str(e))
            logger.info(
                f"Workflow completed successfully (error displaying output: {error_msg})"
            )
            return 0

    return 1
