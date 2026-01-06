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

from datetime import datetime
from typing import Any, Dict


class ContextManager:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def ensure_complete_context(self, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure previous_outputs has complete, template-friendly context.

        Ported from ExecutionEngine._ensure_complete_context.
        """
        enhanced_outputs: Dict[str, Any] = {}

        for agent_id, agent_result in previous_outputs.items():
            enhanced_outputs[agent_id] = agent_result

            if isinstance(agent_result, dict):
                if "memories" in agent_result and isinstance(agent_result["memories"], list):
                    enhanced_outputs[agent_id] = {
                        **agent_result,
                        "memories": agent_result["memories"],
                    }

                elif "response" in agent_result:
                    enhanced_outputs[agent_id] = {
                        **agent_result,
                        "response": agent_result["response"],
                        "confidence": agent_result.get("confidence", "0.0"),
                        "internal_reasoning": agent_result.get(
                            "internal_reasoning", ""
                        ),
                        "_metrics": agent_result.get("_metrics", {}),
                        "formatted_prompt": agent_result.get("formatted_prompt", ""),
                    }

                elif "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    if "response" in nested_result:
                        enhanced_outputs[agent_id] = {
                            **agent_result,
                            "response": nested_result["response"],
                            "confidence": nested_result.get("confidence", "0.0"),
                            "internal_reasoning": nested_result.get(
                                "internal_reasoning", ""
                            ),
                            "_metrics": nested_result.get("_metrics", {}),
                            "formatted_prompt": nested_result.get("formatted_prompt", ""),
                        }
                    elif "memories" in nested_result:
                        enhanced_outputs[agent_id] = {
                            **agent_result,
                            "memories": nested_result["memories"],
                            "query": nested_result.get("query", ""),
                            "backend": nested_result.get("backend", ""),
                            "search_type": nested_result.get("search_type", ""),
                            "num_results": nested_result.get("num_results", 0),
                        }

                elif "status" in agent_result:
                    enhanced_outputs[agent_id] = {
                        **agent_result,
                        "status": agent_result["status"],
                        "fork_group": agent_result.get("fork_group", ""),
                        "merged": agent_result.get("merged", {}),
                    }

                else:
                    enhanced_outputs[agent_id] = agent_result

            else:
                enhanced_outputs[agent_id] = agent_result

        return enhanced_outputs

    def build_template_context(self, payload: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """Build the template rendering context.

        Ported from ExecutionEngine._build_template_context.
        """
        context = payload.copy()

        if "previous_outputs" not in context:
            context["previous_outputs"] = {}

        context.update(
            {
                "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                "step_index": getattr(self.orchestrator, "step_index", 0),
                "agent_id": agent_id,
                "current_time": datetime.now().isoformat(),
                "workflow_name": getattr(self.orchestrator, "workflow_name", "unknown"),
            }
        )

        if "input" in context and isinstance(context["input"], dict):
            input_data = context["input"]
            for var in ["loop_number", "past_loops_metadata", "user_input", "query"]:
                if var in input_data:
                    context[var] = input_data[var]

        prev_outputs = context.get("previous_outputs", {})
        flattened_outputs: Dict[str, Any] = {}

        for agent_name, agent_result in prev_outputs.items():
            simplified_result = self.simplify_agent_result_for_templates(agent_result)
            flattened_outputs[agent_name] = simplified_result

            if isinstance(simplified_result, dict):
                if "response" in simplified_result:
                    flattened_outputs[f"{agent_name}_response"] = simplified_result["response"]
                if "memories" in simplified_result:
                    flattened_outputs[f"{agent_name}_memories"] = simplified_result["memories"]

        context["previous_outputs"] = flattened_outputs
        return context

    def simplify_agent_result_for_templates(self, agent_result: Any) -> Any:
        """Simplify agent result structures for Jinja2 templates.

        Ported from ExecutionEngine._simplify_agent_result_for_templates.
        """
        if not isinstance(agent_result, dict):
            return agent_result

        simplified = agent_result.copy()

        if "response" in agent_result:
            simplified["response"] = agent_result["response"]
            if "confidence" in agent_result:
                simplified["confidence"] = agent_result["confidence"]
            if "internal_reasoning" in agent_result:
                simplified["internal_reasoning"] = agent_result["internal_reasoning"]
            return simplified

        if "result" in agent_result and isinstance(agent_result["result"], dict):
            nested_result = agent_result["result"]
            if "response" in nested_result:
                simplified["response"] = nested_result["response"]
            if "confidence" in nested_result:
                simplified["confidence"] = nested_result.get("confidence", "0.0")
            if "internal_reasoning" in nested_result:
                simplified["internal_reasoning"] = nested_result.get("internal_reasoning", "")
            if "_metrics" in nested_result:
                simplified["_metrics"] = nested_result.get("_metrics", {})
            if "formatted_prompt" in nested_result:
                simplified["formatted_prompt"] = nested_result.get("formatted_prompt", "")

            if "memories" in nested_result:
                simplified["memories"] = nested_result["memories"]
                simplified["query"] = nested_result.get("query", "")
                simplified["backend"] = nested_result.get("backend", "")
                simplified["search_type"] = nested_result.get("search_type", "")
                simplified["num_results"] = nested_result.get("num_results", 0)

            simplified["result"] = nested_result
            return simplified

        if "memories" in agent_result:
            simplified["memories"] = agent_result["memories"]
            simplified["query"] = agent_result.get("query", "")
            simplified["backend"] = agent_result.get("backend", "")
            simplified["search_type"] = agent_result.get("search_type", "")
            simplified["num_results"] = agent_result.get("num_results", 0)
            return simplified

        if "merged" in agent_result and isinstance(agent_result["merged"], dict):
            for merged_agent_id, merged_result in agent_result["merged"].items():
                if isinstance(merged_result, dict) and "response" in merged_result:
                    simplified[f"{merged_agent_id}_response"] = merged_result["response"]
            simplified["merged"] = agent_result["merged"]
            return simplified

        return simplified
