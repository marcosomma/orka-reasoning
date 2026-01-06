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
Metric Normalization Utilities
==============================

Provides functions to normalize metric values to consistent types.
Ensures confidence is float, tokens are int, costs are float/None, etc.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def normalize_confidence(value: Any, default: float = 0.0) -> float:
    """Normalize confidence to float in range [0.0, 1.0].

    Args:
        value: Input confidence value (str, int, float, None)
        default: Default value if conversion fails

    Returns:
        float: Normalized confidence value clamped to [0.0, 1.0]
    """
    if value is None:
        return default

    try:
        conf = float(value)
        # Clamp to valid range
        return max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        logger.warning(f"Invalid confidence value: {value!r}, using default {default}")
        return default


def normalize_cost(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Normalize cost_usd to float or None.

    Args:
        value: Input cost value
        default: Default value if conversion fails

    Returns:
        float or None: Normalized cost value (None for local LLMs)
    """
    if value is None:
        return default

    try:
        cost = float(value)
        return cost if cost >= 0 else default
    except (TypeError, ValueError):
        return default


def normalize_tokens(value: Any, default: int = 0) -> int:
    """Normalize token count to non-negative integer.

    Args:
        value: Input token count
        default: Default value if conversion fails

    Returns:
        int: Normalized token count (non-negative)
    """
    if value is None:
        return default

    try:
        tokens = int(value)
        return max(0, tokens)
    except (TypeError, ValueError):
        return default


def normalize_latency(value: Any, default: float = 0.0) -> float:
    """Normalize latency_ms to non-negative float.

    Args:
        value: Input latency value
        default: Default value if conversion fails

    Returns:
        float: Normalized latency in milliseconds (non-negative)
    """
    if value is None:
        return default

    try:
        latency = float(value)
        return max(0.0, latency)
    except (TypeError, ValueError):
        return default


def normalize_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all metrics in a _metrics dict.

    Args:
        metrics: Raw metrics dictionary

    Returns:
        dict: Normalized metrics with correct types
    """
    if not isinstance(metrics, dict):
        return {}

    normalized = dict(metrics)  # Shallow copy

    # Normalize known fields
    if "confidence" in normalized:
        normalized["confidence"] = normalize_confidence(normalized["confidence"])
    if "cost_usd" in normalized:
        normalized["cost_usd"] = normalize_cost(normalized["cost_usd"])
    if "tokens" in normalized:
        normalized["tokens"] = normalize_tokens(normalized["tokens"])
    if "prompt_tokens" in normalized:
        normalized["prompt_tokens"] = normalize_tokens(normalized["prompt_tokens"])
    if "completion_tokens" in normalized:
        normalized["completion_tokens"] = normalize_tokens(normalized["completion_tokens"])
    if "latency_ms" in normalized:
        normalized["latency_ms"] = normalize_latency(normalized["latency_ms"])

    return normalized


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize metrics in a payload dictionary.

    Args:
        payload: Agent payload dictionary

    Returns:
        dict: Payload with normalized metrics
    """
    if not isinstance(payload, dict):
        return payload

    normalized = dict(payload)

    # Normalize top-level confidence
    if "confidence" in normalized:
        normalized["confidence"] = normalize_confidence(normalized["confidence"])

    # Normalize nested _metrics
    if "_metrics" in normalized and isinstance(normalized["_metrics"], dict):
        normalized["_metrics"] = normalize_metrics(normalized["_metrics"])

    return normalized
