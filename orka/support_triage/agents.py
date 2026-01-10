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
Support Triage Agents
=====================

Specialized agents for the ticket triage workflow. These agents implement
the core processing logic with trust boundary enforcement.

Agents:
- EnvelopeValidatorAgent: Validates input envelope schema and constraints
- RedactionAgent: Redacts PII from untrusted content before LLM processing
- TrustBoundaryAgent: Enforces trust boundaries and detects prompt injection
- PermissionGateAgent: Validates tool calls against policy permissions
- OutputVerificationAgent: Validates output schema and citations
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..agents.base_agent import BaseAgent
from .schemas import (
    ActionType,
    Classification,
    Decision,
    DecisionReason,
    DecisionRisks,
    InputEnvelope,
    OutputEnvelope,
    RiskLevel,
    TrustLevel,
)
from .validators import (
    CitationValidator,
    EnvelopeValidator,
    OutputValidator,
    PermissionChecker,
    TrustBoundaryEnforcer,
)

if TYPE_CHECKING:
    from ..contracts import Context

logger = logging.getLogger(__name__)


def _get_agent_response(previous_outputs: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    """
    Helper to extract agent response from previous_outputs.

    OrKa wraps agent outputs in a structure like:
    {"response": {...actual_output...}, "confidence": ..., "_metrics": ...}

    This helper handles both wrapped and unwrapped formats for backward compatibility.
    """
    if agent_id not in previous_outputs:
        return {}

    output = previous_outputs[agent_id]
    if not isinstance(output, dict):
        return {}

    # Check if this is a wrapped response (has "response" key)
    if "response" in output:
        response = output["response"]
        if isinstance(response, dict):
            return response
        return {}

    # Direct (unwrapped) format
    return output


class EnvelopeValidatorAgent(BaseAgent):
    """
    Validates input envelope schema and constraints.

    This is a deterministic agent (not LLM) that performs schema validation,
    size checks, and freshness validation on input envelopes.

    Usage in YAML:
    ```yaml
    - id: validate_input
      type: envelope_validator
      params:
        strict: true
        max_message_length: 50000
        context_freshness_hours: 24
    ```
    """

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        # Extract config from params
        config_params = self.params.get("params", self.params)
        self.strict = config_params.get("strict", True)

        # Create validator with config
        self.validator = EnvelopeValidator(strict=self.strict)

        # Override defaults if provided
        if "max_message_length" in config_params:
            self.validator.MAX_MESSAGE_LENGTH = config_params["max_message_length"]
        if "context_freshness_hours" in config_params:
            self.validator.CONTEXT_FRESHNESS_HOURS = config_params["context_freshness_hours"]

        logger.info(f"Initialized EnvelopeValidatorAgent '{agent_id}'")

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """Validate the envelope from context."""
        input_data = ctx.get("input", "")

        # Try to parse envelope from input
        try:
            if isinstance(input_data, str):
                envelope_data = json.loads(input_data)
            else:
                envelope_data = input_data

            envelope = InputEnvelope.model_validate(envelope_data)
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": f"Invalid JSON: {str(e)}",
                "violations": [{"field": "input", "message": str(e), "severity": "error"}],
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Schema validation failed: {str(e)}",
                "violations": [{"field": "envelope", "message": str(e), "severity": "error"}],
            }

        # Validate
        try:
            is_valid, violations = self.validator.validate(envelope)
            return {
                "valid": is_valid,
                "violations": violations,
                "envelope": envelope.model_dump(mode="json"),
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "violations": getattr(e, "violations", []),
            }


