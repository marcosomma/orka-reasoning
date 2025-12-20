from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ExtractionStats:
    total_log_entries: int = 0
    agent_entries: int = 0
    successful_extractions: int = 0
    extraction_methods: dict[str, int] = field(default_factory=dict)


def _record_method(stats: ExtractionStats, method: str) -> None:
    stats.extraction_methods[method] = stats.extraction_methods.get(method, 0) + 1


def _extract_from_orchestrator_payload(log_entry: dict[str, Any]) -> tuple[bool, Any, str]:
    """Prefer the orchestrator's canonical log schema.

    Orka's execution engine writes log entries like:
      {"agent_id": "...", "event_type": "...", "payload": {"result": ..., "response": ..., ...}}

    LoopNode's internal workflow runner uses that engine, so this should cover the
    vast majority of loop executions without any ad-hoc heuristics.
    """
    payload = log_entry.get("payload")
    if not isinstance(payload, dict):
        return False, None, ""

    # Canonical: payload.result is the structured result for the agent.
    if "result" in payload:
        return True, payload.get("result"), "orchestrator.payload.result"

    # Fallback: some logs may only have payload.response.
    if "response" in payload:
        return True, {"response": payload.get("response")}, "orchestrator.payload.response"

    return False, None, ""


def extract_agent_results_from_logs(
    logs: list[Any], *, legacy_fallback: bool = True
) -> tuple[dict[str, Any], list[str], ExtractionStats]:
    """Extract agent results from Orchestrator logs.

    This is a direct extraction of LoopNode's current heuristics, preserved so we can
    refactor internal workflow execution safely.
    """
    agents_results: Dict[str, Any] = {}
    executed_agents: list[str] = []
    stats = ExtractionStats(total_log_entries=len(logs))

    for log_entry in logs:
        if isinstance(log_entry, dict) and log_entry.get("event_type") == "MetaReport":
            continue

        if not isinstance(log_entry, dict):
            continue

        agent_id = log_entry.get("agent_id")
        if not agent_id:
            continue

        executed_agents.append(agent_id)
        stats.agent_entries += 1

        result_found = False
        extraction_method: Optional[str] = None

        # Strategy 0: Orchestrator canonical payload schema
        if not result_found:
            found, extracted, method = _extract_from_orchestrator_payload(log_entry)
            if found:
                agents_results[agent_id] = extracted
                result_found = True
                extraction_method = method

        # Strategy 1: Standard payload.result (for most agents)
        if not result_found and "payload" in log_entry:
            payload = log_entry["payload"]
            if isinstance(payload, dict) and "result" in payload:
                agents_results[agent_id] = payload["result"]
                result_found = True
                extraction_method = "payload.result"

        # Strategy 2: Check if the log entry itself contains result data
        if not result_found and "result" in log_entry:
            agents_results[agent_id] = log_entry["result"]
            result_found = True
            extraction_method = "direct_result"

        # Strategy 3: Extract from structured log content (for embedded results)
        if not result_found and legacy_fallback:
            log_content = str(log_entry)
            if f'\"{agent_id}\":' in log_content and '\"response\":' in log_content:
                try:
                    pattern = f'\"{re.escape(str(agent_id))}\":\\s*\\{{[^}}]+\\}}'
                    match = re.search(pattern, log_content)
                    if match:
                        agent_data_str = "{" + match.group(0) + "}"
                        try:
                            agent_data = json.loads(agent_data_str)
                            if agent_id in agent_data:
                                agents_results[agent_id] = agent_data[agent_id]
                                result_found = True
                                extraction_method = "embedded_json"
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    logger.debug("Failed to parse embedded JSON for %s: %s", agent_id, e)

        # Strategy 4: response/content patterns in log entry
        if not result_found:
            potential_response = None
            if "response" in log_entry:
                potential_response = {"response": log_entry["response"]}
            elif "content" in log_entry:
                potential_response = {"response": log_entry["content"]}
            elif "output" in log_entry:
                potential_response = {"response": log_entry["output"]}
            elif "payload" in log_entry and isinstance(log_entry["payload"], dict):
                payload = log_entry["payload"]
                if "response" in payload:
                    potential_response = {"response": payload["response"]}
                elif "content" in payload:
                    potential_response = {"response": payload["content"]}
                elif "output" in payload:
                    potential_response = {"response": payload["output"]}

            if potential_response is not None:
                agents_results[agent_id] = potential_response
                result_found = True
                extraction_method = "response_pattern"

        # Strategy 5: Search for agent data in the entire log structure
        if not result_found and legacy_fallback:
            full_content = str(log_entry)
            score_indicators = [
                "AGREEMENT_SCORE:",
                "SCORE:",
                "score:",
                "Score:",
                "RATING:",
                "rating:",
            ]
            for indicator in score_indicators:
                if indicator in full_content and str(agent_id) in full_content:
                    agents_results[agent_id] = {"response": full_content}
                    result_found = True
                    extraction_method = "content_search"
                    break

        if result_found:
            stats.successful_extractions += 1
            if extraction_method:
                _record_method(stats, extraction_method)
                if legacy_fallback and extraction_method in {"embedded_json", "content_search"}:
                    logger.debug(
                        "Loop log extraction used legacy heuristic '%s' for agent '%s'",
                        extraction_method,
                        agent_id,
                    )
        else:
            # Keep behavior: just log debug; do not raise
            logger.debug("❌ No result found for '%s' - Available keys: %s", agent_id, list(log_entry.keys()))

    return agents_results, executed_agents, stats


