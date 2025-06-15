# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import logging
import os
import platform
import subprocess
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MetaReportGenerator:
    """
    Generates meta reports with aggregated metrics from execution logs.
    """

    def __init__(self):
        """Initialize the meta report generator."""

    def generate_meta_report(self, logs):
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
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _get_runtime_environment(self):
        """
        Get runtime environment information for debugging and reproducibility.
        """
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

    def generate_execution_summary(self, logs, meta_report):
        """
        Generate a human-readable execution summary.

        Args:
            logs: Execution logs
            meta_report: Meta report data

        Returns:
            str: Formatted execution summary
        """
        summary_lines = [
            "=" * 60,
            "ORKA EXECUTION SUMMARY",
            "=" * 60,
            f"Total Execution Time: {meta_report['total_duration']:.3f}s",
            f"Total Agents Executed: {len(logs)}",
            f"Total LLM Calls: {meta_report['total_llm_calls']}",
            f"Total Tokens: {meta_report['total_tokens']:,}",
            f"Total Cost: ${meta_report['total_cost_usd']:.6f}",
            f"Average Latency: {meta_report['avg_latency_ms']:.2f}ms",
            "",
            "Agent Breakdown:",
        ]

        # Add agent breakdown
        for agent_id, metrics in meta_report.get("agent_breakdown", {}).items():
            summary_lines.append(
                f"  {agent_id}: {metrics['calls']} calls, "
                f"{metrics['tokens']} tokens, "
                f"${metrics['cost_usd']:.4f}",
            )

        summary_lines.extend(
            [
                "",
                "Model Usage:",
            ],
        )

        # Add model usage
        for model, usage in meta_report.get("model_usage", {}).items():
            summary_lines.append(
                f"  {model}: {usage['calls']} calls, "
                f"{usage['tokens']} tokens, "
                f"${usage['cost_usd']:.4f}",
            )

        summary_lines.append("=" * 60)

        return "\n".join(summary_lines)
