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

from typing import Any, Dict, List

from .types import MetadataKey, PastLoopMetadata


def extract_metadata_field(
    field: MetadataKey, past_loops: List[PastLoopMetadata], max_entries: int = 5
) -> str:
    values: list[str] = []
    for loop in reversed(past_loops[-max_entries:]):
        if field in loop and loop[field]:
            values.append(str(loop[field]))
    return " | ".join(values)


def build_dynamic_metadata(
    past_loops_metadata_templates: Dict[MetadataKey, str],
    past_loops: List[PastLoopMetadata],
) -> Dict[str, Any]:
    dynamic_metadata: Dict[str, Any] = {}
    for field_name in past_loops_metadata_templates.keys():
        if field_name in ["insights", "improvements", "mistakes"]:
            dynamic_metadata[field_name] = extract_metadata_field(field_name, past_loops)
        else:
            if past_loops:
                last_loop = past_loops[-1]
                value = last_loop.get(field_name, f"No {field_name} available")
                dynamic_metadata[field_name] = str(value)
            else:
                dynamic_metadata[field_name] = f"No {field_name} available"
    return dynamic_metadata


