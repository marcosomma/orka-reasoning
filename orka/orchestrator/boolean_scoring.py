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
Boolean/Deterministic Scoring System
====================================

Implements deterministic boolean criteria evaluation for path scoring.
Each criterion returns True/False, enabling auditable pass/fail decisions.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class BooleanCriteriaResult:
    """Result of boolean criteria evaluation."""

    path: List[str]
    criteria_results: Dict[str, Dict[str, bool]]
    passed_criteria: int
    total_criteria: int
    overall_pass: bool
    critical_failures: List[str]
    pass_percentage: float
    audit_trail: str
    reasoning: str = ""


class BooleanScoringEngine:
    """
    Deterministic boolean scoring engine.

    Evaluates paths using explicit pass/fail criteria instead of continuous scores.
    Provides full auditability and deterministic decisions.
    """

    def __init__(self, config: Any):
        """Initialize boolean scoring engine with configuration."""
        self.config = config

        # Thresholds for boolean decisions
        self.min_success_rate = getattr(config, "min_success_rate", 0.70)
        self.min_domain_overlap = getattr(config, "min_domain_overlap", 0.30)
        self.max_acceptable_cost = getattr(config, "max_acceptable_cost", 0.10)
        self.max_acceptable_latency = getattr(config, "max_acceptable_latency", 10000)  # ms
        self.optimal_path_length = getattr(config, "optimal_path_length", (2, 3))

        # Safety configuration
        self.risky_capabilities = getattr(
            config,
            "risky_capabilities",
            {"file_write", "code_execution", "external_api", "database_write"},
        )
        self.required_safety_markers = getattr(
            config, "required_safety_markers", {"sandboxed", "read_only", "validated"}
        )

        # Scoring mode configuration
        self.strict_mode = getattr(config, "strict_mode", False)
        self.require_critical = getattr(config, "require_critical", True)
        self.important_threshold = getattr(config, "important_threshold", 0.8)
        self.include_nice_to_have = getattr(config, "include_nice_to_have", True)

        logger.info(
            f"BooleanScoringEngine initialized: strict={self.strict_mode}, "
            f"require_critical={self.require_critical}, important_threshold={self.important_threshold}"
        )

    async def evaluate_candidate(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any]
    ) -> BooleanCriteriaResult:
        """
        Evaluate candidate using boolean criteria.

        Returns:
            BooleanCriteriaResult with pass/fail for each criterion
        """
        try:
            path = candidate.get("path", [candidate.get("node_id", "")])

            # Evaluate all criteria categories
            input_readiness = await self._check_input_readiness(candidate, context)
            safety = await self._check_safety(candidate, context)
            capability_match = await self._check_capabilities(candidate, question, context)
            efficiency = await self._check_efficiency(candidate, context)
            historical_performance = await self._check_history(candidate, context)

            criteria_results = {
                "input_readiness": input_readiness,
                "safety": safety,
                "capability_match": capability_match,
                "efficiency": efficiency,
                "historical_performance": historical_performance,
            }

            # Calculate overall pass/fail
            overall_pass, critical_failures = self._calculate_overall_pass(criteria_results)

            # Count passed criteria
            passed = sum(sum(cat.values()) for cat in criteria_results.values())
            total = sum(len(cat) for cat in criteria_results.values())
            pass_percentage = passed / total if total > 0 else 0.0

            # Generate audit trail
            audit_trail = self._generate_audit_trail(criteria_results, critical_failures)
            reasoning = self._generate_reasoning(criteria_results, overall_pass, critical_failures)

            result = BooleanCriteriaResult(
                path=path,
                criteria_results=criteria_results,
                passed_criteria=passed,
                total_criteria=total,
                overall_pass=overall_pass,
                critical_failures=critical_failures,
                pass_percentage=pass_percentage,
                audit_trail=audit_trail,
                reasoning=reasoning,
            )

            logger.info(
                f"Boolean evaluation for {' -> '.join(path)}: "
                f"{'PASS' if overall_pass else 'FAIL'} ({passed}/{total} criteria)"
            )

            return result

        except Exception as e:
            logger.error(f"Boolean evaluation failed for candidate: {e}")
            # Return a failing result with error information
            return self._create_error_result(candidate, str(e))

    async def _check_input_readiness(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Check if all required inputs are ready.

        Returns:
            Dict of boolean checks:
            - all_required_inputs_available
            - no_circular_dependencies
            - input_types_compatible
        """
        try:
            node_id = candidate["node_id"]
            path = candidate.get("path", [node_id])

            # Get agent from orchestrator
            orchestrator = context.get("orchestrator")
            if not orchestrator or not hasattr(orchestrator, "agents"):
                return {
                    "all_required_inputs_available": True,  # Unknown - assume ok
                    "no_circular_dependencies": True,
                    "input_types_compatible": True,
                }

            agent = orchestrator.agents.get(node_id)
            if not agent:
                return {
                    "all_required_inputs_available": True,
                    "no_circular_dependencies": True,
                    "input_types_compatible": True,
                }

            # Check 1: Required inputs available
            required_inputs = getattr(agent, "required_inputs", [])
            previous_outputs = context.get("previous_outputs", {})

            if not required_inputs:
                all_inputs_available = True  # No requirements
            else:
                available = set(previous_outputs.keys())
                required = set(required_inputs)
                all_inputs_available = required.issubset(available)

            # Check 2: No circular dependencies
            no_circular = node_id not in previous_outputs  # Agent not already executed

            # Check 3: Input types compatible (simplified - check if previous outputs are dict-like)
            input_types_ok = all(
                isinstance(previous_outputs.get(inp), (dict, str, list, type(None)))
                for inp in required_inputs
            )

            return {
                "all_required_inputs_available": all_inputs_available,
                "no_circular_dependencies": no_circular,
                "input_types_compatible": input_types_ok,
            }

        except Exception as e:
            logger.error(f"Input readiness check failed: {e}")
            return {
                "all_required_inputs_available": False,
                "no_circular_dependencies": False,
                "input_types_compatible": False,
            }

    async def _check_safety(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Check safety requirements.

        Returns:
            Dict of boolean checks:
            - no_risky_capabilities_without_sandbox
            - output_validation_present
            - rate_limits_configured
        """
        try:
            node_id = candidate["node_id"]

            orchestrator = context.get("orchestrator")
            if not orchestrator or not hasattr(orchestrator, "agents"):
                return {
                    "no_risky_capabilities_without_sandbox": True,
                    "output_validation_present": True,
                    "rate_limits_configured": True,
                }

            agent = orchestrator.agents.get(node_id)
            if not agent:
                return {
                    "no_risky_capabilities_without_sandbox": True,
                    "output_validation_present": True,
                    "rate_limits_configured": True,
                }

            # Get agent capabilities and safety tags
            capabilities = set(getattr(agent, "capabilities", []))
            safety_tags = set(getattr(agent, "safety_tags", []))

            # Check 1: Risky capabilities have safety markers
            risky_caps = capabilities.intersection(self.risky_capabilities)
            if risky_caps:
                has_safety = bool(safety_tags.intersection(self.required_safety_markers))
            else:
                has_safety = True  # No risky capabilities, so safe

            # Check 2: Output validation present (check for validation config)
            has_validation = hasattr(agent, "output_validation") or "validated" in safety_tags

            # Check 3: Rate limits configured (check for rate limit settings)
            has_rate_limits = hasattr(agent, "rate_limit") or hasattr(
                agent, "max_requests_per_minute"
            )

            return {
                "no_risky_capabilities_without_sandbox": has_safety,
                "output_validation_present": has_validation
                or not risky_caps,  # Only required for risky
                "rate_limits_configured": has_rate_limits or "external_api" not in capabilities,
            }

        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return {
                "no_risky_capabilities_without_sandbox": False,
                "output_validation_present": False,
                "rate_limits_configured": False,
            }

    async def _check_capabilities(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Check if agent capabilities match the question.

        Returns:
            Dict of boolean checks:
            - capabilities_cover_question_type
            - modality_match
            - domain_overlap_sufficient
        """
        try:
            node_id = candidate["node_id"]

            orchestrator = context.get("orchestrator")
            if not orchestrator or not hasattr(orchestrator, "agents"):
                return {
                    "capabilities_cover_question_type": True,
                    "modality_match": True,
                    "domain_overlap_sufficient": True,
                }

            agent = orchestrator.agents.get(node_id)
            if not agent:
                return {
                    "capabilities_cover_question_type": True,
                    "modality_match": True,
                    "domain_overlap_sufficient": True,
                }

            capabilities = set(getattr(agent, "capabilities", []))

            # Check 1: Capabilities cover question type
            question_lower = question.lower()
            covers_question = False

            # Question type detection
            if any(word in question_lower for word in ["search", "find", "news", "latest"]):
                covers_question = bool(
                    {"web_search", "information_retrieval"}.intersection(capabilities)
                )
            elif any(word in question_lower for word in ["analyze", "evaluate", "explain"]):
                covers_question = bool(
                    {"analysis", "reasoning", "text_generation"}.intersection(capabilities)
                )
            elif any(word in question_lower for word in ["remember", "recall", "history"]):
                covers_question = bool({"memory_retrieval"}.intersection(capabilities))
            else:
                # General questions - LLM agents can handle
                covers_question = bool(
                    {"text_generation", "response_generation"}.intersection(capabilities)
                )

            # Check 2: Modality match
            has_image = any(
                word in question_lower for word in ["image", "picture", "visual", "photo"]
            )
            has_audio = any(word in question_lower for word in ["audio", "sound", "voice", "music"])

            if has_image:
                modality_ok = bool({"vision", "image_processing"}.intersection(capabilities))
            elif has_audio:
                modality_ok = bool({"audio_processing"}.intersection(capabilities))
            else:
                modality_ok = True  # Text is default

            # Check 3: Domain overlap (keyword matching for now)
            node_id_words = set(node_id.lower().replace("_", " ").split())
            question_words = set(question_lower.replace("?", "").split())

            overlap = len(node_id_words.intersection(question_words))
            domain_overlap_ok = (
                overlap >= 1 or len(question_words) < 3
            )  # Low bar for short questions

            return {
                "capabilities_cover_question_type": covers_question,
                "modality_match": modality_ok,
                "domain_overlap_sufficient": domain_overlap_ok,
            }

        except Exception as e:
            logger.error(f"Capability check failed: {e}")
            return {
                "capabilities_cover_question_type": False,
                "modality_match": False,
                "domain_overlap_sufficient": False,
            }

    async def _check_efficiency(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Check efficiency requirements.

        Returns:
            Dict of boolean checks:
            - path_length_optimal
            - cost_within_budget
            - latency_acceptable
        """
        try:
            path = candidate.get("path", [candidate.get("node_id", "")])
            estimated_cost = candidate.get("estimated_cost", 0.001)
            estimated_latency = candidate.get("estimated_latency", 1000)

            # Check 1: Path length in optimal range
            min_optimal, max_optimal = self.optimal_path_length
            length_ok = min_optimal <= len(path) <= max_optimal

            # Check 2: Cost within budget
            cost_ok = estimated_cost <= self.max_acceptable_cost

            # Check 3: Latency acceptable
            latency_ok = estimated_latency <= self.max_acceptable_latency

            return {
                "path_length_optimal": length_ok,
                "cost_within_budget": cost_ok,
                "latency_acceptable": latency_ok,
            }

        except Exception as e:
            logger.error(f"Efficiency check failed: {e}")
            return {
                "path_length_optimal": False,
                "cost_within_budget": False,
                "latency_acceptable": False,
            }

    async def _check_history(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Check historical performance.

        Returns:
            Dict of boolean checks:
            - success_rate_above_threshold
            - no_recent_failures
        """
        try:
            node_id = candidate["node_id"]

            orchestrator = context.get("orchestrator")
            if not orchestrator or not hasattr(orchestrator, "memory_manager"):
                # No history available - assume OK
                return {
                    "success_rate_above_threshold": True,
                    "no_recent_failures": True,
                }

            # Try to get historical data
            try:
                memory_manager = orchestrator.memory_manager
                success_rate_key = f"agent_success_rate:{node_id}"
                failure_key = f"agent_recent_failures:{node_id}"

                # Check 1: Success rate above threshold
                if hasattr(memory_manager, "get_metric"):
                    success_rate = memory_manager.get_metric(success_rate_key)
                    if success_rate is not None:
                        success_ok = float(success_rate) >= self.min_success_rate
                    else:
                        success_ok = True  # No history - neutral
                else:
                    success_ok = True

                # Check 2: No recent failures
                if hasattr(memory_manager, "get_metric"):
                    recent_failures = memory_manager.get_metric(failure_key)
                    if recent_failures is not None:
                        no_failures = int(recent_failures) == 0
                    else:
                        no_failures = True  # No history - neutral
                else:
                    no_failures = True

                return {
                    "success_rate_above_threshold": success_ok,
                    "no_recent_failures": no_failures,
                }

            except Exception as e:
                logger.debug(f"Could not retrieve historical data for {node_id}: {e}")
                return {
                    "success_rate_above_threshold": True,
                    "no_recent_failures": True,
                }

        except Exception as e:
            logger.error(f"History check failed: {e}")
            return {
                "success_rate_above_threshold": False,
                "no_recent_failures": False,
            }

    def _calculate_overall_pass(
        self, criteria_results: Dict[str, Dict[str, bool]]
    ) -> tuple[bool, List[str]]:
        """
        Calculate overall pass/fail based on criteria results.

        Returns:
            (overall_pass, critical_failures)
        """
        critical_failures = []

        # CRITICAL: Input readiness (all must pass)
        if self.require_critical:
            input_results = criteria_results["input_readiness"]
            for criterion, passed in input_results.items():
                if not passed:
                    critical_failures.append(f"input_readiness.{criterion}")

        # CRITICAL: Safety (all must pass)
        if self.require_critical:
            safety_results = criteria_results["safety"]
            for criterion, passed in safety_results.items():
                if not passed:
                    critical_failures.append(f"safety.{criterion}")

        # If any critical failures, overall fails
        if critical_failures:
            return False, critical_failures

        # IMPORTANT: Capability match (threshold-based)
        capability_results = criteria_results["capability_match"]
        capability_passed = sum(capability_results.values())
        capability_total = len(capability_results)
        capability_percentage = (
            capability_passed / capability_total if capability_total > 0 else 0.0
        )

        if capability_percentage < self.important_threshold:
            critical_failures.append(
                f"capability_match.threshold ({capability_percentage:.2f} < {self.important_threshold})"
            )
            return False, critical_failures

        # NICE-TO-HAVE: Efficiency and history (optional in non-strict mode)
        if self.strict_mode and self.include_nice_to_have:
            efficiency_results = criteria_results["efficiency"]
            if not all(efficiency_results.values()):
                # In strict mode, efficiency matters
                for criterion, passed in efficiency_results.items():
                    if not passed:
                        critical_failures.append(f"efficiency.{criterion}")
                return False, critical_failures

        # All checks passed
        return True, []

    def _generate_audit_trail(
        self, criteria_results: Dict[str, Dict[str, bool]], critical_failures: List[str]
    ) -> str:
        """Generate human-readable audit trail."""
        lines = ["Boolean Criteria Evaluation:", ""]

        for category, results in criteria_results.items():
            lines.append(f"{category.upper()}:")
            for criterion, passed in results.items():
                status = "Y PASS" if passed else "N FAIL"
                lines.append(f"  {criterion}: {status}")
            lines.append("")

        if critical_failures:
            lines.append("CRITICAL FAILURES:")
            for failure in critical_failures:
                lines.append(f"  - {failure}")

        return "\n".join(lines)

    def _generate_reasoning(
        self,
        criteria_results: Dict[str, Dict[str, bool]],
        overall_pass: bool,
        critical_failures: List[str],
    ) -> str:
        """Generate human-readable reasoning for the decision."""
        if overall_pass:
            return (
                "All critical and important criteria passed. Path is valid and safe for execution."
            )

        # Failure reasoning
        reasons = []

        if any("input_readiness" in f for f in critical_failures):
            reasons.append("Required inputs are not available")

        if any("safety" in f for f in critical_failures):
            reasons.append("Safety requirements not met (risky capabilities without safeguards)")

        if any("capability_match" in f for f in critical_failures):
            reasons.append("Agent capabilities do not sufficiently match the question type")

        if any("efficiency" in f for f in critical_failures):
            reasons.append("Efficiency requirements not met (path too long, cost/latency too high)")

        return "Path rejected: " + "; ".join(reasons)

    def _create_error_result(self, candidate: Dict[str, Any], error: str) -> BooleanCriteriaResult:
        """Create a failing result when evaluation errors out."""
        path = candidate.get("path", [candidate.get("node_id", "unknown")])

        return BooleanCriteriaResult(
            path=path,
            criteria_results={},
            passed_criteria=0,
            total_criteria=0,
            overall_pass=False,
            critical_failures=[f"evaluation_error: {error}"],
            pass_percentage=0.0,
            audit_trail=f"Evaluation failed with error: {error}",
            reasoning=f"Evaluation failed: {error}",
        )
