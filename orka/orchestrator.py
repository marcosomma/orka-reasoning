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
# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import asyncio
import inspect
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from time import time
from uuid import uuid4

from jinja2 import Template

from .agents import (
    agents,
    llm_agents,
    local_llm_agents,
    validation_and_structuring_agent,
)
from .fork_group_manager import ForkGroupManager, SimpleForkGroupManager
from .loader import YAMLLoader
from .memory_logger import create_memory_logger
from .nodes import failing_node, failover_node, fork_node, join_node, router_node
from .nodes.memory_reader_node import MemoryReaderNode
from .nodes.memory_writer_node import MemoryWriterNode
from .tools.search_tools import DuckDuckGoTool

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
    "memory": "special_handler",  # This will be handled specially in init_single_agent
}


class Orchestrator:
    """
    The Orchestrator is the core engine that loads a YAML configuration,
    instantiates agents and nodes, and manages the execution of the reasoning workflow.
    It supports parallelism, dynamic routing, and full trace logging.
    """

    def __init__(self, config_path):
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
        """
        self.loader = YAMLLoader(config_path)
        self.loader.validate()

        self.orchestrator_cfg = self.loader.get_orchestrator()
        self.agent_cfgs = self.loader.get_agents()

        # Configure memory backend
        memory_backend = os.getenv("ORKA_MEMORY_BACKEND", "redis").lower()

        # Get debug flag from orchestrator config or environment
        debug_keep_previous_outputs = self.orchestrator_cfg.get("debug", {}).get(
            "keep_previous_outputs",
            False,
        )
        debug_keep_previous_outputs = (
            debug_keep_previous_outputs
            or os.getenv("ORKA_DEBUG_KEEP_PREVIOUS_OUTPUTS", "false").lower() == "true"
        )

        if memory_backend == "kafka":
            self.memory = create_memory_logger(
                backend="kafka",
                bootstrap_servers=os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS",
                    "localhost:9092",
                ),
                topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "orka-memory"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
            )
            # For Kafka, we'll use a simple in-memory fork manager since Kafka doesn't have Redis-like operations
            self.fork_manager = SimpleForkGroupManager()
        else:
            self.memory = create_memory_logger(
                backend="redis",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
            )
            # For Redis, use the existing Redis-based fork manager
            self.fork_manager = ForkGroupManager(self.memory.redis)

        self.queue = self.orchestrator_cfg["agents"][:]  # Initial agent execution queue
        self.agents = self._init_agents()  # Dict of agent_id -> agent instance
        self.run_id = str(uuid4())  # Unique run/session ID
        self.step_index = 0  # Step counter for traceability

        # Error tracking and telemetry
        self.error_telemetry = {
            "errors": [],  # List of all errors encountered
            "retry_counters": {},  # Per-agent retry counts
            "partial_successes": [],  # Agents that succeeded after retries
            "silent_degradations": [],  # JSON parsing failures that fell back to raw text
            "status_codes": {},  # HTTP status codes for API calls
            "execution_status": "running",  # overall status: running, completed, failed, partial
            "critical_failures": [],  # Failures that stopped execution
            "recovery_actions": [],  # Actions taken to recover from errors
        }

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

            # Special handling for memory agent type
            if agent_type == "memory" or agent_cls == "special_handler":
                # Special handling for memory nodes based on operation
                operation = cfg.get("config", {}).get("operation", "read")
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                namespace = cfg.get("namespace", "default")

                # Clean the config to remove any already processed fields
                memory_cfg = clean_cfg.copy()

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
                    )
                else:  # default to read
                    # Use memory reader node for read operations
                    return MemoryReaderNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        limit=memory_cfg.get("limit", 10),
                        similarity_threshold=memory_cfg.get(
                            "similarity_threshold",
                            0.6,
                        ),
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

    def render_prompt(self, template_str, payload):
        """
        Render a Jinja2 template string with the given payload.
        Used for dynamic prompt construction.
        """
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead.",
            )
        return Template(template_str).render(**payload)

    def _add_prompt_to_payload(self, agent, payload_out, payload):
        """
        Add prompt and formatted_prompt to payload_out if agent has a prompt.

        Args:
            agent: The agent instance
            payload_out: The payload dictionary to modify
            payload: The context payload for template rendering
        """
        if hasattr(agent, "prompt") and agent.prompt:
            payload_out["prompt"] = agent.prompt
            # If the agent has a prompt, render it with the current payload context
            try:
                formatted_prompt = self.render_prompt(agent.prompt, payload)
                payload_out["formatted_prompt"] = formatted_prompt
            except Exception:
                # If rendering fails, keep the original prompt
                payload_out["formatted_prompt"] = agent.prompt

    def _render_agent_prompt(self, agent, payload):
        """
        Render agent's prompt and add formatted_prompt to payload for agent execution.

        Args:
            agent: The agent instance
            payload: The payload dictionary to modify
        """
        if hasattr(agent, "prompt") and agent.prompt:
            try:
                formatted_prompt = self.render_prompt(agent.prompt, payload)
                payload["formatted_prompt"] = formatted_prompt
            except Exception:
                # If rendering fails, use the original prompt
                payload["formatted_prompt"] = agent.prompt

    @staticmethod
    def normalize_bool(value):
        """
        Normalize a value to boolean.
        Accepts bools or strings like 'true', 'yes', etc.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes"]
        return False

    def _record_error(
        self,
        error_type,
        agent_id,
        error_msg,
        exception=None,
        step=None,
        status_code=None,
        recovery_action=None,
    ):
        """
        Record an error in the error telemetry system.

        Args:
            error_type: Type of error (agent_failure, json_parsing, api_error, etc.)
            agent_id: ID of the agent that failed
            error_msg: Human readable error message
            exception: The actual exception object (optional)
            step: Step number where error occurred
            status_code: HTTP status code if applicable
            recovery_action: Action taken to recover (retry, fallback, etc.)
        """
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "agent_id": agent_id,
            "message": error_msg,
            "step": step or self.step_index,
            "run_id": self.run_id,
        }

        if exception:
            error_entry["exception"] = {
                "type": str(type(exception).__name__),
                "message": str(exception),
                "traceback": str(exception.__traceback__)
                if hasattr(exception, "__traceback__")
                else None,
            }

        if status_code:
            error_entry["status_code"] = status_code
            self.error_telemetry["status_codes"][agent_id] = status_code

        if recovery_action:
            error_entry["recovery_action"] = recovery_action
            self.error_telemetry["recovery_actions"].append(
                {
                    "timestamp": error_entry["timestamp"],
                    "agent_id": agent_id,
                    "action": recovery_action,
                },
            )

        self.error_telemetry["errors"].append(error_entry)

        # Log error to console
        print(f"🚨 [ORKA-ERROR] {error_type} in {agent_id}: {error_msg}")

    def _record_retry(self, agent_id):
        """Record a retry attempt for an agent."""
        if agent_id not in self.error_telemetry["retry_counters"]:
            self.error_telemetry["retry_counters"][agent_id] = 0
        self.error_telemetry["retry_counters"][agent_id] += 1

    def _record_partial_success(self, agent_id, retry_count):
        """Record that an agent succeeded after retries."""
        self.error_telemetry["partial_successes"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "retry_count": retry_count,
            },
        )

    def _record_silent_degradation(self, agent_id, degradation_type, details):
        """Record silent degradations like JSON parsing failures."""
        self.error_telemetry["silent_degradations"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "type": degradation_type,
                "details": details,
            },
        )

    def _save_error_report(self, logs, final_error=None):
        """
        Save comprehensive error report with all logged data up to the failure point.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Determine final execution status
        if final_error:
            self.error_telemetry["execution_status"] = "failed"
            self.error_telemetry["critical_failures"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": str(final_error),
                    "step": self.step_index,
                },
            )
        elif self.error_telemetry["errors"]:
            self.error_telemetry["execution_status"] = "partial"
        else:
            self.error_telemetry["execution_status"] = "completed"

        # Generate meta report even on failure
        try:
            meta_report = self._generate_meta_report(logs)
        except Exception as e:
            self._record_error(
                "meta_report_generation",
                "meta_report",
                f"Failed to generate meta report: {e}",
                e,
            )
            meta_report = {
                "error": "Failed to generate meta report",
                "partial_data": {
                    "total_agents_executed": len(logs),
                    "run_id": self.run_id,
                },
            }

        # Create comprehensive error report
        error_report = {
            "orka_execution_report": {
                "run_id": self.run_id,
                "timestamp": timestamp,
                "execution_status": self.error_telemetry["execution_status"],
                "error_telemetry": self.error_telemetry,
                "meta_report": meta_report,
                "execution_logs": logs,
                "total_steps_attempted": self.step_index,
                "total_errors": len(self.error_telemetry["errors"]),
                "total_retries": sum(self.error_telemetry["retry_counters"].values()),
                "agents_with_errors": list(
                    set(error["agent_id"] for error in self.error_telemetry["errors"]),
                ),
                "memory_snapshot": self._capture_memory_snapshot(),
            },
        }

        # Save error report
        error_report_path = os.path.join(log_dir, f"orka_error_report_{timestamp}.json")
        try:
            with open(error_report_path, "w") as f:
                json.dump(error_report, f, indent=2, default=str)
            print(f"📋 Error report saved: {error_report_path}")
        except Exception as e:
            print(f"❌ Failed to save error report: {e}")

        # Also save to memory backend
        try:
            trace_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
            self.memory.save_to_file(trace_path)
            print(f"📋 Execution trace saved: {trace_path}")
        except Exception as e:
            print(f"⚠️ Failed to save trace to memory backend: {e}")

        return error_report_path

    def _capture_memory_snapshot(self):
        """Capture current state of memory backend for debugging."""
        try:
            if hasattr(self.memory, "memory") and self.memory.memory:
                return {
                    "total_entries": len(self.memory.memory),
                    "last_10_entries": self.memory.memory[-10:]
                    if len(self.memory.memory) >= 10
                    else self.memory.memory,
                    "backend_type": type(self.memory).__name__,
                }
        except Exception as e:
            return {"error": f"Failed to capture memory snapshot: {e}"}
        return {"status": "no_memory_data"}

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Add agent IDs to the execution queue (used for forked/parallel execution).
        """
        self.queue.extend(agent_ids)  # Add to queue keeping order

    def _extract_llm_metrics(self, agent, result):
        """
        Extract LLM metrics from agent result or agent state.

        Args:
            agent: The agent instance
            result: The agent's result

        Returns:
            dict or None: LLM metrics if found
        """
        # Check if result is a dict with _metrics
        if isinstance(result, dict) and "_metrics" in result:
            return result["_metrics"]

        # Check if agent has stored metrics (for binary/classification agents)
        if hasattr(agent, "_last_metrics") and agent._last_metrics:
            return agent._last_metrics

        return None

    def _get_runtime_environment(self):
        """
        Get runtime environment information for debugging and reproducibility.
        """
        import os
        import platform
        import subprocess

        env_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Get Git SHA if available
        try:
            git_sha = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    stderr=subprocess.DEVNULL,
                    cwd=os.getcwd(),
                    timeout=5,
                )
                .decode()
                .strip()
            )
            env_info["git_sha"] = git_sha[:12]  # Short SHA
        except:
            env_info["git_sha"] = "unknown"

        # Check for Docker environment
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            env_info["docker_image"] = os.environ.get("DOCKER_IMAGE", "unknown")
        else:
            env_info["docker_image"] = None

        # GPU information
        try:
            import GPUtil

            gpus = GPUtil.getGPUs()
            if gpus:
                env_info["gpu_type"] = (
                    f"{gpus[0].name} ({len(gpus)} GPU{'s' if len(gpus) > 1 else ''})"
                )
            else:
                env_info["gpu_type"] = "none"
        except:
            env_info["gpu_type"] = "unknown"

        # Pricing version (current month-year)
        env_info["pricing_version"] = "2025-01"

        return env_info

    def _generate_meta_report(self, logs):
        """
        Generate a meta report with aggregated metrics from execution logs.

        Args:
            logs: List of execution log entries

        Returns:
            dict: Meta report with aggregated metrics
        """
        total_duration = 0
        total_tokens = 0
        total_cost_usd = 0
        total_llm_calls = 0
        latencies = []

        agent_metrics = {}
        model_usage = {}

        # Track seen metrics to avoid double-counting due to deduplication
        seen_metrics = set()

        def extract_metrics_recursively(data, source_agent_id="unknown"):
            """Recursively extract _metrics from nested data structures, avoiding duplicates."""
            found_metrics = []

            if isinstance(data, dict):
                # Check if this dict has _metrics
                if "_metrics" in data:
                    metrics = data["_metrics"]
                    # Create a unique identifier for this metrics object
                    metrics_id = (
                        metrics.get("model", ""),
                        metrics.get("tokens", 0),
                        metrics.get("prompt_tokens", 0),
                        metrics.get("completion_tokens", 0),
                        metrics.get("latency_ms", 0),
                        metrics.get("cost_usd", 0),
                    )

                    # Only add if we haven't seen this exact metrics before
                    if metrics_id not in seen_metrics:
                        seen_metrics.add(metrics_id)
                        found_metrics.append((metrics, source_agent_id))

                # Recursively check all values
                for key, value in data.items():
                    if key != "_metrics":  # Avoid infinite recursion
                        sub_metrics = extract_metrics_recursively(value, source_agent_id)
                        found_metrics.extend(sub_metrics)

            elif isinstance(data, list):
                for item in data:
                    sub_metrics = extract_metrics_recursively(item, source_agent_id)
                    found_metrics.extend(sub_metrics)

            return found_metrics

        for log_entry in logs:
            # Aggregate execution duration
            duration = log_entry.get("duration", 0)
            total_duration += duration

            agent_id = log_entry.get("agent_id", "unknown")

            # Extract all LLM metrics from the log entry recursively
            all_metrics = []

            # First check for llm_metrics at root level (legacy format)
            if log_entry.get("llm_metrics"):
                all_metrics.append((log_entry["llm_metrics"], agent_id))

            # Then recursively search for _metrics in payload
            if log_entry.get("payload"):
                payload_metrics = extract_metrics_recursively(log_entry["payload"], agent_id)
                all_metrics.extend(payload_metrics)

            # Process all found metrics
            for llm_metrics, source_agent in all_metrics:
                if not llm_metrics:
                    continue

                total_llm_calls += 1
                total_tokens += llm_metrics.get("tokens", 0)

                # Handle null costs (real local LLM cost calculation may return None)
                cost = llm_metrics.get("cost_usd")
                if cost is not None:
                    total_cost_usd += cost
                else:
                    # Check if we should fail on null costs
                    import os

                    if os.environ.get("ORKA_LOCAL_COST_POLICY") == "null_fail":
                        raise ValueError(
                            f"Pipeline failed due to null cost in agent '{source_agent}' "
                            f"(model: {llm_metrics.get('model', 'unknown')}). "
                            f"Configure real cost calculation or use cloud models.",
                        )
                    logger.warning(
                        f"Agent '{source_agent}' returned null cost - excluding from total",
                    )

                latency = llm_metrics.get("latency_ms", 0)
                if latency > 0:
                    latencies.append(latency)

                # Track per-agent metrics (use the source agent, which could be nested)
                if source_agent not in agent_metrics:
                    agent_metrics[source_agent] = {
                        "calls": 0,
                        "tokens": 0,
                        "cost_usd": 0,
                        "latencies": [],
                    }

                agent_metrics[source_agent]["calls"] += 1
                agent_metrics[source_agent]["tokens"] += llm_metrics.get("tokens", 0)
                if cost is not None:
                    agent_metrics[source_agent]["cost_usd"] += cost
                if latency > 0:
                    agent_metrics[source_agent]["latencies"].append(latency)

                # Track model usage
                model = llm_metrics.get("model", "unknown")
                if model not in model_usage:
                    model_usage[model] = {
                        "calls": 0,
                        "tokens": 0,
                        "cost_usd": 0,
                    }

                model_usage[model]["calls"] += 1
                model_usage[model]["tokens"] += llm_metrics.get("tokens", 0)
                if cost is not None:
                    model_usage[model]["cost_usd"] += cost

        # Calculate averages
        avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0

        # Calculate per-agent average latencies and clean up the latencies list
        for agent_id in agent_metrics:
            agent_latencies = agent_metrics[agent_id]["latencies"]
            agent_metrics[agent_id]["avg_latency_ms"] = (
                sum(agent_latencies) / len(agent_latencies) if agent_latencies else 0
            )
            # Remove the temporary latencies list to clean up the output
            del agent_metrics[agent_id]["latencies"]

        # Get runtime environment information
        runtime_env = self._get_runtime_environment()

        return {
            "total_duration": round(total_duration, 3),
            "total_llm_calls": total_llm_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 6),
            "avg_latency_ms": round(avg_latency_ms, 2),
            "agent_breakdown": agent_metrics,
            "model_usage": model_usage,
            "runtime_environment": runtime_env,
            "execution_stats": {
                "total_agents_executed": len(logs),
                "run_id": self.run_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    @staticmethod
    def build_previous_outputs(logs):
        """
        Build a dictionary of previous agent outputs from the execution logs.
        Used to provide context to downstream agents.
        """
        outputs = {}
        for log in logs:
            agent_id = log["agent_id"]
            payload = log.get("payload", {})

            # Case: regular agent output
            if "result" in payload:
                outputs[agent_id] = payload["result"]

            # Case: JoinNode with merged dict
            if "result" in payload and isinstance(payload["result"], dict):
                merged = payload["result"].get("merged")
                if isinstance(merged, dict):
                    outputs.update(merged)

        return outputs

    async def run(self, input_data):
        """
        Main execution loop for the orchestrator with comprehensive error handling.
        Always returns a JSON report, even on failure, for debugging purposes.
        """
        logs = []

        try:
            return await self._run_with_comprehensive_error_handling(input_data, logs)
        except Exception as critical_error:
            # Critical failure - save everything we have so far
            self._record_error(
                "critical_failure",
                "orchestrator",
                f"Critical orchestrator failure: {critical_error}",
                critical_error,
            )

            print(f"💥 [ORKA-CRITICAL] Orchestrator failed: {critical_error}")
            error_report_path = self._save_error_report(logs, critical_error)

            # Try to cleanup memory backend
            try:
                self.memory.close()
            except Exception as cleanup_error:
                print(f"⚠️ Failed to cleanup memory backend: {cleanup_error}")

            # Return error report for debugging instead of raising
            return {
                "status": "critical_failure",
                "error": str(critical_error),
                "error_report_path": error_report_path,
                "logs_captured": len(logs),
                "error_telemetry": self.error_telemetry,
            }

    async def _run_with_comprehensive_error_handling(self, input_data, logs):
        """
        Main execution loop with comprehensive error handling wrapper.
        """
        queue = self.orchestrator_cfg["agents"][:]

        while queue:
            agent_id = queue.pop(0)

            try:
                agent = self.agents[agent_id]
                agent_type = agent.type
                self.step_index += 1

                # Build payload for the agent: current input and all previous outputs
                payload = {
                    "input": input_data,
                    "previous_outputs": self.build_previous_outputs(logs),
                }
                freezed_payload = json.dumps(
                    payload,
                )  # Freeze the payload as a string for logging/debug
                print(
                    f"{datetime.now()} > [ORKA] {self.step_index} >  Running agent '{agent_id}' of type '{agent_type}', payload: {freezed_payload}",
                )
                log_entry = {
                    "agent_id": agent_id,
                    "event_type": agent.__class__.__name__,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                start_time = time()

                # Attempt to run agent with retry logic
                max_retries = 3
                retry_count = 0
                agent_result = None

                while retry_count <= max_retries:
                    try:
                        agent_result = await self._execute_single_agent(
                            agent_id,
                            agent,
                            agent_type,
                            payload,
                            input_data,
                            queue,
                            logs,
                        )

                        # If we had retries, record partial success
                        if retry_count > 0:
                            self._record_partial_success(agent_id, retry_count)

                        # Handle waiting status - re-queue the agent
                        if isinstance(agent_result, dict) and agent_result.get("status") in [
                            "waiting",
                            "timeout",
                        ]:
                            if agent_result.get("status") == "waiting":
                                queue.append(agent_id)  # Re-queue for later
                            # For these statuses, we should continue to the next agent in queue
                            continue

                        break  # Success - exit retry loop

                    except Exception as agent_error:
                        retry_count += 1
                        self._record_retry(agent_id)
                        self._record_error(
                            "agent_execution",
                            agent_id,
                            f"Attempt {retry_count} failed: {agent_error}",
                            agent_error,
                            recovery_action="retry" if retry_count <= max_retries else "skip",
                        )

                        if retry_count <= max_retries:
                            print(
                                f"🔄 [ORKA-RETRY] Agent {agent_id} failed, retrying ({retry_count}/{max_retries})",
                            )
                            await asyncio.sleep(1)  # Brief delay before retry
                        else:
                            print(
                                f"❌ [ORKA-SKIP] Agent {agent_id} failed {max_retries} times, skipping",
                            )
                            # Create a failure result
                            agent_result = {
                                "status": "failed",
                                "error": str(agent_error),
                                "retries_attempted": retry_count - 1,
                            }
                            break

                # Process the result (success or failure)
                if agent_result is not None:
                    # Log the result and timing for this step
                    duration = round(time() - start_time, 4)
                    payload_out = {"input": input_data, "result": agent_result}
                    payload_out["previous_outputs"] = payload["previous_outputs"]
                    log_entry["duration"] = duration

                    # Extract LLM metrics if present (even from failed agents)
                    try:
                        llm_metrics = self._extract_llm_metrics(agent, agent_result)
                        if llm_metrics:
                            log_entry["llm_metrics"] = llm_metrics
                    except Exception as metrics_error:
                        self._record_error(
                            "metrics_extraction",
                            agent_id,
                            f"Failed to extract metrics: {metrics_error}",
                            metrics_error,
                            recovery_action="continue",
                        )

                    log_entry["payload"] = payload_out
                    logs.append(log_entry)

                    # Save to memory even if agent failed
                    try:
                        if agent_type != "forknode":
                            self.memory.log(
                                agent_id,
                                agent.__class__.__name__,
                                payload_out,
                                step=self.step_index,
                                run_id=self.run_id,
                            )
                    except Exception as memory_error:
                        self._record_error(
                            "memory_logging",
                            agent_id,
                            f"Failed to log to memory: {memory_error}",
                            memory_error,
                            recovery_action="continue",
                        )

                    print(
                        f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' returned: {agent_result}",
                    )

            except Exception as step_error:
                # Catch-all for any other step-level errors
                self._record_error(
                    "step_execution",
                    agent_id,
                    f"Step execution failed: {step_error}",
                    step_error,
                    recovery_action="continue",
                )
                print(
                    f"⚠️ [ORKA-STEP-ERROR] Step {self.step_index} failed for {agent_id}: {step_error}",
                )
                continue  # Continue to next agent

        # Generate meta report with aggregated metrics
        meta_report = self._generate_meta_report(logs)

        # Save logs to file at the end of the run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")

        # Store meta report in memory for saving
        meta_report_entry = {
            "agent_id": "meta_report",
            "event_type": "MetaReport",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "meta_report": meta_report,
                "run_id": self.run_id,
                "timestamp": timestamp,
            },
        }
        self.memory.memory.append(meta_report_entry)

        # Save to memory backend
        self.memory.save_to_file(log_path)

        # Cleanup memory backend resources to prevent hanging
        try:
            self.memory.close()
        except Exception as e:
            print(f"Warning: Failed to cleanly close memory backend: {e!s}")

        # Print meta report summary
        print("\n" + "=" * 50)
        print("ORKA EXECUTION META REPORT")
        print("=" * 50)
        print(f"Total Execution Time: {meta_report['total_duration']:.3f}s")
        print(f"Total LLM Calls: {meta_report['total_llm_calls']}")
        print(f"Total Tokens: {meta_report['total_tokens']}")
        print(f"Total Cost: ${meta_report['total_cost_usd']:.6f}")
        print(f"Average Latency: {meta_report['avg_latency_ms']:.2f}ms")
        print("=" * 50)

        return logs

    async def _execute_single_agent(
        self,
        agent_id,
        agent,
        agent_type,
        payload,
        input_data,
        queue,
        logs,
    ):
        """
        Execute a single agent with proper error handling and status tracking.
        Returns the result of the agent execution.
        """
        # Handle RouterNode: dynamic routing based on previous outputs
        if agent_type == "routernode":
            decision_key = agent.params.get("decision_key")
            routing_map = agent.params.get("routing_map")
            if decision_key is None:
                raise ValueError("Router agent must have 'decision_key' in params.")
            raw_decision_value = payload["previous_outputs"].get(decision_key)
            normalized = self.normalize_bool(raw_decision_value)
            payload["previous_outputs"][decision_key] = "true" if normalized else "false"

            result = agent.run(payload)
            next_agents = result if isinstance(result, list) else [result]
            # For router nodes, we need to update the queue
            queue.clear()
            queue.extend(next_agents)

            payload_out = {
                "input": input_data,
                "decision_key": decision_key,
                "decision_value": str(raw_decision_value),
                "routing_map": str(routing_map),
                "next_agents": str(next_agents),
            }
            self._add_prompt_to_payload(agent, payload_out, payload)
            return payload_out

        # Handle ForkNode: run multiple agents in parallel branches
        elif agent_type == "forknode":
            result = await agent.run(self, payload)
            fork_targets = agent.config.get("targets", [])
            # Flatten branch steps for parallel execution
            flat_targets = []
            for branch in fork_targets:
                if isinstance(branch, list):
                    flat_targets.extend(branch)
                else:
                    flat_targets.append(branch)
            fork_targets = flat_targets

            if not fork_targets:
                raise ValueError(
                    f"ForkNode '{agent_id}' requires non-empty 'targets' list.",
                )

            fork_group_id = self.fork_manager.generate_group_id(agent_id)
            self.fork_manager.create_group(fork_group_id, fork_targets)
            payload["fork_group_id"] = fork_group_id

            mode = agent.config.get(
                "mode",
                "sequential",
            )  # Default to sequential if not set

            payload_out = {
                "input": input_data,
                "fork_group": fork_group_id,
                "fork_targets": fork_targets,
            }
            self._add_prompt_to_payload(agent, payload_out, payload)

            self.memory.log(
                agent_id,
                agent.__class__.__name__,
                payload_out,
                step=self.step_index,
                run_id=self.run_id,
            )

            print(
                f"{datetime.now()} > [ORKA][FORK][PARALLEL] {self.step_index} >  Running forked agents in parallel for group {fork_group_id}",
            )
            fork_logs = await self.run_parallel_agents(
                fork_targets,
                fork_group_id,
                input_data,
                payload["previous_outputs"],
            )
            logs.extend(fork_logs)  # Add forked agent logs to the main log
            return payload_out

        # Handle JoinNode: wait for all forked agents to finish, then join results
        elif agent_type == "joinnode":
            fork_group_id = self.memory.hget(
                f"fork_group_mapping:{agent.group_id}",
                "group_id",
            )
            if fork_group_id:
                fork_group_id = (
                    fork_group_id.decode() if isinstance(fork_group_id, bytes) else fork_group_id
                )
            else:
                fork_group_id = agent.group_id  # fallback

            payload["fork_group_id"] = fork_group_id  # inject
            result = agent.run(payload)
            payload_out = {
                "input": input_data,
                "fork_group_id": fork_group_id,
                "result": result,
            }
            self._add_prompt_to_payload(agent, payload_out, payload)

            if not fork_group_id:
                raise ValueError(
                    f"JoinNode '{agent_id}' missing required group_id.",
                )

            # Handle different JoinNode statuses
            if result.get("status") == "waiting":
                print(
                    f"{datetime.now()} > [ORKA][JOIN][WAITING] {self.step_index} > Node '{agent_id}' is still waiting on fork group: {fork_group_id}",
                )
                queue.append(agent_id)
                self.memory.log(
                    agent_id,
                    agent.__class__.__name__,
                    payload_out,
                    step=self.step_index,
                    run_id=self.run_id,
                )
                # Return waiting status instead of continue
                return {"status": "waiting", "result": result}
            elif result.get("status") == "timeout":
                print(
                    f"{datetime.now()} > [ORKA][JOIN][TIMEOUT] {self.step_index} > Node '{agent_id}' timed out waiting for fork group: {fork_group_id}",
                )
                self.memory.log(
                    agent_id,
                    agent.__class__.__name__,
                    payload_out,
                    step=self.step_index,
                    run_id=self.run_id,
                )
                # Clean up the fork group even on timeout
                self.fork_manager.delete_group(fork_group_id)
                return {"status": "timeout", "result": result}
            elif result.get("status") == "done":
                self.fork_manager.delete_group(
                    fork_group_id,
                )  # Clean up fork group after successful join

            return payload_out

        else:
            # Normal Agent: run and handle result

            # Render prompt before running agent if agent has a prompt
            self._render_agent_prompt(agent, payload)

            if agent_type in ("memoryreadernode", "memorywriternode"):
                # Memory nodes have async run methods
                result = await agent.run(payload)
            else:
                # Regular synchronous agent
                result = agent.run(payload)

            # If agent is waiting (e.g., for async input), return waiting status
            if isinstance(result, dict) and result.get("status") == "waiting":
                print(
                    f"{datetime.now()} > [ORKA][WAITING] {self.step_index} > Node '{agent_id}' is still waiting: {result.get('received')}",
                )
                queue.append(agent_id)
                return {"status": "waiting", "result": result}

            # After normal agent finishes, mark it done if it's part of a fork
            fork_group = payload.get("input", {})
            if fork_group:
                self.fork_manager.mark_agent_done(fork_group, agent_id)

            # Check if this agent has a next-in-sequence step in its branch
            next_agent = self.fork_manager.next_in_sequence(fork_group, agent_id)
            if next_agent:
                print(
                    f"{datetime.now()} > [ORKA][FORK-SEQUENCE] {self.step_index} > Agent '{agent_id}' finished. Enqueuing next in sequence: '{next_agent}'",
                )
                self.enqueue_fork([next_agent], fork_group)

            payload_out = {"input": input_data, "result": result}
            self._add_prompt_to_payload(agent, payload_out, payload)
            return payload_out

    async def _run_agent_async(self, agent_id, input_data, previous_outputs):
        """
        Run a single agent asynchronously.
        """
        agent = self.agents[agent_id]
        payload = {"input": input_data, "previous_outputs": previous_outputs}

        # Render prompt before running agent if agent has a prompt
        self._render_agent_prompt(agent, payload)

        # Inspect the run method to see if it needs orchestrator
        run_method = agent.run
        sig = inspect.signature(run_method)
        needs_orchestrator = len(sig.parameters) > 1  # More than just 'self'
        is_async = inspect.iscoroutinefunction(run_method)

        if needs_orchestrator:
            # Node that needs orchestrator
            result = run_method(self, payload)
            if is_async or asyncio.iscoroutine(result):
                result = await result
        elif is_async:
            # Async node/agent that doesn't need orchestrator
            result = await run_method(payload)
        else:
            # Synchronous agent
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, run_method, payload)

        return agent_id, result

    async def _run_branch_async(self, branch_agents, input_data, previous_outputs):
        """
        Run a sequence of agents in a branch sequentially.
        """
        branch_results = {}
        for agent_id in branch_agents:
            agent_id, result = await self._run_agent_async(
                agent_id,
                input_data,
                previous_outputs,
            )
            branch_results[agent_id] = result
            # Update previous_outputs for the next agent in the branch
            previous_outputs = {**previous_outputs, **branch_results}
        return branch_results

    async def run_parallel_agents(
        self,
        agent_ids,
        fork_group_id,
        input_data,
        previous_outputs,
    ):
        """
        Run multiple branches in parallel, with agents within each branch running sequentially.
        Returns a list of log entries for each forked agent.
        """
        # Get the fork node to understand the branch structure
        # Fork group ID format: {node_id}_{timestamp}, so we need to remove the timestamp
        fork_node_id = "_".join(
            fork_group_id.split("_")[:-1],
        )  # Remove the last part (timestamp)
        fork_node = self.agents[fork_node_id]
        branches = fork_node.targets

        # Run each branch in parallel
        branch_tasks = [
            self._run_branch_async(branch, input_data, previous_outputs) for branch in branches
        ]

        # Wait for all branches to complete
        branch_results = await asyncio.gather(*branch_tasks)

        # Process results and create logs
        forked_step_index = 0
        result_logs = []
        updated_previous_outputs = previous_outputs.copy()

        # Flatten branch results into a single list of (agent_id, result) pairs
        all_results = []
        for branch_result in branch_results:
            all_results.extend(branch_result.items())

        for agent_id, result in all_results:
            forked_step_index += 1
            step_index = f"{self.step_index}[{forked_step_index}]"

            # Ensure result is awaited if it's a coroutine
            if asyncio.iscoroutine(result):
                result = await result

            # Save result to Redis for JoinNode
            join_state_key = "waitfor:join_parallel_checks:inputs"
            self.memory.hset(join_state_key, agent_id, json.dumps(result))

            # Create log entry with current previous_outputs (before updating with this agent's result)
            payload_data = {"result": result}
            agent = self.agents[agent_id]
            payload_context = {
                "input": input_data,
                "previous_outputs": updated_previous_outputs,
            }
            self._add_prompt_to_payload(agent, payload_data, payload_context)

            log_data = {
                "agent_id": agent_id,
                "event_type": f"ForkedAgent-{self.agents[agent_id].__class__.__name__}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload_data,
                "previous_outputs": updated_previous_outputs.copy(),
                "step": step_index,
                "run_id": self.run_id,
            }
            result_logs.append(log_data)

            # Log to memory
            self.memory.log(
                agent_id,
                f"ForkedAgent-{self.agents[agent_id].__class__.__name__}",
                payload_data,
                step=step_index,
                run_id=self.run_id,
                previous_outputs=updated_previous_outputs.copy(),
            )

            # Update previous_outputs with this agent's result AFTER logging
            updated_previous_outputs[agent_id] = result

        return result_logs
