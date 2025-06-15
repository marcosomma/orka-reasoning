# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import logging
from datetime import datetime

from ..agents import (
    agents,
    llm_agents,
    local_llm_agents,
    validation_and_structuring_agent,
)
from ..nodes import failing_node, failover_node, fork_node, join_node, router_node
from ..nodes.memory_reader_node import MemoryReaderNode
from ..nodes.memory_writer_node import MemoryWriterNode
from ..tools.search_tools import DuckDuckGoTool

logger = logging.getLogger(__name__)

# Agent type registry
AGENT_TYPES = {
    "binary": agents.BinaryAgent,
    "classification": agents.ClassificationAgent,
    "local_llm": local_llm_agents.LocalLLMAgent,
    "openai-answer": llm_agents.OpenAIAnswerBuilder,
    "openai-binary": llm_agents.OpenAIBinaryAgent,
    "openai-classification": llm_agents.OpenAIClassificationAgent,
    "validate_and_structure": validation_and_structuring_agent.ValidationAndStructuringAgent,
    "duckduckgo": DuckDuckGoTool,
    "router": router_node.RouterNode,
    "failover": failover_node.FailoverNode,
    "failing": failing_node.FailingNode,
    "join": join_node.JoinNode,
    "fork": fork_node.ForkNode,
    "memory": "special_handler",  # This will be handled specially in init_single_agent
}