class RedactionAgent(BaseAgent):
    """
    Redacts PII from untrusted content before LLM processing.

    This is a deterministic agent that applies regex-based PII redaction
    to customer messages and attachments.

    Usage in YAML:
    ```yaml
    - id: redact_pii
      type: redaction
      params:
        redaction_level: strict  # strict, moderate, minimal
        custom_patterns: []
    ```
    """

    # PII patterns with replacement tokens
    PII_PATTERNS = {
        "email": (
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL_REDACTED]",
        ),
        "phone": (
            r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",
            "[PHONE_REDACTED]",
        ),
        "ssn": (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[SSN_REDACTED]"),
        "credit_card": (
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "[CARD_REDACTED]",
        ),
        "ip_address": (
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "[IP_REDACTED]",
        ),
        "date_of_birth": (
            r"\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b",
            "[DOB_REDACTED]",
        ),
    }

    # Additional patterns for strict mode
    STRICT_PATTERNS = {
        "address": (
            r"\b\d{1,5}\s+\w+\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court)\b",
            "[ADDRESS_REDACTED]",
        ),
        "name_pattern": (
            r"\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",
            "[NAME_REDACTED]",
        ),
    }

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        config_params = self.params.get("params", self.params)
        self.redaction_level = config_params.get("redaction_level", "strict")
        custom_patterns = config_params.get("custom_patterns", [])

        # Build pattern list based on level
        self.patterns = {}
        self.patterns.update(self.PII_PATTERNS)

        if self.redaction_level in ("strict", "moderate"):
            self.patterns.update(self.STRICT_PATTERNS)

        # Add custom patterns
        for i, pattern in enumerate(custom_patterns):
            self.patterns[f"custom_{i}"] = (pattern, f"[CUSTOM_{i}_REDACTED]")

        # Compile patterns
        self.compiled_patterns = {
            name: (re.compile(pattern, re.IGNORECASE), replacement)
            for name, (pattern, replacement) in self.patterns.items()
        }

        logger.info(
            f"Initialized RedactionAgent '{agent_id}' with level '{self.redaction_level}'"
        )

    def redact_text(self, text: str) -> Dict[str, Any]:
        """
        Redact PII from text.

        Args:
            text: Text to redact

        Returns:
            Dict with redacted text and redaction metadata
        """
        redacted = text
        redactions = []

        for name, (pattern, replacement) in self.compiled_patterns.items():
            matches = pattern.findall(redacted)
            if matches:
                redactions.append(
                    {
                        "type": name,
                        "count": len(matches),
                    }
                )
                redacted = pattern.sub(replacement, redacted)

        return {
            "redacted_text": redacted,
            "redactions": redactions,
            "pii_detected": len(redactions) > 0,
        }

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """Redact PII from envelope content."""
        input_data = ctx.get("input", "")

        # Get envelope from previous output or parse from input
        previous_outputs = ctx.get("previous_outputs", {})

        # Use helper to get unwrapped response
        validate_result = _get_agent_response(previous_outputs, "validate_input")
        if validate_result and "envelope" in validate_result:
            envelope_data = validate_result["envelope"]
        else:
            try:
                if isinstance(input_data, str):
                    envelope_data = json.loads(input_data)
                else:
                    envelope_data = input_data
            except Exception:
                envelope_data = {}

        results = {
            "message_redaction": None,
            "thread_redactions": [],
            "total_pii_found": 0,
        }

        # Redact customer message
        if "case" in envelope_data and "customer_message" in envelope_data["case"]:
            msg = envelope_data["case"]["customer_message"]
            if "text" in msg:
                result = self.redact_text(msg["text"])
                results["message_redaction"] = result
                results["total_pii_found"] += len(result["redactions"])
                # Update envelope
                envelope_data["case"]["customer_message"]["text"] = result["redacted_text"]

        # Redact thread history
        if "case" in envelope_data and "thread_history" in envelope_data["case"]:
            for i, msg in enumerate(envelope_data["case"]["thread_history"]):
                if "text" in msg:
                    result = self.redact_text(msg["text"])
                    results["thread_redactions"].append(result)
                    results["total_pii_found"] += len(result["redactions"])
                    envelope_data["case"]["thread_history"][i]["text"] = result["redacted_text"]

        results["envelope"] = envelope_data
        return results


