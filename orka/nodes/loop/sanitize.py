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

from __future__ import annotations

from typing import Any, Optional


def create_safe_result(result: Any) -> Any:
    """Create a safe, serializable version of the result that avoids circular references.

    Mirrors LoopNode._create_safe_result behavior.
    """

    def _make_safe(obj: Any, seen: Optional[set[int]] = None) -> Any:
        if seen is None:
            seen = set()

        obj_id = id(obj)
        if obj_id in seen:
            return "<circular_reference>"

        if obj is None:
            return None

        if isinstance(obj, (str, int, float, bool)):
            return obj

        seen.add(obj_id)

        try:
            if isinstance(obj, list):
                return [_make_safe(item, seen.copy()) for item in obj]

            if isinstance(obj, dict):
                return {
                    str(key): _make_safe(value, seen.copy())
                    for key, value in obj.items()
                    if key not in ("previous_outputs", "payload")
                }

            s = str(obj)
            return s[:1000] + "..." if len(s) > 1000 else s

        finally:
            seen.discard(obj_id)

    return _make_safe(result)


def create_safe_result_with_context(result: Any) -> Any:
    """Create a safe, serializable version of the result that preserves important loop context.

    Mirrors LoopNode._create_safe_result_with_context behavior.
    """

    def _make_safe_with_context(obj: Any, seen: Optional[set[int]] = None, depth: int = 0) -> Any:
        if seen is None:
            seen = set()

        if depth > 10:
            return "<max_depth_reached>"

        obj_id = id(obj)
        if obj_id in seen:
            return "<circular_reference>"

        if obj is None:
            return None

        if isinstance(obj, (str, int, float, bool)):
            return obj

        seen.add(obj_id)

        try:
            if isinstance(obj, list):
                return [_make_safe_with_context(item, seen.copy(), depth + 1) for item in obj]

            if isinstance(obj, dict):
                safe_dict: dict[str, Any] = {}
                for key, value in obj.items():
                    key_str = str(key)

                    # Always preserve past_loops for context
                    if key_str == "past_loops":
                        safe_dict[key_str] = _make_safe_with_context(value, seen.copy(), depth + 1)
                        continue

                    # Preserve agent responses for cognitive debate context
                    if any(
                        agent_type in key_str.lower()
                        for agent_type in [
                            "progressive",
                            "conservative",
                            "realist",
                            "purist",
                            "agreement",
                        ]
                    ):
                        if isinstance(value, dict):
                            agent_dict: dict[str, Any] = {}
                            for agent_key, agent_value in value.items():
                                if agent_key == "response":
                                    response_str = str(agent_value)
                                    if len(response_str) > 2000:
                                        agent_dict[agent_key] = response_str[:2000] + "...<truncated_for_safety>"
                                    else:
                                        agent_dict[agent_key] = response_str
                                elif agent_key in ["confidence", "internal_reasoning"]:
                                    s = str(agent_value)
                                    agent_dict[agent_key] = s[:500] if len(s) > 500 else agent_value
                                # Skip large metadata like _metrics, formatted_prompt
                            safe_dict[key_str] = agent_dict
                        else:
                            s = str(value)
                            safe_dict[key_str] = s[:1000] if len(s) > 1000 else value
                        continue

                    # Skip problematic circular references but preserve simple values
                    if key_str in ("previous_outputs", "payload"):
                        continue

                    if isinstance(value, (str, int, float, bool, type(None))):
                        safe_dict[key_str] = value
                    elif isinstance(value, (dict, list)):
                        safe_dict[key_str] = _make_safe_with_context(value, seen.copy(), depth + 1)
                    else:
                        s = str(value)
                        safe_dict[key_str] = s[:1000] if len(s) > 1000 else s

                return safe_dict

            s = str(obj)
            return s[:1000] + "..." if len(s) > 1000 else s

        finally:
            seen.discard(obj_id)

    return _make_safe_with_context(result)


