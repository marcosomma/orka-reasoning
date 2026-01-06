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
Budget Controller
================

Budget management and constraint enforcement for path selection.
Monitors and controls resource usage including tokens, cost, and latency.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BudgetController:
    """
    Resource budget management and enforcement.

    Manages and enforces constraints on:
    - Token usage
    - Cost limits (USD)
    - Latency budgets (milliseconds)
    - Memory usage
    """

    def __init__(self, config: Any):
        """Initialize budget controller with configuration."""
        self.config = config
        self.cost_budget_tokens = config.cost_budget_tokens
        self.latency_budget_ms = config.latency_budget_ms

        # Track current usage
        self.current_usage = {"tokens": 0, "cost_usd": 0.0, "latency_ms": 0.0}

        logger.debug(
            f"BudgetController initialized with token_budget={self.cost_budget_tokens}, "
            f"latency_budget={self.latency_budget_ms}ms"
        )

    async def filter_candidates(
        self, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter candidates based on budget constraints.

        Args:
            candidates: List of candidate paths
            context: Execution context

        Returns:
            List of candidates that fit within budget
        """
        try:
            # Get current budget state
            remaining_budget = await self._get_remaining_budget(context)

            budget_compliant = []

            for candidate in candidates:
                budget_assessment = await self._assess_candidate_budget(
                    candidate, remaining_budget, context
                )

                # Add budget information to candidate
                candidate["budget_assessment"] = budget_assessment
                candidate["fits_budget"] = budget_assessment["compliant"]

                if budget_assessment["compliant"]:
                    budget_compliant.append(candidate)
                else:
                    logger.debug(
                        f"Candidate {candidate['node_id']} exceeds budget: "
                        f"{budget_assessment['violations']}"
                    )

            logger.info(
                f"Budget filtering: {len(budget_compliant)}/{len(candidates)} "
                f"candidates within budget"
            )

            return budget_compliant

        except Exception as e:
            logger.error(f"Budget filtering failed: {e}")
            return candidates  # Default to allowing all if filtering fails

    async def _get_remaining_budget(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get remaining budget for this execution."""
        try:
            # TODO: Get actual usage from orchestrator/memory
            # For now, use configured limits as remaining budget

            return {
                "tokens": self.cost_budget_tokens - self.current_usage["tokens"],
                "cost_usd": 1.0 - self.current_usage["cost_usd"],  # Default $1 limit
                "latency_ms": self.latency_budget_ms - self.current_usage["latency_ms"],
            }

        except Exception as e:
            logger.error(f"Failed to get remaining budget: {e}")
            return {
                "tokens": self.cost_budget_tokens,
                "cost_usd": 1.0,
                "latency_ms": self.latency_budget_ms,
            }

    async def _assess_candidate_budget(
        self, candidate: Dict[str, Any], remaining_budget: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess if candidate fits within budget constraints."""
        try:
            violations = []
            estimates = {}

            # Estimate resource requirements
            token_estimate = await self._estimate_tokens(candidate, context)
            cost_estimate = await self._estimate_cost(candidate, context)
            latency_estimate = await self._estimate_latency(candidate, context)

            estimates = {
                "tokens": token_estimate,
                "cost_usd": cost_estimate,
                "latency_ms": latency_estimate,
            }

            # Check against remaining budget
            if token_estimate > remaining_budget["tokens"]:
                violations.append(f"tokens: {token_estimate} > {remaining_budget['tokens']}")

            if cost_estimate > remaining_budget["cost_usd"]:
                violations.append(
                    f"cost: ${cost_estimate:.4f} > ${remaining_budget['cost_usd']:.4f}"
                )

            if latency_estimate > remaining_budget["latency_ms"]:
                violations.append(
                    f"latency: {latency_estimate}ms > {remaining_budget['latency_ms']}ms"
                )

            return {
                "compliant": len(violations) == 0,
                "violations": violations,
                "estimates": estimates,
                "remaining_budget": remaining_budget,
            }

        except Exception as e:
            logger.error(f"Budget assessment failed: {e}")
            return {
                "compliant": True,  # Default to allowing if assessment fails
                "violations": [],
                "estimates": {},
                "error": str(e),
            }

    async def _estimate_tokens(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> int:
        """Estimate token usage for candidate path."""
        try:
            path = candidate.get("path", [candidate["node_id"]])
            base_tokens_per_node = 100  # Conservative estimate

            # Simple estimation based on path length
            estimated_tokens = len(path) * base_tokens_per_node

            # Adjust based on node types (if available)
            # TODO: Use actual node metadata for better estimates

            # Add buffer for safety
            estimated_tokens = int(estimated_tokens * 1.2)

            return estimated_tokens

        except Exception as e:
            logger.error(f"Token estimation failed: {e}")
            return 200  # Conservative fallback

    async def _estimate_cost(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Estimate cost for candidate path."""
        try:
            # Use pre-calculated estimate if available
            if "estimated_cost" in candidate:
                return float(candidate["estimated_cost"])

            # Fallback estimation
            token_estimate = await self._estimate_tokens(candidate, context)

            # Rough cost estimation (varies by model)
            cost_per_1k_tokens = 0.002  # Approximate for GPT-3.5
            estimated_cost = (token_estimate / 1000.0) * cost_per_1k_tokens

            return float(estimated_cost)

        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return 0.01

    async def _estimate_latency(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Estimate latency for candidate path."""
        try:
            # Use pre-calculated estimate if available
            if "estimated_latency" in candidate:
                return float(candidate["estimated_latency"])

            # Fallback estimation
            path = candidate.get("path", [candidate["node_id"]])
            base_latency_per_node = 1000  # 1 second per node

            estimated_latency = len(path) * base_latency_per_node

            # Adjust for node types
            # TODO: Use actual node metadata for better estimates

            return float(estimated_latency)

        except Exception as e:
            logger.error(f"Latency estimation failed: {e}")
            return 2000.0

    async def update_usage(self, tokens_used: int, cost_incurred: float, latency_ms: float) -> None:
        """Update current resource usage."""
        try:
            self.current_usage["tokens"] += tokens_used
            self.current_usage["cost_usd"] += cost_incurred
            self.current_usage["latency_ms"] += latency_ms

            logger.debug(
                f"Budget usage updated: tokens={self.current_usage['tokens']}, "
                f"cost=${self.current_usage['cost_usd']:.4f}, "
                f"latency={self.current_usage['latency_ms']}ms"
            )

        except Exception as e:
            logger.error(f"Failed to update usage: {e}")

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary."""
        try:
            return {
                "current_usage": self.current_usage.copy(),
                "budget_limits": {
                    "tokens": self.cost_budget_tokens,
                    "cost_usd": 1.0,  # TODO: Make configurable
                    "latency_ms": self.latency_budget_ms,
                },
                "utilization": {
                    "tokens": self.current_usage["tokens"] / self.cost_budget_tokens,
                    "cost": self.current_usage["cost_usd"] / 1.0,
                    "latency": self.current_usage["latency_ms"] / self.latency_budget_ms,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {"error": str(e)}

    def is_budget_exhausted(self, threshold: float = 0.9) -> bool:
        """Check if budget is nearly exhausted."""
        try:
            usage_summary = self.get_usage_summary()
            utilization = usage_summary.get("utilization", {})

            # Check if any resource is above threshold
            for resource, util in utilization.items():
                if util > threshold:
                    logger.warning(f"Budget nearly exhausted for {resource}: {util:.1%}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Budget exhaustion check failed: {e}")
            return False
