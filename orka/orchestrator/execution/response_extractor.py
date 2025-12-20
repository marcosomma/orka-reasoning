from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResponseExtractor:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

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
            logger.info(f"✅ Terminal validation passed: {last_agent_id} is a response builder")
            return queue
        response_builder = self._get_best_response_builder()
        if response_builder:
            validated_queue = queue + [response_builder]
            logger.info(f"🔧 Terminal enforcement: Added {response_builder} to ensure LLM response")
            logger.info(f"📋 Final validated queue: {validated_queue}")
            return validated_queue
        else:
            logger.warning("⚠️ No response builder found - workflow may not provide comprehensive response")
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
            logger.warning("No suitable final agent found, returning full logs")
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