class TrustBoundaryAgent(BaseAgent):
    """
    Enforces trust boundaries and detects prompt injection.

    This is a deterministic agent that validates trust levels and
    scans untrusted content for injection attempts.

    Usage in YAML:
    ```yaml
    - id: check_trust
      type: trust_boundary
      params:
        custom_injection_patterns: []
        fail_on_injection: false  # If true, fails on injection detection
    ```
    """

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        config_params = self.params.get("params", self.params)
        custom_patterns = config_params.get("custom_injection_patterns", [])
        self.fail_on_injection = config_params.get("fail_on_injection", False)

        self.enforcer = TrustBoundaryEnforcer(custom_patterns=custom_patterns)

        logger.info(f"Initialized TrustBoundaryAgent '{agent_id}'")

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """Check trust boundaries in envelope."""
        input_data = ctx.get("input", "")
        previous_outputs = ctx.get("previous_outputs", {})

        # Get envelope from previous output using helper
        envelope_data = None
        for key in ["redact_pii", "validate_input"]:
            result = _get_agent_response(previous_outputs, key)
            if result and "envelope" in result:
                envelope_data = result["envelope"]
                break

        if not envelope_data:
            try:
                if isinstance(input_data, str):
                    envelope_data = json.loads(input_data)
                else:
                    envelope_data = input_data
            except Exception:
                return {
                    "valid": False,
                    "error": "Could not parse envelope",
                    "injection_detected": False,
                }

        try:
            envelope = InputEnvelope.model_validate(envelope_data)
        except Exception as e:
            return {
                "valid": False,
                "error": f"Invalid envelope: {str(e)}",
                "injection_detected": False,
            }

        # Validate trust boundaries
        is_valid, violations = self.enforcer.validate_envelope_trust(envelope)

        # Check for injection
        has_injection = any(
            v.get("message", "").startswith("Potential prompt injection")
            for v in violations
        )

        # Create sanitized content for downstream LLM processing
        sanitized_content = self.enforcer.sanitize_for_analysis(
            envelope.case.customer_message.text,
            TrustLevel.UNTRUSTED,
        )

        result = {
            "valid": is_valid,
            "violations": violations,
            "injection_detected": has_injection,
            "sanitized_content": sanitized_content,
            "envelope": envelope_data,
        }

        if has_injection and self.fail_on_injection:
            result["error"] = "Prompt injection detected in untrusted content"
            result["valid"] = False

        return result


class PermissionGateAgent(BaseAgent):
    """
    Validates tool calls against policy permissions.

    This is a deterministic agent that checks if proposed actions
    are allowed by the current policy.

    Usage in YAML:
    ```yaml
    - id: check_permissions
      type: permission_gate
      params:
        policy_id: support_policy_v3
    ```
    """

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        config_params = self.params.get("params", self.params)
        self.policy_id = config_params.get("policy_id", "default_policy_v1")

        logger.info(f"Initialized PermissionGateAgent '{agent_id}'")

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """Check permissions for proposed actions."""
        input_data = ctx.get("input", "")
        previous_outputs = ctx.get("previous_outputs", {})

        # Get envelope and permissions using helper
        envelope_data = None
        for key in ["check_trust", "redact_pii", "validate_input"]:
            result = _get_agent_response(previous_outputs, key)
            if result and "envelope" in result:
                envelope_data = result["envelope"]
                break

        if not envelope_data:
            return {
                "valid": False,
                "error": "No envelope found in context",
                "checked_actions": [],
            }

        # Get proposed actions from action_plan if available
        action_plan = []
        for key in ["synthesize", "draft_reply"]:
            result = _get_agent_response(previous_outputs, key)
            if result and "action_plan" in result:
                action_plan = result["action_plan"]
                break

        # Create permission checker
        try:
            envelope = InputEnvelope.model_validate(envelope_data)
            checker = PermissionChecker(
                permissions=envelope.permissions,
                policy_id=envelope.constraints.policy_id,
            )
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to create permission checker: {str(e)}",
                "checked_actions": [],
            }

        # Check each proposed action
        checked_actions = []
        all_allowed = True

        for action in action_plan:
            action_type = action.get("action", "")
            details = action.get("details", "")

            result, reason = checker.check_tool_call(action_type, {"details": details})

            checked_actions.append(
                {
                    "action": action_type,
                    "result": result,
                    "reason": reason,
                    "policy_id": self.policy_id,
                }
            )

            if result != "allowed":
                all_allowed = False

        return {
            "valid": all_allowed,
            "checked_actions": checked_actions,
            "policy_id": self.policy_id,
            "blocked_count": sum(1 for a in checked_actions if a["result"] != "allowed"),
        }


