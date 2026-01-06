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

"""
Agent Factory
=============

Factory for creating and initializing agents and nodes based on configuration.
"""

import logging
from typing import Any, Dict, List, Type, Union, cast

from ..agents import (
    agents,
    invariant_validator_agent,
    llm_agents,
    local_llm_agents,
    plan_validator,
    validation_and_structuring_agent,
)
from ..memory.base_logger import BaseMemoryLogger
from ..memory.redisstack_logger import RedisStackMemoryLogger
from ..nodes import (  # path_executor_node - lazy loaded to avoid circular imports (Bug #1)
    failing_node,
    failover_node,
    fork_node,
    join_node,
    loop_node,
    loop_validator_node,
    router_node,
)
from ..nodes.graph_scout_agent import GraphScoutAgent
from ..nodes.memory_reader_node import MemoryReaderNode
from ..nodes.memory_writer_node import MemoryWriterNode
from ..nodes.rag_node import RAGNode
from ..tools.search_tools import DuckDuckGoTool

logger = logging.getLogger(__name__)

# Define a type for agent classes
# Note: PathExecutorNode type removed - it's lazy loaded to avoid circular imports
AgentClass = Union[
    Type[agents.BinaryAgent],
    Type[agents.ClassificationAgent],
    Type[invariant_validator_agent.InvariantValidatorAgent],
    Type[local_llm_agents.LocalLLMAgent],
    Type[llm_agents.OpenAIAnswerBuilder],
    Type[llm_agents.OpenAIBinaryAgent],
    Type[llm_agents.OpenAIClassificationAgent],
    Type[plan_validator.PlanValidatorAgent],
    Type[validation_and_structuring_agent.ValidationAndStructuringAgent],
    Type[RAGNode],
    Type[DuckDuckGoTool],
    Type[router_node.RouterNode],
    Type[failover_node.FailoverNode],
    Type[failing_node.FailingNode],
    Type[join_node.JoinNode],
    Type[fork_node.ForkNode],
    Type[loop_node.LoopNode],
    Type[loop_validator_node.LoopValidatorNode],
    # Type[path_executor_node.PathExecutorNode], - lazy loaded (Bug #1 fix)
    Type[GraphScoutAgent],
    Type[MemoryReaderNode],
    Type[MemoryWriterNode],
    str,  # For "special_handler" and "path_executor"
]

AGENT_TYPES: Dict[str, AgentClass] = {
    "binary": agents.BinaryAgent,
    "classification": agents.ClassificationAgent,
    "invariant_validator": invariant_validator_agent.InvariantValidatorAgent,
    "local_llm": local_llm_agents.LocalLLMAgent,
    "openai-answer": llm_agents.OpenAIAnswerBuilder,
    "openai-binary": llm_agents.OpenAIBinaryAgent,
    "openai-classification": llm_agents.OpenAIClassificationAgent,
    "plan_validator": plan_validator.PlanValidatorAgent,
    "validate_and_structure": validation_and_structuring_agent.ValidationAndStructuringAgent,
    "rag": RAGNode,
    "duckduckgo": DuckDuckGoTool,
    "router": router_node.RouterNode,
    "failover": failover_node.FailoverNode,
    "failing": failing_node.FailingNode,
    "join": join_node.JoinNode,
    "fork": fork_node.ForkNode,
    "loop": loop_node.LoopNode,
    "loop_validator": loop_validator_node.LoopValidatorNode,
    "path_executor": "special_handler",  # [DEBUG] Bug #1: Lazy loaded to avoid circular imports
    "graph-scout": GraphScoutAgent,
    "memory": "special_handler",  # This will be handled specially in init_single_agent
}


