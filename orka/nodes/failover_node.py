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
import logging
from datetime import datetime

from .base_node import BaseNode

logger = logging.getLogger(__name__)


class FailoverNode(BaseNode):
    """
    A node that implements failover logic by trying multiple child nodes in sequence.
    If one child fails, it tries the next one until one succeeds or all fail.
    """

    def __init__(self, node_id, children=None, queue=None, prompt=None, **kwargs):
        """
        Initialize the failover node.

        Args:
            node_id (str): Unique identifier for the node.
            children (list): List of child nodes to try in sequence.
            queue (list): Queue of agents or nodes to be processed.
            prompt (str): Prompt for the node (optional for failover).
            **kwargs: Additional parameters.
        """
        # Call parent constructor
        super().__init__(node_id, prompt or "", queue or [], **kwargs)

        # Set failover-specific attributes
        self.children = children or []
        self.agent_id = node_id  # Ensure agent_id is set for proper identification

    async def _run_impl(self, input_data):
        """
        Run the failover logic by trying each child node in sequence.

        Args:
            input_data: Input data to pass to child nodes.

        Returns:
            dict: Result from the first successful child node.

        Raises:
            RuntimeError: If all child nodes fail.
        """
        last_error = None

        logger.info(
            f"Starting failover with {len(self.children)} children",
        )

        for i, child in enumerate(self.children):
            child_id = getattr(
                child,
                "agent_id",
                getattr(child, "node_id", f"unknown_child_{i}"),
            )
            logger.info(
                f"Trying child {i + 1}/{len(self.children)}: {child_id}",
            )
            try:
                # Render prompt for child before running (fix for {{ input }} template access)
                child_payload = input_data.copy()
                if hasattr(child, "prompt") and child.prompt:
                    try:
                        from jinja2 import Template

                        formatted_prompt = Template(child.prompt).render(**input_data)
                        child_payload["formatted_prompt"] = formatted_prompt
                    except Exception:
                        # If rendering fails, use original prompt as fallback
                        child_payload["formatted_prompt"] = child.prompt

                # Try running the current child node
                if hasattr(child, "run") and callable(child.run):
                    # Check if the child's run method is async
                    import asyncio

                    if asyncio.iscoroutinefunction(child.run):
                        result = await child.run(child_payload)
                    else:
                        result = child.run(child_payload)
                else:
                    logger.error(
                        f"Child '{child_id}' has no run method",
                    )
                    continue

                # Check if result is valid (not None, not empty, and contains meaningful data)
                logger.debug(
                    f"Child '{child_id}' returned result type: {type(result)}",
                )
                if result:
                    logger.debug(
                        f"Result preview: {str(result)[:200]}...",
                    )

                if result and self._is_valid_result(result):
                    logger.info(
                        f"Agent '{child_id}' succeeded",
                    )
                    # Return result in a more accessible format
                    return {
                        "result": result,
                        "successful_child": child_id,
                        child_id: result,  # Keep backward compatibility
                    }
                else:
                    logger.info(
                        f"Agent '{child_id}' returned empty/invalid result",
                    )

            except Exception as e:
                # Log the failure and continue to next child
                last_error = e
                logger.warning(
                    f"Agent '{child_id}' failed: {e}",
                )

                # Add delay before trying next child to avoid rate limiting
                if "ratelimit" in str(e).lower() or "rate" in str(e).lower():
                    import asyncio

                    logger.info(
                        f"Rate limit detected, waiting 2 seconds before next attempt",
                    )
                    await asyncio.sleep(2)

        # If we get here, all children failed
        error_msg = (
            f"All fallback agents failed. Last error: {last_error}"
            if last_error
            else "All fallback agents failed."
        )
        logger.error(f"{datetime.now()} > [ORKA][NODE][FAILOVER][ERROR] {error_msg}")

        # Return structured error result instead of raising exception
        return {
            "result": error_msg,
            "status": "failed",
            "successful_child": None,
            "error": str(last_error) if last_error else "All children failed",
        }

    def _is_valid_result(self, result):
        """
        Check if a result is valid and meaningful.

        Args:
            result: The result to validate

        Returns:
            bool: True if result is valid, False otherwise
        """
        if not result:
            return False

        # If result is a dict, check for meaningful content
        if isinstance(result, dict):
            # Check for common success indicators
            if result.get("status") == "error":
                return False

            # Check for response content
            if "response" in result:
                response = result["response"]
                if not response or response in ["NONE", "", None]:
                    return False
                # Check if response contains HTML tags (likely irrelevant web search results)
                if isinstance(response, str) and ("<" in response and ">" in response):
                    if "tag" in response.lower() or "html" in response.lower():
                        return False

            # Check for result content
            if "result" in result:
                inner_result = result["result"]
                if isinstance(inner_result, dict) and "response" in inner_result:
                    response = inner_result["response"]
                    if not response or response in ["NONE", "", None]:
                        return False
                    # Check for HTML content in nested response
                    if isinstance(response, str) and ("<" in response and ">" in response):
                        if "tag" in response.lower() or "html" in response.lower():
                            return False

        # If result is a list, check if it's not empty and doesn't contain HTML content or error messages
        elif isinstance(result, list):
            if len(result) == 0:
                return False
            # Check if list contains error messages or HTML-like content
            for item in result:
                if isinstance(item, str):
                    item_lower = item.lower()

                    # Check for error messages
                    error_indicators = [
                        "failed",
                        "error",
                        "ratelimit",
                        "rate limit",
                        "timeout",
                        "connection error",
                        "404",
                        "500",
                        "503",
                    ]
                    if any(indicator in item_lower for indicator in error_indicators):
                        logger.debug(
                            f"Rejecting error message: {item[:50]}...",
                        )
                        return False

                    # More comprehensive HTML detection
                    if (
                        ("<" in item and ">" in item)
                        or "tag" in item_lower
                        or "html" in item_lower
                        or "element" in item_lower
                    ):
                        # Additional checks for common HTML-related terms
                        html_indicators = [
                            "input",
                            "form",
                            "attribute",
                            "w3schools",
                            "css",
                            "javascript",
                            "web-based",
                        ]
                        if any(indicator in item_lower for indicator in html_indicators):
                            logger.debug(
                                f"Rejecting HTML content: {item[:50]}...",
                            )
                            return False

        # If result is a string, check if it's meaningful and not HTML or error message
        elif isinstance(result, str):
            if result in ["NONE", "", None]:
                return False

            result_lower = result.lower()

            # Check for error messages
            error_indicators = [
                "failed",
                "error",
                "ratelimit",
                "rate limit",
                "timeout",
                "connection error",
                "404",
                "500",
                "503",
            ]
            if any(indicator in result_lower for indicator in error_indicators):
                logger.error(
                    f"{datetime.now()} > [ORKA][NODE][FAILOVER][DEBUG] Rejecting error message: {result[:50]}...",
                )
                return False

            # Check for HTML content
            if "<" in result and ">" in result:
                if "tag" in result_lower or "html" in result_lower:
                    return False

        return True
