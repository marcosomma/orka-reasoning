"""
SatelliteStateWriter base node.

Satellites produce typed state patches for the streaming runtime.
This node validates simple schema and returns a patch envelope that the
runtime can forward to the state channel.
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import BaseNode


class SatelliteStateWriter(BaseNode):
    """Create a typed state patch from input.

    Params may include a fixed role (e.g., "summarizer", "intent").
    """

    async def _run_impl(self, input_data: Any) -> Dict[str, Any]:
        # Accept either {section: text} or a raw string to be stored as summary
        if isinstance(input_data, dict):
            state_patch = {k: str(v) for k, v in input_data.items()}
        else:
            state_patch = {"summary": str(input_data)}
        role = str(self.params.get("role", "generic"))
        return {
            "agent_id": self.node_id,
            "role": role,
            "state_patch": state_patch,
            "provenance": {
                "source": role,
                "reason": "node_output",
                "evidence_pointers": [],
                "policy_version": self.params.get("policy_version", "v1"),
            },
        }
