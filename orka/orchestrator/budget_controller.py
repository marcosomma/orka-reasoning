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
        """Initialize budget controller with configurable limits."""
        self.config = config

        # Token budget
        try:
            self.cost_budget_tokens = int(
                getattr(config, "cost_budget_tokens", None) or 10000
            )
        except (TypeError, ValueError):
            self.cost_budget_tokens = 10000

        # Cost budget (configurable, default $1.00)
        try:
            max_cost_val = getattr(config, "max_cost_usd", None)
            self.max_cost_usd = float(max_cost_val) if max_cost_val is not None else 1.0
        except (TypeError, ValueError):
            self.max_cost_usd = 1.0

        # Latency budget
        try:
            self.latency_budget_ms = int(
                getattr(config, "latency_budget_ms", None) or 30000
            )
        except (TypeError, ValueError):
            self.latency_budget_ms = 30000

        # Track current usage
        self.current_usage = {"tokens": 0, "cost_usd": 0.0, "latency_ms": 0.0}

        logger.debug(
            f"BudgetController initialized with token_budget={self.cost_budget_tokens}, "
            f"cost_budget=${self.max_cost_usd:.2f}, latency_budget={self.latency_budget_ms}ms"
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
            orchestrator = context.get("orchestrator")

            # Get actual usage from orchestrator metrics if available
            if orchestrator and hasattr(orchestrator, "metrics"):
                metrics = orchestrator.metrics
                if hasattr(metrics, "get_usage"):
                    try:
                        actual_usage = metrics.get_usage()
                        self.current_usage.update(
                            {
                                "tokens": actual_usage.get(
                                    "total_tokens", self.current_usage["tokens"]
                                ),
                                "cost_usd": actual_usage.get(
                                    "total_cost", self.current_usage["cost_usd"]
                                ),
                                "latency_ms": actual_usage.get(
                                    "total_latency_ms", self.current_usage["latency_ms"]
                                ),
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Could not get metrics from orchestrator: {e}")

            # Get usage from memory if available
            if orchestrator and hasattr(orchestrator, "memory") and orchestrator.memory:
                memory = orchestrator.memory
                run_id = getattr(orchestrator, "run_id", None)
                if run_id and hasattr(memory, "get_run_metrics"):
                    try:
                        run_metrics = memory.get_run_metrics(run_id)
                        if run_metrics:
                            self.current_usage["tokens"] = max(
                                self.current_usage["tokens"],
                                run_metrics.get("tokens_used", 0),
                            )
                    except Exception as e:
                        logger.debug(f"Could not get metrics from memory: {e}")

            return {
                "tokens": self.cost_budget_tokens - self.current_usage["tokens"],
                "cost_usd": self.max_cost_usd - self.current_usage["cost_usd"],
                "latency_ms": self.latency_budget_ms - self.current_usage["latency_ms"],
            }

        except Exception as e:
            logger.error(f"Failed to get remaining budget: {e}")
            return {
                "tokens": self.cost_budget_tokens,
                "cost_usd": self.max_cost_usd,
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
            orchestrator = context.get("orchestrator")

            estimated_tokens = 0

            for node_id in path:
                node_tokens = 100  # Base estimate

                # Use actual node metadata if available
                if orchestrator and hasattr(orchestrator, "agents"):
                    agent = orchestrator.agents.get(node_id)
                    if agent:
                        # Check for token estimates in agent config
                        if hasattr(agent, "config") and agent.config:
                            config_tokens = agent.config.get("estimated_tokens")
                            if config_tokens:
                                node_tokens = int(config_tokens)

                        # Estimate based on prompt length
                        if hasattr(agent, "prompt") and agent.prompt:
                            prompt_len = len(str(agent.prompt))
                            # Rough estimate: 4 chars per token
                            node_tokens = max(node_tokens, prompt_len // 4)

                        # Check model type for multiplier
                        model = getattr(agent, "model", "")
                        if "gpt-4" in str(model).lower():
                            node_tokens = int(node_tokens * 1.5)  # GPT-4 tends to use more

                estimated_tokens += node_tokens

            # Add buffer for safety
            return int(estimated_tokens * 1.2)

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

            path = candidate.get("path", [candidate["node_id"]])
            orchestrator = context.get("orchestrator")

            estimated_latency = 0.0

            for node_id in path:
                node_latency = 1000.0  # Base 1 second

                # Use actual node metadata if available
                if orchestrator and hasattr(orchestrator, "agents"):
                    agent = orchestrator.agents.get(node_id)
                    if agent:
                        # Check for latency estimates in agent config
                        if hasattr(agent, "config") and isinstance(agent.config, dict):
                            config_latency = agent.config.get("estimated_latency_ms")
                            if config_latency is not None:
                                try:
                                    node_latency = float(config_latency)
                                except (TypeError, ValueError):
                                    pass

                        # Adjust based on agent type
                        agent_type = getattr(agent, "agent_type", "") or ""
                        if agent_type in ("local_llm", "ollama"):
                            node_latency *= 0.5  # Local models are faster
                        elif agent_type in ("openai-gpt-4", "gpt-4"):
                            node_latency *= 2.0  # GPT-4 is slower

                        # Check for timeout settings (must be numeric)
                        timeout = getattr(agent, "timeout", None)
                        if isinstance(timeout, (int, float)) and timeout > 0:
                            if node_latency > timeout * 1000:
                                node_latency = timeout * 1000 * 0.8  # Estimate 80% of timeout

                estimated_latency += node_latency

            return estimated_latency

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
                    "cost_usd": self.max_cost_usd,
                    "latency_ms": self.latency_budget_ms,
                },
                "utilization": {
                    "tokens": self.current_usage["tokens"] / self.cost_budget_tokens
                    if self.cost_budget_tokens > 0
                    else 0.0,
                    "cost": self.current_usage["cost_usd"] / self.max_cost_usd
                    if self.max_cost_usd > 0
                    else 0.0,
                    "latency": self.current_usage["latency_ms"] / self.latency_budget_ms
                    if self.latency_budget_ms > 0
                    else 0.0,
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