class AgentManager:
    """
    Manages agent initialization, configuration, and validation.
    Handles the creation of all agent types and their dependencies.
    """

    def __init__(self, memory_logger=None):
        """
        Initialize the agent manager.

        Args:
            memory_logger: Memory logger instance for agents that need it
        """
        self.memory_logger = memory_logger
        self.agents = {}

    def init_agents(self, agent_configs):
        """
        Instantiate all agents/nodes as defined in the agent configs.

        Args:
            agent_configs: List of agent configuration dictionaries

        Returns:
            dict: Mapping of agent IDs to their instances
        """
        instances = {}

        for cfg in agent_configs:
            agent = self._init_single_agent(cfg)
            instances[cfg["id"]] = agent

        self.agents = instances
        return instances

    def _init_single_agent(self, cfg):
        """
        Initialize a single agent based on its configuration.

        Args:
            cfg: Agent configuration dictionary

        Returns:
            Agent instance
        """
        agent_cls = AGENT_TYPES.get(cfg["type"])
        if not agent_cls:
            raise ValueError(f"Unsupported agent type: {cfg['type']}")

        agent_type = cfg["type"].strip().lower()
        agent_id = cfg["id"]

        # Remove fields not needed for instantiation
        clean_cfg = cfg.copy()
        clean_cfg.pop("id", None)
        clean_cfg.pop("type", None)
        clean_cfg.pop("prompt", None)
        clean_cfg.pop("queue", None)

        print(
            f"{datetime.now()} > [ORKA][INIT] Instantiating agent {agent_id} of type {agent_type}",
        )

        # Special handling for node types with unique constructor signatures
        if agent_type == "router":
            return self._init_router_node(agent_id, cfg, clean_cfg)
        elif agent_type in ("fork", "join"):
            return self._init_fork_join_node(agent_type, agent_id, cfg, clean_cfg)
        elif agent_type == "failover":
            return self._init_failover_node(agent_id, cfg, clean_cfg)
        elif agent_type == "failing":
            return self._init_failing_node(agent_id, cfg, clean_cfg)
        elif agent_type == "memory" or agent_cls == "special_handler":
            return self._init_memory_node(agent_id, cfg, clean_cfg)
        elif agent_type == "duckduckgo":
            return self._init_search_tool(agent_id, cfg, clean_cfg)
        elif agent_type == "validate_and_structure":
            return self._init_validation_agent(agent_id, cfg, clean_cfg)
        else:
            return self._init_default_agent(agent_cls, agent_id, cfg, clean_cfg)

    def _init_router_node(self, agent_id, cfg, clean_cfg):
        """Initialize a router node."""
        return router_node.RouterNode(node_id=agent_id, **clean_cfg)

    def _init_fork_join_node(self, agent_type, agent_id, cfg, clean_cfg):
        """Initialize fork or join nodes."""
        prompt = cfg.get("prompt", None)
        queue = cfg.get("queue", None)

        if agent_type == "fork":
            return fork_node.ForkNode(
                node_id=agent_id,
                prompt=prompt,
                queue=queue,
                memory_logger=self.memory_logger,
                **clean_cfg,
            )
        else:  # join
            return join_node.JoinNode(
                node_id=agent_id,
                prompt=prompt,
                queue=queue,
                memory_logger=self.memory_logger,
                **clean_cfg,
            )

    def _init_failover_node(self, agent_id, cfg, clean_cfg):
        """Initialize a failover node with child agents."""
        queue = cfg.get("queue", None)
        child_instances = [
            self._init_single_agent(child_cfg) for child_cfg in cfg.get("children", [])
        ]
        return failover_node.FailoverNode(
            node_id=agent_id,
            children=child_instances,
            queue=queue,
        )

    def _init_failing_node(self, agent_id, cfg, clean_cfg):
        """Initialize a failing node."""
        prompt = cfg.get("prompt", None)
        queue = cfg.get("queue", None)
        return failing_node.FailingNode(
            node_id=agent_id,
            prompt=prompt,
            queue=queue,
            **clean_cfg,
        )

    def _init_memory_node(self, agent_id, cfg, clean_cfg):
        """Initialize memory reader or writer nodes."""
        operation = cfg.get("config", {}).get("operation", "read")
        prompt = cfg.get("prompt", None)
        queue = cfg.get("queue", None)
        namespace = cfg.get("namespace", "default")

        if operation == "write":
            vector_enabled = clean_cfg.get("vector", False)
            return MemoryWriterNode(
                node_id=agent_id,
                prompt=prompt,
                queue=queue,
                namespace=namespace,
                vector=vector_enabled,
                key_template=cfg.get("key_template"),
                metadata=cfg.get("metadata", {}),
            )
        else:  # default to read
            return MemoryReaderNode(
                node_id=agent_id,
                prompt=prompt,
                queue=queue,
                namespace=namespace,
                limit=clean_cfg.get("limit", 10),
                similarity_threshold=clean_cfg.get("similarity_threshold", 0.6),
            )

    def _init_search_tool(self, agent_id, cfg, clean_cfg):
        """Initialize search tools like DuckDuckGo."""
        prompt = cfg.get("prompt", None)
        queue = cfg.get("queue", None)
        return DuckDuckGoTool(
            tool_id=agent_id,
            prompt=prompt,
            queue=queue,
            **clean_cfg,
        )

    def _init_validation_agent(self, agent_id, cfg, clean_cfg):
        """Initialize validation and structuring agent."""
        params = {
            "agent_id": agent_id,
            "prompt": cfg.get("prompt", ""),
            "queue": cfg.get("queue", None),
            "store_structure": cfg.get("store_structure"),
            **clean_cfg,
        }
        return validation_and_structuring_agent.ValidationAndStructuringAgent(params=params)

    def _init_default_agent(self, agent_cls, agent_id, cfg, clean_cfg):
        """Initialize default agents (binary, classification, LLM agents, etc.)."""
        prompt = cfg.get("prompt", None)
        queue = cfg.get("queue", None)
        return agent_cls(agent_id=agent_id, prompt=prompt, queue=queue, **clean_cfg)

    def get_agent(self, agent_id):
        """
        Get an agent by ID.

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def get_all_agents(self):
        """
        Get all initialized agents.

        Returns:
            dict: All agent instances
        """
        return self.agents.copy()

    def validate_agent_config(self, cfg):
        """
        Validate an agent configuration.

        Args:
            cfg: Agent configuration dictionary

        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ["id", "type"]

        for field in required_fields:
            if field not in cfg:
                logger.error(f"Agent config missing required field: {field}")
                return False

        if cfg["type"] not in AGENT_TYPES:
            logger.error(f"Unsupported agent type: {cfg['type']}")
            return False

        return True

    def get_supported_agent_types(self):
        """
        Get list of supported agent types.

        Returns:
            list: List of supported agent type names
        """
        return list(AGENT_TYPES.keys())
