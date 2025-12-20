# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Cost Analysis Mixin
===================

Methods for extracting and analyzing cost/token data from agent executions.
"""

import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class CostAnalysisMixin:
    """Mixin providing cost analysis extraction methods."""

    # Expected from host class
    _blob_store: dict[str, Any]
    _blob_threshold: int

    def save_enhanced_trace(
        self, file_path: str, enhanced_data: Dict[str, Any]
    ) -> None:
        """Save enhanced trace data with memory backend references and blob deduplication."""
        try:
            deduplicated_data = self._apply_deduplication_to_enhanced_trace(enhanced_data)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(deduplicated_data, f, indent=2, default=str)

            if (
                "_metadata" in deduplicated_data
                and "deduplication_enabled" in deduplicated_data["_metadata"]
            ):
                if deduplicated_data["_metadata"]["deduplication_enabled"]:
                    stats = deduplicated_data["_metadata"].get("stats", {})
                    blob_count = deduplicated_data["_metadata"].get("total_blobs_stored", 0)
                    size_reduction = stats.get("size_reduction", 0)
                    logger.info(
                        f"Enhanced trace saved with deduplication: "
                        f"{blob_count} blobs, {size_reduction} bytes saved"
                    )
                else:
                    logger.info("Enhanced trace saved (no deduplication needed)")
            else:
                logger.info(f"Enhanced trace saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save enhanced trace with deduplication: {e}")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(enhanced_data, f, indent=2, default=str)
                logger.info(f"Enhanced trace saved (fallback mode) to {file_path}")
            except Exception as fallback_e:
                logger.error(f"Fallback save also failed: {fallback_e}")
                self.save_to_file(file_path)

    def _apply_deduplication_to_enhanced_trace(
        self, enhanced_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply blob deduplication to enhanced trace data."""
        try:
            original_blob_store = getattr(self, "_blob_store", {})
            self._blob_store = {}

            events = []
            blob_stats = {
                "total_entries": 0,
                "deduplicated_blobs": 0,
                "size_reduction": 0,
            }

            if "agent_executions" in enhanced_data:
                for execution in enhanced_data["agent_executions"]:
                    blob_stats["total_entries"] += 1

                    event = {
                        "agent_id": execution.get("agent_id"),
                        "event_type": execution.get("event_type"),
                        "timestamp": execution.get("timestamp"),
                    }

                    for key in ["step", "run_id", "fork_group", "parent"]:
                        if key in execution:
                            event[key] = execution[key]

                    if "payload" in execution:
                        payload = execution["payload"]
                        payload_size = len(
                            json.dumps(payload, separators=(",", ":"), default=json_serializer)
                        )

                        if payload_size > getattr(self, "_blob_threshold", 200):
                            original_size = payload_size
                            deduplicated_payload = self._deduplicate_dict_content(payload)
                            new_size = len(
                                json.dumps(
                                    deduplicated_payload,
                                    separators=(",", ":"),
                                    default=json_serializer,
                                )
                            )

                            if new_size < original_size:
                                blob_stats["deduplicated_blobs"] += 1
                                blob_stats["size_reduction"] += original_size - new_size

                            event["payload"] = deduplicated_payload
                        else:
                            event["payload"] = payload

                    for key in ["memory_references", "template_resolution"]:
                        if key in execution:
                            event[key] = execution[key]

                    events.append(event)

            use_dedup_format = bool(self._blob_store)

            if use_dedup_format:
                cost_analysis = self._extract_cost_analysis(enhanced_data, events)
                result = {
                    "_metadata": {
                        "version": "1.2.0",
                        "deduplication_enabled": True,
                        "blob_threshold_chars": getattr(self, "_blob_threshold", 200),
                        "total_blobs_stored": len(self._blob_store),
                        "stats": blob_stats,
                        "generated_at": datetime.now(UTC).isoformat(),
                    },
                    "blob_store": self._blob_store.copy(),
                    "events": events,
                    "cost_analysis": cost_analysis,
                }
            else:
                result = enhanced_data.copy()
                result["_metadata"] = {
                    "version": "1.2.0",
                    "deduplication_enabled": False,
                    "generated_at": datetime.now(UTC).isoformat(),
                }
                result["cost_analysis"] = self._extract_cost_analysis(enhanced_data, events)

            self._blob_store = original_blob_store
            return result

        except Exception as e:
            logger.error(f"Failed to apply deduplication to enhanced trace: {e}")
            if "original_blob_store" in locals():
                self._blob_store = original_blob_store
            return enhanced_data

    def _extract_cost_analysis(
        self, enhanced_data: Dict[str, Any], events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract token and cost analysis from agent executions."""
        try:
            cost_analysis: Dict[str, Any] = {
                "summary": {
                    "total_agents": 0,
                    "total_tokens": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_latency_ms": 0.0,
                    "models_used": set(),
                    "providers_used": set(),
                },
                "agents": {},
                "by_model": {},
                "by_provider": {},
            }

            for event in events:
                agent_id = event.get("agent_id")
                event_type = event.get("event_type")

                if not agent_id or not event_type or "LLMAgent" not in str(event_type):
                    continue

                metrics = self._extract_agent_metrics(event, enhanced_data)

                if metrics:
                    if agent_id not in cost_analysis["agents"]:
                        cost_analysis["agents"][agent_id] = {
                            "executions": 0,
                            "total_tokens": 0,
                            "total_prompt_tokens": 0,
                            "total_completion_tokens": 0,
                            "total_cost_usd": 0.0,
                            "total_latency_ms": 0.0,
                            "models": set(),
                            "providers": set(),
                            "event_type": event_type,
                        }

                    agent_data = cost_analysis["agents"][agent_id]
                    agent_data["executions"] += 1
                    agent_data["total_tokens"] += metrics.get("tokens", 0)
                    agent_data["total_prompt_tokens"] += metrics.get("prompt_tokens", 0)
                    agent_data["total_completion_tokens"] += metrics.get("completion_tokens", 0)
                    agent_data["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    agent_data["total_latency_ms"] += metrics.get("latency_ms", 0.0)

                    model = metrics.get("model", "unknown")
                    provider = metrics.get("provider", "unknown")
                    agent_data["models"].add(model)
                    agent_data["providers"].add(provider)

                    summary = cost_analysis["summary"]
                    summary["total_agents"] += 1
                    summary["total_tokens"] += metrics.get("tokens", 0)
                    summary["total_prompt_tokens"] += metrics.get("prompt_tokens", 0)
                    summary["total_completion_tokens"] += metrics.get("completion_tokens", 0)
                    summary["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    summary["total_latency_ms"] += metrics.get("latency_ms", 0.0)
                    summary["models_used"].add(model)
                    summary["providers_used"].add(provider)

                    if model not in cost_analysis["by_model"]:
                        cost_analysis["by_model"][model] = {
                            "agents": 0,
                            "total_tokens": 0,
                            "total_cost_usd": 0.0,
                            "total_latency_ms": 0.0,
                        }
                    model_data = cost_analysis["by_model"][model]
                    model_data["agents"] += 1
                    model_data["total_tokens"] += metrics.get("tokens", 0)
                    model_data["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    model_data["total_latency_ms"] += metrics.get("latency_ms", 0.0)

                    if provider not in cost_analysis["by_provider"]:
                        cost_analysis["by_provider"][provider] = {
                            "agents": 0,
                            "total_tokens": 0,
                            "total_cost_usd": 0.0,
                            "total_latency_ms": 0.0,
                        }
                    provider_data = cost_analysis["by_provider"][provider]
                    provider_data["agents"] += 1
                    provider_data["total_tokens"] += metrics.get("tokens", 0)
                    provider_data["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    provider_data["total_latency_ms"] += metrics.get("latency_ms", 0.0)

            # Convert sets to lists for JSON serialization
            cost_analysis["summary"]["models_used"] = list(
                cost_analysis["summary"]["models_used"]
            )
            cost_analysis["summary"]["providers_used"] = list(
                cost_analysis["summary"]["providers_used"]
            )

            for agent_data in cost_analysis["agents"].values():
                agent_data["models"] = list(agent_data["models"])
                agent_data["providers"] = list(agent_data["providers"])

            return cost_analysis

        except Exception as e:
            logger.error(f"Failed to extract cost analysis: {e}")
            return {"error": str(e)}

    def _extract_agent_metrics(
        self, event: Dict[str, Any], enhanced_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract metrics from an agent event, resolving blob references if needed."""
        try:
            payload = event.get("payload", {})

            if isinstance(payload, dict) and payload.get("_type") == "blob_reference":
                blob_ref = payload.get("ref")
                if blob_ref and hasattr(self, "_blob_store") and blob_ref in self._blob_store:
                    resolved_payload = self._blob_store[blob_ref]
                elif (
                    blob_ref
                    and "blob_store" in enhanced_data
                    and blob_ref in enhanced_data["blob_store"]
                ):
                    resolved_payload = enhanced_data["blob_store"][blob_ref]
                else:
                    return {}
            else:
                resolved_payload = payload

            metrics = {}

            if "_metrics" in resolved_payload:
                metrics = resolved_payload["_metrics"]
            elif isinstance(resolved_payload, list):
                for item in resolved_payload:
                    if isinstance(item, dict):
                        self._extract_metrics_recursive(item, metrics)
            else:
                self._extract_metrics_recursive(resolved_payload, metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to extract agent metrics: {e}")
            return {}

    def _extract_metrics_recursive(
        self,
        data: Any,
        metrics: Dict[str, Any],
        max_depth: int = 10,
        current_depth: int = 0,
    ) -> None:
        """Recursively search for _metrics fields in nested dictionaries."""
        if current_depth >= max_depth or not isinstance(data, dict):
            return

        for key, value in data.items():
            if key == "_metrics" and isinstance(value, dict):
                for metric_key, metric_value in value.items():
                    if metric_key in ["tokens", "prompt_tokens", "completion_tokens"]:
                        metrics[metric_key] = metrics.get(metric_key, 0) + metric_value
                    elif metric_key in ["cost_usd", "latency_ms"]:
                        metrics[metric_key] = metrics.get(metric_key, 0.0) + metric_value
                    else:
                        if metric_key not in metrics:
                            metrics[metric_key] = metric_value
            elif isinstance(value, dict):
                self._extract_metrics_recursive(value, metrics, max_depth, current_depth + 1)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._extract_metrics_recursive(
                            item, metrics, max_depth, current_depth + 1
                        )

    # Stubs for methods provided by other mixins
    def _deduplicate_dict_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Stub - provided by BlobDeduplicationMixin."""
        return data

    def save_to_file(self, file_path: str) -> None:
        """Stub - provided by FileOperationsMixin."""
        raise NotImplementedError

