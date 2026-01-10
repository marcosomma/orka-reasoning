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
Support Triage System
=====================

Production-oriented ticket triage system with auditability, replay, and safety under tool use.

This module provides:
- Envelope schemas for ticket ingestion with trust boundaries
- Tool call tracking with idempotency keys
- Decision records with citations and evidence
- Trace event system for observability
- Evaluation framework for self-assessment

Key Components:
- schemas: Pydantic models for envelope, tool calls, decisions, and outputs
- validators: Input validation and trust boundary enforcement
- tools: Idempotent tool wrappers with permission checks
- trace: Event-level observability and replay support
- evaluation: Self-assessment workflows and golden case testing

Usage:
------
To activate support triage agents in OrKa workflows:

    from orka.support_triage import register_agents
    register_agents()

Or set the environment variable before running:

    ORKA_FEATURES=support_triage orka run workflow.yml

Then use the agent types in YAML:

    agents:
      - id: validate_input
        type: envelope_validator
        params:
          strict: true
"""

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from .schemas import (
    InputEnvelope,
    TenantInfo,
    TaskInfo,
    CaseInfo,
    CustomerMessage,
    Attachment,
    CustomerProfile,
    Entitlements,
    ContextInfo,
    RetrievalHandle,
    ToolCallResult,
    EvidenceInfo,
    PrivacyConstraints,
    TokenBudgets,
    Constraints,
    Permissions,
    DesiredOutput,
    ToolCall,
    ToolResult,
    ToolResultItem,
    DecisionReason,
    DecisionRisks,
    Decision,
    ActionPlanItem,
    RiskAssessment,
    Classification,
    Reply,
    Citation,
    OutputEnvelope,
    TraceEvent,
    EvalCaseExpected,
    EvalCaseTolerances,
    EvalCase,
)

from .validators import (
    EnvelopeValidator,
    TrustBoundaryEnforcer,
    PermissionChecker,
    OutputValidator,
    CitationValidator,
)

from .trace import (
    TraceEventEmitter,
    TraceStore,
    compute_hash,
)

# Flag to track if agents have been registered
_agents_registered = False


def register_agents(*, overwrite: bool = False) -> None:
    """
    Register support triage agents with the OrKa agent factory.

    This function makes the following agent types available in YAML workflows:
    - envelope_validator: Validates input envelope schema and constraints
    - redaction: Redacts PII from untrusted content
    - trust_boundary: Enforces trust boundaries and detects prompt injection
    - permission_gate: Validates tool calls against policy permissions
    - output_verification: Validates output schema and citations
    - decision_recorder: Records decisions with evidence and citations

    Args:
        overwrite: If True, allows overwriting existing agent types

    Example:
        >>> from orka.support_triage import register_agents
        >>> register_agents()
        >>> # Now you can use type: envelope_validator in YAML workflows
    """
    global _agents_registered

    if _agents_registered and not overwrite:
        logger.debug("Support triage agents already registered")
        return

    # Import here to avoid circular imports
    from ..orchestrator.agent_factory import register_agent_types
    from .agents import (
        EnvelopeValidatorAgent,
        RedactionAgent,
        TrustBoundaryAgent,
        PermissionGateAgent,
        OutputVerificationAgent,
        DecisionRecorderAgent,
        RiskLevelExtractorAgent,
    )

    agent_types = {
        "envelope_validator": EnvelopeValidatorAgent,
        "redaction": RedactionAgent,
        "trust_boundary": TrustBoundaryAgent,
        "permission_gate": PermissionGateAgent,
        "output_verification": OutputVerificationAgent,
        "decision_recorder": DecisionRecorderAgent,
        "risk_level_extractor": RiskLevelExtractorAgent,
    }

    register_agent_types(agent_types, overwrite=overwrite)
    _agents_registered = True
    logger.info(f"Registered {len(agent_types)} support triage agent types")


def is_registered() -> bool:
    """Check if support triage agents have been registered."""
    return _agents_registered

__all__ = [
    # Registration
    "register_agents",
    "is_registered",
    # Schemas
    "InputEnvelope",
    "TenantInfo",
    "TaskInfo",
    "CaseInfo",
    "CustomerMessage",
    "Attachment",
    "CustomerProfile",
    "Entitlements",
    "ContextInfo",
    "RetrievalHandle",
    "ToolCallResult",
    "EvidenceInfo",
    "PrivacyConstraints",
    "TokenBudgets",
    "Constraints",
    "Permissions",
    "DesiredOutput",
    "ToolCall",
    "ToolResult",
    "ToolResultItem",
    "DecisionReason",
    "DecisionRisks",
    "Decision",
    "ActionPlanItem",
    "RiskAssessment",
    "Classification",
    "Reply",
    "Citation",
    "OutputEnvelope",
    "TraceEvent",
    "EvalCaseExpected",
    "EvalCaseTolerances",
    "EvalCase",
    # Validators
    "EnvelopeValidator",
    "TrustBoundaryEnforcer",
    "PermissionChecker",
    "OutputValidator",
    "CitationValidator",
    # Trace
    "TraceEventEmitter",
    "TraceStore",
    "compute_hash",
]
