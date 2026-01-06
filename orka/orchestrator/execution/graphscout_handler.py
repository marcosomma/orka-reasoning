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

"""GraphScoutHandler

Handles GraphScout agent decisions and converts them into queue mutations.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class GraphScoutHandler:
    """Encapsulates GraphScout decision processing."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def handle(self, agent_id: str, agent_result: Any, logs: List[Dict[str, Any]], input_data: Any) -> None:
        """Process GraphScout agent result and mutate engine.queue as needed.

        Supports OrkaResponse-style (decision in result field) and legacy-style
        (decision at top-level) formats. If GraphScout returns a shortlist, the
        handler will use engine._select_best_candidate_from_shortlist (if
        available) to pick the final target.
        """
        engine = self.engine

        try:
            if not isinstance(agent_result, dict):
                return

            # Normalize decision and payload
            decision = None
            payload = None

            # OrkaResponse-style: result -> {decision: .., target: ..}
            if "result" in agent_result and isinstance(agent_result["result"], dict):
                payload = agent_result["result"]
                decision = payload.get("decision")
            else:
                # Legacy-style: decision at top level
                decision = agent_result.get("decision")
                payload = agent_result

            if not decision:
                return

            # Handle shortlist (validation) pattern
            if decision in ("shortlist", "shortlist_candidates"):
                shortlist = payload.get("target") or payload.get("shortlist") or []
                # shortlist expected as list of dicts
                if not shortlist:
                    return

                # If engine has a selector, use it to pick the best
                if hasattr(engine, "_select_best_candidate_from_shortlist"):
                    best = engine._select_best_candidate_from_shortlist(shortlist, input_data.get("input", ""), engine.build_previous_outputs(logs))
                    node_id = best.get("node_id") if isinstance(best, dict) else None
                    if node_id:
                        self._insert_targets([node_id])
                else:
                    # Fallback: pick first candidate's node_id
                    first = shortlist[0]
                    node_id = first.get("node_id") if isinstance(first, dict) else None
                    if node_id:
                        self._insert_targets([node_id])
                return

            # Handle commit/route/commit_next/commit_path
            if decision in ("route", "commit_next", "commit_path"):
                targ = payload.get("target")
                if not targ:
                    return
                if isinstance(targ, str):
                    targets = [targ]
                elif isinstance(targ, list):
                    targets = targ
                else:
                    # could be a dict describing a path
                    targets = targ if isinstance(targ, list) else [targ]

                # Convert candidate dicts to node_ids if necessary
                normalized: List[str] = []
                for t in targets:
                    if isinstance(t, dict) and "node_id" in t:
                        normalized.append(t["node_id"])
                    elif isinstance(t, str):
                        normalized.append(t)

                if normalized:
                    self._insert_targets(normalized)

        except Exception as e:
            logger.error(f"GraphScoutHandler error processing GraphScout result for {agent_id}: {e}")

    def _insert_targets(self, targets: List[str]) -> None:
        """Prepend targets to engine.queue while avoiding immediate duplicates."""
        engine = self.engine
        new_queue: List[str] = []
        # Only insert targets that are known agents to avoid typos
        for t in targets:
            if t not in new_queue and t in getattr(engine, "agents", {}):
                new_queue.append(t)

        # Prepend new_queue to existing engine.queue
        engine.queue = new_queue + getattr(engine, "queue", [])
        logger.info(f"GraphScout inserted agents into queue: {new_queue}")
