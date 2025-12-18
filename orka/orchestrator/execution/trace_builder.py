import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


class TraceBuilder:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def build_enhanced_trace(self, logs: List[Dict[str, Any]], meta_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build an enhanced trace from logs and memory backend info.

        This extracts template resolution info, recent memory references and includes
        an execution metadata header. It mirrors the previous implementation that
        lived in ExecutionEngine so that behavior remains unchanged.
        """
        enhanced_trace: Dict[str, Any] = {
            "execution_metadata": {
                "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                "total_agents": len(logs),
                "execution_time": datetime.now(UTC).isoformat(),
                "memory_backend": type(getattr(self.orchestrator, "memory", None)).__name__,
                "version": "1.1.0",
            },
            "memory_stats": getattr(self.orchestrator.memory, "get_memory_stats", lambda: {})(),
            "agent_executions": [],
        }

        if meta_report:
            enhanced_trace["meta_report"] = meta_report

        for log_entry in logs:
            enhanced_entry = log_entry.copy()
            agent_id = log_entry.get("agent_id")

            if agent_id:
                try:
                    recent_memories = []
                    if hasattr(self.orchestrator.memory, "search_memories"):
                        recent_memories = self.orchestrator.memory.search_memories(
                            query="", node_id=agent_id, num_results=3, log_type="log"
                        )

                    enhanced_entry["memory_references"] = [
                        {
                            "key": mem.get("key", ""),
                            "timestamp": mem.get("timestamp"),
                            "content_preview": (
                                mem.get("content", "")[:100] + "..."
                                if len(mem.get("content", "")) > 100
                                else mem.get("content", "")
                            ),
                        }
                        for mem in recent_memories
                    ]

                    payload = enhanced_entry.get("payload", {})
                    formatted_prompt = payload.get("formatted_prompt", "")
                    original_prompt = payload.get("prompt", "")

                    enhanced_entry["template_resolution"] = {
                        "has_template": bool(original_prompt),
                        "was_rendered": formatted_prompt != original_prompt,
                        "has_unresolved_vars": self.check_unresolved_variables(formatted_prompt),
                        "variable_count": len(self.extract_template_variables(original_prompt)),
                    }

                except Exception as e:
                    enhanced_entry["enhancement_error"] = str(e)

            enhanced_trace["agent_executions"].append(enhanced_entry)

        return enhanced_trace

    def check_unresolved_variables(self, text: str) -> bool:
        pattern = r"\{\{\s*[^}]+\s*\}\}"
        return bool(re.search(pattern, text))

    def extract_template_variables(self, template: str) -> List[str]:
        pattern = r"\{\{\s*([^}]+)\s*\}\}"
        return [v.strip() for v in re.findall(pattern, template)]
