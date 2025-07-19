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
Metrics Collection and Reporting.

Handles LLM metrics extraction, aggregation, and reporting.
"""

import logging
import os
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

logger = logging.getLogger(__name__)

# Type aliases
AgentId = str
AgentMetrics = Dict[str, Union[int, float, List[float]]]
ModelUsage = Dict[str, Dict[str, Union[int, float]]]
MetricsId = Tuple[str, int, int, int, int, float]
LLMMetrics = Dict[str, Union[str, int, float]]
LogEntry = Dict[str, Any]
EnvironmentInfo = Dict[str, Optional[str]]


class MetricsCollector:
    """Handles metrics collection, aggregation, and reporting."""

    def _extract_llm_metrics(
        self, agent: Any, result: Union[Dict[str, Any], Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract LLM metrics from agent result or agent state.

        Args:
            agent: The agent instance
            result: The agent's result

        Returns:
            LLM metrics if found, None otherwise
        """
        # Check if result is a dict with _metrics
        if isinstance(result, dict) and "_metrics" in result:
            return result["_metrics"]

        # Check if agent has stored metrics (for binary/classification agents)
        if hasattr(agent, "_last_metrics") and agent._last_metrics:
            return agent._last_metrics

        return None

    def _get_runtime_environment(self) -> EnvironmentInfo:
        """
        Get runtime environment information for debugging and reproducibility.

        Returns:
            Dictionary containing environment information.
        """
        env_info: EnvironmentInfo = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_sha": "unknown",
            "docker_image": None,
            "gpu_type": "unknown",
            "pricing_version": "2025-01",
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
        except Exception:
            pass

        # Check for Docker environment
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            env_info["docker_image"] = os.environ.get("DOCKER_IMAGE", "unknown")

        # GPU information
        try:
            # Ignore GPUtil import error since it's optional
            import GPUtil  # type: ignore

            gpus = GPUtil.getGPUs()
            if gpus:
                env_info["gpu_type"] = (
                    f"{gpus[0].name} ({len(gpus)} GPU{'s' if len(gpus) > 1 else ''})"
                )
            else:
                env_info["gpu_type"] = "none"
        except ImportError:
            pass

        return env_info

    def _generate_meta_report(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """
        Generate a meta report with aggregated metrics from execution logs.

        Args:
            logs: List of execution log entries

        Returns:
            Meta report with aggregated metrics
        """
        total_duration: float = 0.0
        total_tokens: int = 0
        total_cost_usd: float = 0.0
        total_llm_calls: int = 0
        latencies: List[float] = []

        agent_metrics: Dict[AgentId, Dict[str, Any]] = {}
        model_usage: ModelUsage = {}

        # Track seen metrics to avoid double-counting due to deduplication
        seen_metrics: Set[MetricsId] = set()

        def extract_metrics_recursively(
            data: Any, source_agent_id: str = "unknown"
        ) -> List[Tuple[LLMMetrics, AgentId]]:
            """
            Recursively extract _metrics from nested data structures, avoiding duplicates.

            Args:
                data: The data structure to search through
                source_agent_id: ID of the agent that generated the metrics

            Returns:
                List of tuples containing metrics and their source agent IDs
            """
            found_metrics: List[Tuple[LLMMetrics, AgentId]] = []

            if isinstance(data, dict):
                # Check if this dict has _metrics
                if "_metrics" in data:
                    metrics = data["_metrics"]
                    # Create a unique identifier for this metrics object
                    metrics_id = (
                        str(metrics.get("model", "")),
                        int(metrics.get("tokens", 0)),
                        int(metrics.get("prompt_tokens", 0)),
                        int(metrics.get("completion_tokens", 0)),
                        int(metrics.get("latency_ms", 0)),
                        float(metrics.get("cost_usd", 0.0)),
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
            duration = float(log_entry.get("duration", 0))
            total_duration += duration

            agent_id = str(log_entry.get("agent_id", "unknown"))

            # Extract all LLM metrics from the log entry recursively
            all_metrics: List[Tuple[LLMMetrics, AgentId]] = []

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
                total_tokens += int(llm_metrics.get("tokens", 0))

                # Handle null costs (real local LLM cost calculation may return None)
                cost = llm_metrics.get("cost_usd")
                if cost is not None:
                    total_cost_usd += float(cost)
                else:
                    # Check if we should fail on null costs
                    if os.environ.get("ORKA_LOCAL_COST_POLICY") == "null_fail":
                        raise ValueError(
                            f"Pipeline failed due to null cost in agent '{source_agent}' "
                            f"(model: {llm_metrics.get('model', 'unknown')}). "
                            f"Configure real cost calculation or use cloud models.",
                        )
                    logger.warning(
                        f"Agent '{source_agent}' returned null cost - excluding from total",
                    )

                latency = float(llm_metrics.get("latency_ms", 0))
                if latency > 0:
                    latencies.append(latency)

                # Track per-agent metrics (use the source agent, which could be nested)
                if source_agent not in agent_metrics:
                    agent_metrics[source_agent] = {
                        "calls": 0,
                        "tokens": 0,
                        "cost_usd": 0.0,
                        "latencies": [],
                    }

                agent_metrics[source_agent]["calls"] = agent_metrics[source_agent]["calls"] + 1
                agent_metrics[source_agent]["tokens"] = agent_metrics[source_agent]["tokens"] + int(
                    llm_metrics.get("tokens", 0)
                )
                if cost is not None:
                    agent_metrics[source_agent]["cost_usd"] = agent_metrics[source_agent][
                        "cost_usd"
                    ] + float(cost)
                if latency > 0:
                    agent_metrics[source_agent]["latencies"].append(latency)  # type: ignore

                # Track model usage
                model = str(llm_metrics.get("model", "unknown"))
                if model not in model_usage:
                    model_usage[model] = {
                        "calls": 0,
                        "tokens": 0,
                        "cost_usd": 0.0,
                    }

                model_usage[model]["calls"] += 1
                model_usage[model]["tokens"] += int(llm_metrics.get("tokens", 0))
                if cost is not None:
                    model_usage[model]["cost_usd"] += float(cost)

        # Calculate averages
        avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0

        # Calculate per-agent average latencies and clean up the latencies list
        for agent_id in agent_metrics:
            agent_latencies = agent_metrics[agent_id].get("latencies", [])
            agent_metrics[agent_id]["avg_latency_ms"] = (
                sum(agent_latencies) / len(agent_latencies) if agent_latencies else 0.0
            )
            # Remove the latencies list to clean up the output
            if "latencies" in agent_metrics[agent_id]:
                del agent_metrics[agent_id]["latencies"]

        # Build the final report
        return {
            "total_duration_ms": total_duration,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "total_llm_calls": total_llm_calls,
            "avg_latency_ms": avg_latency_ms,
            "agent_metrics": agent_metrics,
            "model_usage": model_usage,
            "environment": self._get_runtime_environment(),
        }

    @staticmethod
    def build_previous_outputs(logs: List[LogEntry]) -> Dict[str, Any]:
        """
        Build a dictionary of previous outputs from execution logs.

        Args:
            logs: List of execution log entries

        Returns:
            Dictionary mapping agent IDs to their outputs
        """
        outputs: Dict[str, Any] = {}
        for log in logs:
            agent_id = log.get("agent_id")
            if agent_id and "payload" in log:
                outputs[agent_id] = log["payload"]
        return outputs
