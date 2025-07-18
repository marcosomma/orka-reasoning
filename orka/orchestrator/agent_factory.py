# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Agent Factory
=============

Factory for creating and initializing agents and nodes based on configuration.
"""

import logging
from datetime import datetime

from ..agents import (
    agents,
    llm_agents,
    local_llm_agents,
    validation_and_structuring_agent,
)
from ..nodes import (
    failing_node,
    failover_node,
    fork_node,
    join_node,
    loop_node,
    router_node,
)
from ..nodes.memory_reader_node import MemoryReaderNode
from ..nodes.memory_writer_node import MemoryWriterNode
from ..tools.search_tools import DuckDuckGoTool

logger = logging.getLogger(__name__)

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
    "loop": loop_node.LoopNode,
    "memory": "special_handler",  # This will be handled specially in init_single_agent
}


class AgentFactory:
    """
    Factory class for creating and initializing agents based on configuration.
    """

    def _init_agents(self):
        """
        Instantiate all agents/nodes as defined in the YAML config.
        Returns a dict mapping agent IDs to their instances.
        """
        print(self.orchestrator_cfg)
        print(self.agent_cfgs)
        instances = {}

        def init_single_agent(cfg):
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
            if agent_type in ("router"):
                # RouterNode expects node_id and params
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(node_id=agent_id, **clean_cfg)

            if agent_type in ("fork", "join"):
                # Fork/Join nodes need memory_logger for group management
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    memory_logger=self.memory,
                    **clean_cfg,
                )

            if agent_type == "failover":
                # FailoverNode takes a list of child agent instances
                queue = cfg.get("queue", None)
                child_instances = [
                    init_single_agent(child_cfg) for child_cfg in cfg.get("children", [])
                ]
                return agent_cls(
                    node_id=agent_id,
                    children=child_instances,
                    queue=queue,
                )

            if agent_type == "failing":
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    **clean_cfg,
                )

            if agent_type == "loop":
                # LoopNode expects node_id and standard params
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    **clean_cfg,
                )

            # Special handling for memory agent type
            if agent_type == "memory" or agent_cls == "special_handler":
                # Special handling for memory nodes based on operation
                operation = cfg.get("config", {}).get("operation", "read")
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                namespace = cfg.get("namespace", "default")

                # Extract agent-level decay configuration and merge with global config
                agent_decay_config = cfg.get("decay", {})
                merged_decay_config = {}

                if hasattr(self, "memory") and hasattr(self.memory, "decay_config"):
                    # Start with global decay config as base
                    merged_decay_config = self.memory.decay_config.copy()

                    if agent_decay_config:
                        # Deep merge agent-specific decay config
                        for key, value in agent_decay_config.items():
                            if (
                                key in merged_decay_config
                                and isinstance(merged_decay_config[key], dict)
                                and isinstance(value, dict)
                            ):
                                # Deep merge nested dictionaries
                                merged_decay_config[key].update(value)
                            else:
                                # Direct override for non-dict values
                                merged_decay_config[key] = value
                else:
                    # No global config available, use agent config as-is (with defaults)
                    merged_decay_config = agent_decay_config

                # Clean the config to remove any already processed fields
                memory_cfg = clean_cfg.copy()
                memory_cfg.pop(
                    "decay",
                    None,
                )  # Remove decay from clean_cfg as it's handled separately

                if operation == "write":
                    # Use memory writer node for write operations
                    vector_enabled = memory_cfg.get("vector", False)
                    return MemoryWriterNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        vector=vector_enabled,
                        key_template=cfg.get("key_template"),
                        metadata=cfg.get("metadata", {}),
                        decay_config=merged_decay_config,
                        memory_logger=self.memory,
                    )
                else:  # default to read
                    # Use memory reader node for read operations
                    # Pass ALL config options to MemoryReaderNode
                    config_dict = memory_cfg.get("config", {})
                    return MemoryReaderNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        limit=config_dict.get("limit", 10),
                        similarity_threshold=config_dict.get("similarity_threshold", 0.6),
                        # Pass additional config options that were being ignored
                        enable_context_search=config_dict.get("enable_context_search", False),
                        enable_temporal_ranking=config_dict.get("enable_temporal_ranking", False),
                        temporal_weight=config_dict.get("temporal_weight", 0.1),
                        memory_category_filter=config_dict.get("memory_category_filter", None),
                        memory_type_filter=config_dict.get("memory_type_filter", None),
                        ef_runtime=config_dict.get("ef_runtime", 10),
                        decay_config=merged_decay_config,
                        memory_logger=self.memory,
                    )

            # Special handling for search tools
            if agent_type in ("duckduckgo"):
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    tool_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    **clean_cfg,
                )

            # Special handling for validation agent
            if agent_type == "validate_and_structure":
                # Create params dictionary with all configuration
                params = {
                    "agent_id": agent_id,
                    "prompt": cfg.get("prompt", ""),
                    "queue": cfg.get("queue", None),
                    "store_structure": cfg.get("store_structure"),
                    **clean_cfg,
                }
                return agent_cls(params=params)

            # Default agent instantiation
            prompt = cfg.get("prompt", None)
            queue = cfg.get("queue", None)
            return agent_cls(agent_id=agent_id, prompt=prompt, queue=queue, **clean_cfg)

        for cfg in self.agent_cfgs:
            agent = init_single_agent(cfg)
            instances[cfg["id"]] = agent

        return instances
