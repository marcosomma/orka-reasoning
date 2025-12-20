from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def extract_secondary_metric(
    result: Dict[str, Any],
    metric_key: str,
    default: Any = 0.0,
) -> Any:
    """Extract secondary metrics from agent responses.

    Direct extraction of LoopNode._extract_secondary_metric.
    """
    if not isinstance(result, dict):
        return default

    # Search across agent outputs
    for agent_result in result.values():
        if not isinstance(agent_result, dict):
            continue

        # Direct access
        if metric_key in agent_result:
            return agent_result[metric_key]

        # Search in nested common fields
        for nested_key in ["response", "result", "output", "data"]:
            if nested_key not in agent_result:
                continue
            nested_value = agent_result[nested_key]

            if isinstance(nested_value, dict) and metric_key in nested_value:
                return nested_value[metric_key]

            if isinstance(nested_value, str):
                try:
                    parsed = json.loads(nested_value)
                    if isinstance(parsed, dict) and metric_key in parsed:
                        return parsed[metric_key]
                except json.JSONDecodeError:
                    pass

                try:
                    parsed = ast.literal_eval(nested_value)
                    if isinstance(parsed, dict) and metric_key in parsed:
                        return parsed[metric_key]
                except (ValueError, SyntaxError):
                    pass

                pattern = rf"['\"]?{re.escape(metric_key)}['\"]?\s*:\s*['\"]?([^'\",$\}}]+)['\"]?"
                match = re.search(pattern, nested_value)
                if match:
                    value = match.group(1).strip()
                    if metric_key in ["REASONING_QUALITY", "AGREEMENT_SCORE"] and value.replace(".", "").isdigit():
                        try:
                            return float(value)
                        except ValueError:
                            pass
                    return value

    logger.debug(
        "Secondary metric '%s' not found in result, using default: %s",
        metric_key,
        default,
    )
    return default


