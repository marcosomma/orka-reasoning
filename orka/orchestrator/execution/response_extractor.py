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

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResponseExtractor:
    # Control-flow node types that don't produce user-facing output
    CONTROL_FLOW_TYPES = {
        "forknode", "joinnode", "routernode", "loopnode", "graph-scout",
        "fork", "join", "router", "loop", "graphscout",
    }

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def is_control_flow_agent(self, agent_id: str) -> bool:
        """Check if agent is a control-flow node that doesn't produce user-facing output."""
        if agent_id not in getattr(self.orchestrator, "agents", {}):
            return False
        agent = self.orchestrator.agents[agent_id]
        agent_type = (getattr(agent, "type", "") or "").lower()
        return agent_type in self.CONTROL_FLOW_TYPES

    def is_response_builder(self, agent_id: str) -> bool:
        if agent_id not in getattr(self.orchestrator, "agents", {}):
            return False
        agent = self.orchestrator.agents[agent_id]
        agent_type = getattr(agent, "type", "").lower()
        return (
            any(term in agent_type for term in ["localllm", "local_llm", "answer", "response", "builder"]) 
            and "classification" not in agent_type
            and "response_generation" in getattr(agent, "capabilities", [])
        )

    def _get_best_response_builder(self) -> Optional[str]:
        original_agents = getattr(self.orchestrator, "orchestrator_cfg", {}).get("agents", [])
        response_builders = [a for a in original_agents if self.is_response_builder(a)]
        if not response_builders:
            return None
        for builder in response_builders:
            if "response_builder" in builder.lower():
                return str(builder)
        return str(response_builders[0])

    def validate_and_enforce_terminal_agent(self, queue: List[str]) -> List[str]:
        if not queue:
            return queue
        last_agent_id = queue[-1]
        if self.is_response_builder(last_agent_id):
            logger.info(f"[OK] Terminal validation passed: {last_agent_id} is a response builder")
            return queue
        response_builder = self._get_best_response_builder()
        if response_builder:
            validated_queue = queue + [response_builder]
            logger.info(f"[CONF] Terminal enforcement: Added {response_builder} to ensure LLM response")
            logger.info(f"[LIST] Final validated queue: {validated_queue}")
            return validated_queue
        else:
            logger.warning("[WARN]️ No response builder found - workflow may not provide comprehensive response")
            return queue

    def extract_final_response(self, logs: List[Dict[str, Any]]) -> Any:
        excluded_agent_types = {
            "MemoryReaderNode",
            "MemoryWriterNode",
            "memory",
            "memoryreadernode",
            "memorywriternode",
            "validate_and_structure",
            "guardian",
        }

        final_response_agent_types = {
            "OpenAIAnswerBuilder",
            "LocalLLMAgent",
        }

        final_response_log_entry = None
        for log_entry in reversed(logs):
            _event_type = log_entry.get("event_type")
            if _event_type == "MetaReport":
                continue
            payload = log_entry.get("payload", {})
            nested_result = payload.get("result")
            if isinstance(nested_result, dict) and "response" in nested_result:
                logger.info(f"[ORKA-FINAL] Returning response from final agent: {log_entry.get('agent_id')}")
                return nested_result["response"]
            if isinstance(nested_result, dict):
                deeper_result = nested_result.get("result")
                if isinstance(deeper_result, dict) and "response" in deeper_result:
                    logger.info(f"[ORKA-FINAL] Returning response from final agent: {log_entry.get('agent_id')}")
                    return deeper_result["response"]
            if _event_type in final_response_agent_types:
                payload = log_entry.get("payload", {})
                final_response_log_entry = log_entry
                if payload and ("result" in payload or "response" in payload):
                    final_response_log_entry = log_entry
                    break

        if not final_response_log_entry:
            # Only warn if workflow had LLM agents (not purely control-flow)
            has_llm_agents = any(
                not self.is_control_flow_agent(log.get("agent_id", ""))
                for log in logs
                if log.get("event_type") != "MetaReport"
            )
            if has_llm_agents:
                logger.warning("No suitable final agent found, returning full logs")
            else:
                logger.debug("Control-flow only workflow - returning logs without warning")
            return logs

        payload = final_response_log_entry.get("payload", {})
        response = payload.get("response", {})

        logger.info(f"[ORKA-FINAL] Returning response from final agent: {final_response_log_entry.get('agent_id')}")

        if isinstance(response, dict):
            if "response" in response:
                return response["response"]
            elif "result" in response:
                nested_result = response["result"]
                if isinstance(nested_result, dict):
                    if "response" in nested_result:
                        return nested_result["response"]
                    else:
                        return nested_result
                elif isinstance(nested_result, str):
                    return nested_result
                else:
                    return str(nested_result)
            else:
                return response
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def _select_best_candidate_from_shortlist(self, shortlist: List[Dict[str, Any]], question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not shortlist:
                return {}
            best_candidate = shortlist[0]
            logger.info(
                f"Selected GraphScout's top choice: {best_candidate.get('node_id')} "
                f"(score: {best_candidate.get('score', 0.0):.3f})"
            )
            return best_candidate
        except Exception as e:
            logger.error(f"Candidate selection failed: {e}")
            return shortlist[0] if shortlist else {}