class OutputVerificationAgent(BaseAgent):
    """
    Validates output schema and citations.

    This is a deterministic agent that performs strict validation
    on the final output before human gate.

    Usage in YAML:
    ```yaml
    - id: verify_output
      type: output_verification
      params:
        require_citations: true
        strict_schema: true
    ```
    """

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        config_params = self.params.get("params", self.params)
        self.require_citations = config_params.get("require_citations", True)
        self.strict_schema = config_params.get("strict_schema", True)

        self.output_validator = OutputValidator()

        logger.info(f"Initialized OutputVerificationAgent '{agent_id}'")

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """Verify the output envelope."""
        previous_outputs = ctx.get("previous_outputs", {})

        # Get the draft output using helper (unwrapped from response)
        draft_output = None
        for key in ["draft_reply", "synthesize"]:
            result = _get_agent_response(previous_outputs, key)
            if result:
                draft_output = result
                break

        if not draft_output:
            return {
                "valid": False,
                "error": "No draft output found in context",
                "violations": [],
            }

        # Get request_id from envelope using helper
        request_id = ""
        for key in ["validate_input", "redact_pii", "check_trust"]:
            result = _get_agent_response(previous_outputs, key)
            if result and "envelope" in result:
                envelope = result["envelope"]
                request_id = envelope.get("request_id", "")
                break

        # Try to validate as OutputEnvelope
        try:
            if isinstance(draft_output, str):
                output_data = json.loads(draft_output)
            else:
                output_data = draft_output

            # Ensure request_id is set
            if "request_id" not in output_data:
                output_data["request_id"] = request_id

            output = OutputEnvelope.model_validate(output_data)
            is_valid, violations = self.output_validator.validate_output(output, request_id)

            # Check citations if required
            if self.require_citations and not output.citations:
                violations.append(
                    {
                        "field": "citations",
                        "message": "Citations are required but none provided",
                        "severity": "error",
                    }
                )
                is_valid = False

            return {
                "valid": is_valid,
                "violations": violations,
                "output": output.model_dump(mode="json"),
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Output validation failed: {str(e)}",
                "violations": [{"field": "output", "message": str(e), "severity": "error"}],
            }


