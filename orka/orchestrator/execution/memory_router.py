import logging
from typing import List

logger = logging.getLogger(__name__)


class MemoryRouter:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def apply_memory_routing_logic(self, shortlist: List[dict]) -> List[str]:
        try:
            memory_readers = []
            memory_writers = []
            regular_agents = []
            response_builder_found = False

            for candidate in shortlist:
                candidate_path = candidate.get("path")
                if not candidate_path:
                    agent_id = candidate.get("node_id")
                    candidate_path = [agent_id] if agent_id else []
                if not isinstance(candidate_path, list):
                    candidate_path = [candidate_path]
                for agent_id in candidate_path:
                    if not agent_id:
                        continue
                    if self.is_memory_agent(agent_id):
                        operation = self.get_memory_operation(agent_id)
                        if operation == "read":
                            memory_readers.append(agent_id)
                        elif operation == "write":
                            memory_writers.append(agent_id)
                        else:
                            regular_agents.append(agent_id)
                    elif self.orchestrator._is_response_builder(agent_id):
                        regular_agents.append(agent_id)
                        response_builder_found = True
                    else:
                        regular_agents.append(agent_id)

            agent_sequence = []
            agent_sequence.extend(memory_readers)
            non_response_regular = [a for a in regular_agents if not self.orchestrator._is_response_builder(a)]
            agent_sequence.extend(non_response_regular)
            agent_sequence.extend(memory_writers)

            if not response_builder_found:
                response_builder = self.orchestrator._get_best_response_builder()
                if response_builder and response_builder not in agent_sequence:
                    agent_sequence.append(response_builder)
            else:
                response_builders = [a for a in regular_agents if self.orchestrator._is_response_builder(a)]
                agent_sequence.extend(response_builders)

            logger.info(
                f"Memory routing applied: readers={memory_readers}, writers={memory_writers}, regular={len(non_response_regular)}"
            )
            return agent_sequence
        except Exception as e:
            logger.error(f"Failed to apply memory routing logic: {e}")
            return [str(candidate.get("node_id")) for candidate in shortlist if candidate.get("node_id") is not None]

    def is_memory_agent(self, agent_id: str) -> bool:
        try:
            agent = getattr(self.orchestrator, "agents", {}).get(agent_id)
            if agent:
                agent_class_name = agent.__class__.__name__
                return agent_class_name in ["MemoryReaderNode", "MemoryWriterNode"]
            return False
        except Exception as e:
            logger.error(f"Failed to check if {agent_id} is memory agent: {e}")
            return False

    def get_memory_operation(self, agent_id: str) -> str:
        try:
            agent = getattr(self.orchestrator, "agents", {}).get(agent_id)
            if agent:
                agent_class_name = agent.__class__.__name__
                if agent_class_name == "MemoryReaderNode":
                    return "read"
                elif agent_class_name == "MemoryWriterNode":
                    return "write"
            return "unknown"
        except Exception as e:
            logger.error(f"Failed to get memory operation for {agent_id}: {e}")
            return "unknown"
