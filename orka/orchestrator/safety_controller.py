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
Safety Controller
================

Comprehensive safety assessment and risk management for path selection.
Implements safety policies, risk scoring, and guardrail enforcement.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SafetyPolicy:
    """Defines safety policies and risk assessment rules."""

    def __init__(self, profile: str = "default"):
        """Initialize safety policy with profile."""
        self.profile = profile
        self.risk_patterns = self._load_risk_patterns()
        self.forbidden_capabilities = self._load_forbidden_capabilities()
        self.content_filters = self._load_content_filters()

    def _load_risk_patterns(self) -> Dict[str, List[str]]:
        """Load risk detection patterns."""
        return {
            "pii": [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
                r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            ],
            "medical": [
                r"\b(diagnosis|prescription|medical record|patient)\b",
                r"\b(medication|treatment|therapy|surgery)\b",
            ],
            "legal": [
                r"\b(legal advice|lawsuit|litigation|attorney)\b",
                r"\b(contract|agreement|liability|damages)\b",
            ],
            "financial": [
                r"\b(investment advice|trading|stocks|portfolio)\b",
                r"\b(loan|mortgage|credit|debt)\b",
            ],
        }

    def _load_forbidden_capabilities(self) -> Set[str]:
        """Load forbidden capabilities based on profile."""
        if self.profile == "strict":
            return {
                "external_api_calls",
                "file_system_access",
                "database_writes",
                "email_sending",
                "code_execution",
            }
        elif self.profile == "moderate":
            return {"file_system_access", "database_writes", "code_execution"}
        else:  # default
            return {"code_execution"}

    def _load_content_filters(self) -> Dict[str, List[str]]:
        """Load content filtering rules."""
        return {
            "harmful": [r"\b(violence|harm|attack|threat)\b", r"\b(illegal|criminal|fraud|scam)\b"],
            "inappropriate": [r"\b(explicit|adult|nsfw)\b", r"\b(hate|discrimination|bias)\b"],
        }


