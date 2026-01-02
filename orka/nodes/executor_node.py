"""
StreamingExecutorNode (placeholder for streaming regime).

This node is registered to keep a consistent node registry. The actual
streaming executor is managed by the streaming runtime in orka.streaming.
"""

from __future__ import annotations

from typing import Any, Dict

from .base_node import BaseNode


class StreamingExecutorNode(BaseNode):
    """Minimal node that echoes composed prompt metadata.

    In batch mode this node is not used; in streaming mode the runtime handles
    token streaming. This node remains functional for completeness and tests.
    """

    async def _run_impl(self, input_data: Any) -> Dict[str, Any]:
        # Expect composer output dict and echo minimal details
        if isinstance(input_data, dict) and "sections" in input_data:
            sections = input_data.get("sections", {})
            return {
                "status": "ok",
                "used_sections": list(sections.keys()),
                "total_tokens": input_data.get("total_tokens", 0),
            }
        return {"status": "ok", "echo": str(input_data)}