class AgentFactory:
    """
    Factory class for creating and initializing agents based on configuration.
    """

    def __init__(
        self,
        orchestrator_cfg: Dict[str, Any],
        agent_cfgs: List[Dict[str, Any]],
        memory: BaseMemoryLogger,
    ) -> None:
        self.orchestrator_cfg = orchestrator_cfg
        self.agent_cfgs = agent_cfgs
        self.memory = memory

    def _init_agents(self) -> Dict[str, Any]:
        """
        Instantiate all agents/nodes as defined in the YAML config.
        Returns a dict mapping agent IDs to their instances.
        """
        logger.debug(self.orchestrator_cfg)
        logger.debug(self.agent_cfgs)
        instances = {}

        def init_single_agent(cfg: Dict[str, Any]) -> Any:
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

            # Backward/forward compatibility: allow agents to be configured either
            # with top-level fields or nested under a `params:` dict.
            # This is especially important for `local_llm`, where provider/model_url
            # are read from self.params (kwargs passed at construction time).
            if agent_type == "local_llm":
                nested_params = clean_cfg.pop("params", None)
                if isinstance(nested_params, dict):
                    # Support older examples that used `url:` instead of `model_url:`
                    if "model_url" not in nested_params and "url" in nested_params:
                        nested_params["model_url"] = nested_params.get("url")
                    for key, value in nested_params.items():
                        clean_cfg.setdefault(key, value)

            # PlanValidatorAgent uses a different naming convention (llm_*).
            # Accept workflow configs that specify OpenAI-style keys.
            if agent_type == "plan_validator":
                nested_params = clean_cfg.pop("params", None)
                if isinstance(nested_params, dict):
                    for key, value in nested_params.items():
                        clean_cfg.setdefault(key, value)

                # Map common keys -> expected constructor args
                if "llm_model" not in clean_cfg and "model" in clean_cfg:
                    clean_cfg["llm_model"] = clean_cfg.pop("model")
                if "llm_provider" not in clean_cfg and "provider" in clean_cfg:
                    clean_cfg["llm_provider"] = clean_cfg.pop("provider")
                if "llm_url" not in clean_cfg:
                    if "model_url" in clean_cfg:
                        clean_cfg["llm_url"] = clean_cfg.pop("model_url")
                    elif "url" in clean_cfg:
                        clean_cfg["llm_url"] = clean_cfg.pop("url")

                # Require explicit LLM config (no vendor defaults)
                missing_fields: list[str] = []
                if not clean_cfg.get("llm_model"):
                    missing_fields.append("llm_model (or model)")
                if not clean_cfg.get("llm_provider"):
                    missing_fields.append("llm_provider (or provider)")
                if not clean_cfg.get("llm_url"):
                    missing_fields.append("llm_url (or model_url/url)")
                if missing_fields:
                    raise ValueError(
                        f"plan_validator agent '{agent_id}' requires explicit LLM configuration; missing: {', '.join(missing_fields)}"
                    )

                # Normalize provider aliases
                provider_val_raw = str(clean_cfg.get("llm_provider", "")).strip().lower()
                if provider_val_raw in {"lm_studio", "lmstudio", "openai", "openai_compatible"}:
                    provider_val = "openai_compatible"
                else:
                    provider_val = provider_val_raw
                clean_cfg["llm_provider"] = provider_val

                # For OpenAI-compatible endpoints, ensure we hit chat completions.
                if provider_val != "ollama":
                    llm_url_val = str(clean_cfg.get("llm_url", ""))
                    if llm_url_val and not llm_url_val.endswith("/chat/completions"):
                        if llm_url_val.endswith("/"):
                            llm_url_val = llm_url_val + "v1/chat/completions"
                        else:
                            llm_url_val = llm_url_val + "/v1/chat/completions"
                        clean_cfg["llm_url"] = llm_url_val

            logger.info(
                f"Instantiating agent {agent_id} of type {agent_type}",
            )

            # Special handling for node types with unique constructor signatures
            if agent_type in ("router"):
                # RouterNode expects node_id and params
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return router_node.RouterNode(node_id=agent_id, **clean_cfg)

            if agent_type in ("fork", "join"):
                # Fork/Join nodes need memory_logger for group management
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                node_cls = agent_cls
                if agent_type == "fork":
                    node_cls = fork_node.ForkNode
                else:
                    node_cls = join_node.JoinNode

                return node_cls(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    memory_logger=cast(RedisStackMemoryLogger, self.memory),
                    **clean_cfg,
                )

            if agent_type == "failover":
                # FailoverNode takes a list of child agent instances
                queue = cfg.get("queue", None)
                child_instances = [
                    init_single_agent(child_cfg) for child_cfg in cfg.get("children", [])
                ]
                return failover_node.FailoverNode(
                    node_id=agent_id,
                    children=child_instances,
                    queue=queue,
                )

            if agent_type == "failing":
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return failing_node.FailingNode(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    **clean_cfg,
                )

            if agent_type == "loop":
                # LoopNode expects node_id and standard params
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)

                return loop_node.LoopNode(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    memory_logger=cast(RedisStackMemoryLogger, self.memory),
                    **clean_cfg,
                )

            if agent_type == "loop_validator":
                # LoopValidatorNode expects node_id and LLM configuration
                return loop_validator_node.LoopValidatorNode(
                    node_id=agent_id,
                    **clean_cfg,
                )

            if agent_type == "path_executor":
                # [DEBUG] Bug #1 Fix: Lazy load PathExecutorNode to avoid circular imports
                from ..nodes import path_executor_node

                # PathExecutorNode doesn't need prompt or queue
                clean_cfg.pop("prompt", None)
                clean_cfg.pop("queue", None)
                return path_executor_node.PathExecutorNode(node_id=agent_id, **clean_cfg)

            # Special handling for memory agent type
            if agent_type == "memory" or agent_cls == "special_handler":
                # Special handling for memory nodes based on operation
                config_dict = cfg.get("config", {}) or {}
                operation = config_dict.get("operation", "read")
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                # Support both legacy top-level `namespace:` and newer `config.namespace:`
                namespace = cfg.get("namespace") or config_dict.get("namespace") or "default"
                memory_preset = cfg.get("memory_preset")

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
                    # Support both legacy top-level `vector:` and `config.vector:`
                    vector_enabled = bool(
                        memory_cfg.get("vector", config_dict.get("vector", False))
                    )
                    # If a memory preset is specified, default to vector writes unless explicitly disabled.
                    if memory_preset and "vector" not in memory_cfg and "vector" not in config_dict:
                        vector_enabled = True
                    return MemoryWriterNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        vector=vector_enabled,
                        memory_preset=memory_preset,
                        key_template=cfg.get("key_template"),
                        metadata=cfg.get("metadata", {}),
                        decay_config=merged_decay_config,
                        memory_logger=self.memory,
                    )
                else:  # default to read
                    # Use memory reader node for read operations
                    # Pass ALL config options to MemoryReaderNode
                    config_dict = memory_cfg.get("config", {}) or {}
                    return MemoryReaderNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        memory_preset=memory_preset,
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

            # Special handling for GraphScout agent
            if agent_type == "graph-scout":
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return GraphScoutAgent(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    **clean_cfg,
                )

            # Special handling for search tools
            if agent_type in ("duckduckgo"):
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return DuckDuckGoTool(
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
                # Create a new dictionary with params as the only key
                agent = validation_and_structuring_agent.ValidationAndStructuringAgent(params)
                return agent

            # Special handling for RAG node
            if agent_type == "rag":
                # RAGNode requires registry, prompt, and queue as strings
                from ..contracts import Registry

                registry = Registry(
                    {"memory": self.memory, "tools": {}, "embedder": None, "llm": None}
                )
                prompt = cfg.get("prompt", "")
                queue = cfg.get("queue") or ""
                return RAGNode(
                    node_id=agent_id, registry=registry, prompt=prompt, queue=queue, **clean_cfg
                )

            # Default agent instantiation
            if isinstance(agent_cls, str):
                raise ValueError(f"Invalid agent type: {agent_type}")

            prompt = cfg.get("prompt") or ""
            queue_param = cfg.get("queue")
            # Handle queue parameter based on agent type
            if "queue" in clean_cfg:
                del clean_cfg["queue"]  # Remove to avoid conflicts

            # Handle different queue parameter types based on agent class
            if hasattr(agent_cls, "__name__"):
                class_name = str(agent_cls.__name__)
                if class_name == "RAGNode":
                    # RAGNode expects str
                    queue_str = str(queue_param or "default")
                    return cast(Any, agent_cls)(
                        agent_id=agent_id, prompt=prompt, queue=queue_str, **clean_cfg
                    )
                elif class_name in ["ForkNode", "LoopNode", "JoinNode"]:
                    # These nodes expect list[Any] | None
                    if isinstance(queue_param, list):
                        queue_list = queue_param
                    elif queue_param:
                        queue_list = [queue_param]
                    else:
                        queue_list = None
                    return agent_cls(agent_id=agent_id, prompt=prompt, queue=queue_list, **clean_cfg)  # type: ignore [call-arg , arg-type]
                else:
                    # Most agents expect list[str] | None
                    if isinstance(queue_param, list):
                        # Ensure all items are strings
                        queue_str_list = [str(item) for item in queue_param]
                    elif queue_param:
                        queue_str_list = [str(queue_param)]
                    else:
                        queue_str_list = None
                    return cast(Any, agent_cls)(
                        agent_id=agent_id, prompt=prompt, queue=queue_str_list, **clean_cfg
                    )
            else:
                # Fallback for unknown types
                return agent_cls(agent_id=agent_id, prompt=prompt, **clean_cfg)  # type: ignore [call-arg]

        for cfg in self.agent_cfgs:
            agent = init_single_agent(cfg)
            instances[cfg["id"]] = agent

        return instances