class DecisionRecorderAgent(BaseAgent):
    """
    Records decisions with evidence and citations.

    This agent creates structured decision records for audit trail.

    Usage in YAML:
    ```yaml
    - id: record_decision
      type: decision_recorder
      params:
        decision_type: routing
    ```
    """

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        config_params = self.params.get("params", self.params)
        self.decision_type = config_params.get("decision_type", "routing")

        logger.info(f"Initialized DecisionRecorderAgent '{agent_id}'")

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """Record a decision from previous outputs."""
        previous_outputs = ctx.get("previous_outputs", {})

        # Get request_id using helper
        request_id = ""
        for key in ["validate_input", "redact_pii", "check_trust"]:
            result = _get_agent_response(previous_outputs, key)
            if result and "envelope" in result:
                envelope = result["envelope"]
                request_id = envelope.get("request_id", "")
                break

        # Get classification result using helper
        classification = None
        for key in ["classify_intent", "classification"]:
            result = _get_agent_response(previous_outputs, key)
            if result:
                classification = result
                break

        # Get risk assessment using helper
        risk_assessment = None
        for key in ["risk_assess", "risk_assessment"]:
            result = _get_agent_response(previous_outputs, key)
            if result:
                risk_assessment = result
                break

        # Get injection detection from trust check using helper
        injection_detected = False
        trust_result = _get_agent_response(previous_outputs, "check_trust")
        if trust_result:
            injection_detected = trust_result.get("injection_detected", False)

        # Build decision record
        decision = Decision(
            decision_id=f"d_{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            type=self.decision_type,
            chosen_path=self._determine_path(classification, risk_assessment),
            confidence=self._calculate_confidence(classification),
            reasons=self._build_reasons(classification, risk_assessment),
            risks=DecisionRisks(
                prompt_injection_detected=injection_detected,
                pii_risk=self._extract_risk_level(risk_assessment, "pii"),
                financial_risk=self._extract_risk_level(risk_assessment, "financial"),
            ),
            created_at=datetime.utcnow(),
        )

        return {
            "decision": decision.model_dump(mode="json"),
            "decision_id": decision.decision_id,
        }

    def _determine_path(
        self, classification: Optional[Dict], risk: Optional[Dict]
    ) -> str:
        """Determine the chosen path based on classification."""
        if classification:
            # Data is already unwrapped by _get_agent_response
            intent = classification.get("intent", "")
            if intent:
                return f"{intent}_flow"
        return "default_flow"

    def _calculate_confidence(self, classification: Optional[Dict]) -> float:
        """Calculate confidence score."""
        if classification:
            # Data is already unwrapped by _get_agent_response
            conf = classification.get("confidence")
            if conf is not None:
                return float(conf)
        return 0.5

    def _build_reasons(
        self, classification: Optional[Dict], risk: Optional[Dict]
    ) -> List[DecisionReason]:
        """Build decision reasons from classification and risk."""
        reasons = []

        if classification:
            # Data is already unwrapped by _get_agent_response
            intent = classification.get("intent", "")
            if intent:
                reasons.append(
                    DecisionReason(
                        claim=f"Detected intent: {intent}",
                        evidence_refs=["case.customer_message.text"],
                    )
                )

        if risk:
            # Data is already unwrapped by _get_agent_response
            overall = risk.get("overall_risk", risk.get("overall", ""))
            if overall:
                reasons.append(
                    DecisionReason(
                        claim=f"Risk level: {overall}",
                        evidence_refs=["context.entitlements", "constraints.policy_id"],
                    )
                )

        return reasons

    def _extract_risk_level(
        self, risk: Optional[Dict], risk_type: str
    ) -> RiskLevel:
        """Extract specific risk level from risk assessment."""
        if not risk:
            return RiskLevel.LOW

        risk_flags = risk.get("risk_flags", risk.get("risks", {}))
        if isinstance(risk_flags, dict):
            level = risk_flags.get(f"{risk_type}_risk", "low")
            try:
                return RiskLevel(level.lower())
            except ValueError:
                return RiskLevel.LOW

        return RiskLevel.LOW


class RiskLevelExtractorAgent(BaseAgent):
    """
    Extracts the overall risk level as a simple string for routing.

    This deterministic agent extracts the 'overall_risk' field from
    a risk assessment response and returns it as a simple string
    suitable for router decision matching.

    Usage in YAML:
    ```yaml
    - id: extract_risk_level
      type: risk_level_extractor
      params:
        source_agent: risk_assess
        field: overall_risk
    ```
    """

    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

        config_params = self.params.get("params", self.params)
        self.source_agent = config_params.get("source_agent", "risk_assess")
        self.field = config_params.get("field", "overall_risk")
        self.default_value = config_params.get("default", "medium")

        logger.info(f"Initialized RiskLevelExtractorAgent '{agent_id}'")

    async def _run_impl(self, ctx: "Context") -> str:
        """Extract risk level from source agent response."""
        previous_outputs = ctx.get("previous_outputs", {})

        # Get source agent response using helper
        source_result = _get_agent_response(previous_outputs, self.source_agent)

        if not source_result:
            logger.warning(
                f"RiskLevelExtractorAgent: No response from '{self.source_agent}', "
                f"using default '{self.default_value}'"
            )
            return self.default_value

        # Extract the specified field (support dot notation)
        value = source_result
        for field_part in self.field.split("."):
            if isinstance(value, dict) and field_part in value:
                value = value[field_part]
            else:
                logger.warning(
                    f"RiskLevelExtractorAgent: Field '{self.field}' not found in response, "
                    f"using default '{self.default_value}'"
                )
                return self.default_value

        # Return as string for router matching
        result = str(value).strip().lower()
        logger.info(f"RiskLevelExtractorAgent: Extracted '{self.field}' = '{result}'")
        return result