class SafetyController:
    """
    Comprehensive safety assessment and control system.

    Evaluates candidate paths for safety risks including:
    - Content safety (PII, harmful content)
    - Capability restrictions
    - Policy compliance
    - Risk scoring and thresholds
    """

    def __init__(self, config: Any):
        """Initialize safety controller with configuration."""
        self.config = config
        self.safety_threshold = config.safety_threshold
        self.policy = SafetyPolicy(config.safety_profile)

        logger.debug(f"SafetyController initialized with profile: {config.safety_profile}")

    async def assess_candidates(
        self, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Assess all candidates for safety compliance.

        Args:
            candidates: List of candidates with previews
            context: Execution context

        Returns:
            List of candidates that pass safety assessment
        """
        try:
            safe_candidates = []

            for candidate in candidates:
                safety_assessment = await self._assess_candidate_safety(candidate, context)

                # Add safety information to candidate
                candidate["safety_score"] = safety_assessment["score"]
                candidate["safety_risks"] = safety_assessment["risks"]
                candidate["safety_details"] = safety_assessment["details"]

                # Filter based on safety threshold
                if safety_assessment["score"] >= (1.0 - self.safety_threshold):
                    safe_candidates.append(candidate)
                else:
                    logger.warning(
                        f"Candidate {candidate['node_id']} failed safety check: "
                        f"score={safety_assessment['score']:.3f}, "
                        f"risks={safety_assessment['risks']}"
                    )

            logger.info(
                f"Safety assessment: {len(safe_candidates)}/{len(candidates)} " f"candidates passed"
            )

            return safe_candidates

        except Exception as e:
            logger.error(f"Safety assessment failed: {e}")
            return candidates  # Default to allowing all if assessment fails

    async def _assess_candidate_safety(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess safety for a single candidate."""
        try:
            risks = []
            risk_scores = []
            details = {}

            # Content safety assessment
            content_risks = await self._assess_content_safety(candidate, context)
            risks.extend(content_risks["risks"])
            risk_scores.append(content_risks["score"])
            details["content"] = content_risks["details"]

            # Capability safety assessment
            capability_risks = await self._assess_capability_safety(candidate, context)
            risks.extend(capability_risks["risks"])
            risk_scores.append(capability_risks["score"])
            details["capabilities"] = capability_risks["details"]

            # Policy compliance assessment
            policy_risks = await self._assess_policy_compliance(candidate, context)
            risks.extend(policy_risks["risks"])
            risk_scores.append(policy_risks["score"])
            details["policy"] = policy_risks["details"]

            # Calculate overall safety score (average of component scores)
            overall_score = sum(risk_scores) / len(risk_scores) if risk_scores else 1.0

            return {
                "score": overall_score,
                "risks": list(set(risks)),  # Remove duplicates
                "details": details,
            }

        except Exception as e:
            logger.error(f"Individual safety assessment failed: {e}")
            return {
                "score": 0.0,  # Fail safe - assume unsafe if assessment fails
                "risks": ["assessment_error"],
                "details": {"error": str(e)},
            }

    async def _assess_content_safety(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess content safety risks."""
        try:
            risks = []
            details = {}

            # Get content to analyze
            preview = candidate.get("preview", "")
            question = context.get("input", "")
            content_to_check = f"{question} {preview}"

            # Check for PII patterns
            pii_risks = self._check_patterns(
                content_to_check, self.policy.risk_patterns.get("pii", [])
            )
            if pii_risks:
                risks.append("pii_detected")
                details["pii_matches"] = pii_risks

            # Check for medical content
            medical_risks = self._check_patterns(
                content_to_check, self.policy.risk_patterns.get("medical", [])
            )
            if medical_risks:
                risks.append("medical_content")
                details["medical_matches"] = medical_risks

            # Check for legal content
            legal_risks = self._check_patterns(
                content_to_check, self.policy.risk_patterns.get("legal", [])
            )
            if legal_risks:
                risks.append("legal_content")
                details["legal_matches"] = legal_risks

            # Check for harmful content
            harmful_risks = self._check_patterns(
                content_to_check, self.policy.content_filters.get("harmful", [])
            )
            if harmful_risks:
                risks.append("harmful_content")
                details["harmful_matches"] = harmful_risks

            # Calculate content safety score
            if not risks:
                score = 1.0  # Perfect safety
            elif len(risks) == 1 and risks[0] in ["medical_content", "legal_content"]:
                score = 0.7  # Moderate risk for domain-specific content
            else:
                score = 0.3  # High risk for PII or harmful content

            return {"score": score, "risks": risks, "details": details}

        except Exception as e:
            logger.error(f"Content safety assessment failed: {e}")
            return {"score": 0.5, "risks": [], "details": {}}

    async def _assess_capability_safety(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess capability-based safety risks."""
        try:
            risks = []
            details = {}

            node_id = candidate["node_id"]

            # Check for forbidden capabilities
            forbidden_found = []
            for forbidden_cap in self.policy.forbidden_capabilities:
                if self._node_has_capability(node_id, forbidden_cap):
                    forbidden_found.append(forbidden_cap)
                    risks.append(f"forbidden_capability_{forbidden_cap}")

            details["forbidden_capabilities"] = forbidden_found

            # Calculate capability safety score
            if not forbidden_found:
                score = 1.0
            elif len(forbidden_found) == 1 and forbidden_found[0] in ["external_api_calls"]:
                score = 0.8  # Moderate risk for API calls
            else:
                score = 0.2  # High risk for multiple forbidden capabilities

            return {"score": score, "risks": risks, "details": details}

        except Exception as e:
            logger.error(f"Capability safety assessment failed: {e}")
            return {"score": 0.5, "risks": [], "details": {}}

    async def _assess_policy_compliance(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess policy compliance."""
        try:
            risks = []
            details = {}

            # Check for policy violations
            # This is a placeholder for more sophisticated policy checking

            # Example: Check if path violates maximum depth policy
            path_length = len(candidate.get("path", []))
            if path_length > 5:  # Arbitrary limit
                risks.append("path_too_long")
                details["path_length"] = path_length

            # Calculate policy compliance score
            score = 1.0 if not risks else 0.6

            return {"score": score, "risks": risks, "details": details}

        except Exception as e:
            logger.error(f"Policy compliance assessment failed: {e}")
            return {"score": 0.5, "risks": [], "details": {}}

    def _check_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Check text against risk patterns."""
        matches = []

        try:
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches.append(pattern)

            return matches

        except Exception as e:
            logger.error(f"Pattern checking failed: {e}")
            return []

    def _node_has_capability(self, node_id: str, capability: str) -> bool:
        """Check if node has a specific capability."""
        try:
            orchestrator = getattr(self.config, "orchestrator", None)
            if not orchestrator or not hasattr(orchestrator, "agents"):
                return False
            
            agent = orchestrator.agents.get(node_id)
            if not agent:
                return False
            
            agent_capabilities = getattr(agent, "capabilities", [])
            return capability in agent_capabilities

        except Exception as e:
            logger.error(f"Capability checking failed: {e}")
            return False
