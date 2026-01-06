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
Metrics Collection and Reporting
===============================

Handles LLM metrics extraction, aggregation, and reporting.
"""

import logging
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Handles metrics collection, aggregation, and reporting.
    """

    def _extract_llm_metrics(self, agent: Any, result: Any) -> Dict[str, Any] | None:
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
            metrics: Dict[str, Any] = result["_metrics"]
            return metrics

        # Check if agent has stored metrics (for binary/classification agents)
        if hasattr(agent, "_last_metrics") and agent._last_metrics:
            agent_metrics: Dict[str, Any] = agent._last_metrics
            return agent_metrics

        return None

    def _get_runtime_environment(self) -> Dict[str, Any]:
        """
        Get runtime environment information for debugging and reproducibility.
        """
        env_info: Dict[str, Any] = {
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
        except Exception:
            env_info["git_sha"] = "unknown"

        # Check for Docker environment
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            env_info["docker_image"] = os.environ.get("DOCKER_IMAGE")
        else:
            env_info["docker_image"] = None

        # GPU information
        try:
            # Use shutil.which to check for nvidia-smi (no deprecation warning)
            nvidia_smi_path = shutil.which("nvidia-smi")
            if nvidia_smi_path:
                # Query GPU information using nvidia-smi
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    gpu_names = [
                        line.strip() for line in result.stdout.strip().split("\n") if line.strip()
                    ]
                    if gpu_names:
                        gpu_count = len(gpu_names)
                        env_info["gpu_type"] = (
                            f"{gpu_names[0]} ({gpu_count} GPU{'s' if gpu_count > 1 else ''})"
                        )
                    else:
                        env_info["gpu_type"] = "none"
                else:
                    env_info["gpu_type"] = "none"
            else:
                env_info["gpu_type"] = "none"
        except Exception:
            env_info["gpu_type"] = "unknown"

        # Pricing version (current month-year)
        env_info["pricing_version"] = "2025-01"

        return env_info

    run_id: Any

    def _generate_meta_report(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a meta report with aggregated metrics from execution logs.

        Args:
            logs: List of execution log entries

        Returns:
            dict: Meta report with aggregated metrics
        """
        total_duration = 0.0
        total_tokens = 0.0
        total_cost_usd = 0.0
        total_llm_calls = 0
        latencies: List[float] = []

        agent_metrics: Dict[str, Any] = {}
        model_usage: Dict[str, Any] = {}

        # Track seen metrics to avoid double-counting due to deduplication
        seen_metrics = set()

        def extract_metrics_recursively(
            data: Any, source_agent_id: str = "unknown"
        ) -> List[Tuple[Dict[str, Any], str]]:
            """Recursively extract _metrics from nested data structures, avoiding duplicates."""
            found_metrics: List[Tuple[Dict[str, Any], str]] = []

            if isinstance(data, dict):
                # Check if this dict has _metrics
                if "_metrics" in data:
                    metrics: Dict[str, Any] = data["_metrics"]
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

                # GraphScout-specific: extract metrics from decision_trace candidates
                if "decision_trace" in data:
                    candidates = data.get("decision_trace", {}).get("candidates", [])
                    for candidate in candidates:
                        eval_result = candidate.get("evaluation_result", {})
                        if "_metrics" in eval_result:
                            sub_metrics = extract_metrics_recursively(
                                eval_result, source_agent_id
                            )
                            found_metrics.extend(sub_metrics)

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
            all_metrics: List[Tuple[Dict[str, Any], str]] = []

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
                cost: float | None = llm_metrics.get("cost_usd")
                if cost is not None:
                    total_cost_usd += cost
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

                latency: float = llm_metrics.get("latency_ms", 0)
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
    def build_previous_outputs(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a dictionary of previous agent outputs from the execution logs.
        Used to provide context to downstream agents.
        """
        outputs: Dict[str, Any] = {}
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

            # Case: Current run agent responses
            if "response" in payload:
                outputs[agent_id] = {
                    "response": payload["response"],
                    "confidence": payload.get("confidence", "0.0"),
                    "internal_reasoning": payload.get("internal_reasoning", ""),
                    "_metrics": payload.get("_metrics", {}),
                    "formatted_prompt": payload.get("formatted_prompt", ""),
                }

            # Case: Memory agent responses
            if "memories" in payload:
                outputs[agent_id] = {
                    "memories": payload["memories"],
                    "query": payload.get("query", ""),
                    "backend": payload.get("backend", ""),
                    "search_type": payload.get("search_type", ""),
                    "num_results": payload.get("num_results", 0),
                }

        return outputs
