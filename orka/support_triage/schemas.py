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
Support Triage Schemas
======================

Pydantic models defining the canonical data structures for the ticket triage system.
These schemas ensure type safety, validation, and serialization for:

- Input envelopes (request ingestion with trust boundaries)
- Tool calls and results (idempotent, permissioned operations)
- Decision records (routing decisions with evidence and citations)
- Output envelopes (structured responses for downstream automation)
- Trace events (observability and replay)
- Evaluation cases (self-assessment and regression testing)

Trust Boundary Rules:
- Any field with trust="untrusted" is treated as content to analyze, NEVER as instructions
- Instructions to call tools or change permissions must come from trusted policy only
- This is non-optional to prevent prompt injection attacks
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TrustLevel(str, Enum):
    """Trust levels for data provenance."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class TicketChannel(str, Enum):
    """Supported ticket ingestion channels."""

    EMAIL = "email"
    ZENDESK = "zendesk"
    INTERCOM = "intercom"
    JIRA = "jira"
    SLACK = "slack"
    API = "api"


class RiskLevel(str, Enum):
    """Risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    """Types of actions in the action plan."""

    DRAFT_REPLY = "draft_reply"
    REQUEST_MORE_INFO = "request_more_info"
    ESCALATE = "escalate"
    TAG_TICKET = "tag_ticket"
    SET_PRIORITY = "set_priority"
    ASSIGN_AGENT = "assign_agent"
    CLOSE_TICKET = "close_ticket"


class ToolCallStatus(str, Enum):
    """Status of a tool call execution."""

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"


class TraceEventType(str, Enum):
    """Types of trace events for observability."""

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    DECISION_MADE = "decision_made"
    HUMAN_GATE_REQUESTED = "human_gate_requested"
    HUMAN_GATE_APPROVED = "human_gate_approved"
    HUMAN_GATE_REJECTED = "human_gate_rejected"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"


# =============================================================================
# Input Envelope Components
# =============================================================================


class TenantInfo(BaseModel):
    """Tenant identification for multi-tenant support."""

    id: str = Field(..., description="Tenant identifier (e.g., 'acme_eu')")
    environment: Literal["prod", "staging", "dev"] = Field(
        default="prod", description="Deployment environment"
    )


class TaskInfo(BaseModel):
    """Task specification for the triage workflow."""

    type: Literal["support_ticket", "incident", "feature_request"] = Field(
        default="support_ticket", description="Type of task to process"
    )
    goal: Literal["draft_reply_and_plan", "classify_only", "full_resolution"] = Field(
        default="draft_reply_and_plan", description="Processing goal"
    )
    locale: str = Field(default="en-US", description="Locale for response generation")
    priority_hint: Literal["low", "normal", "high", "urgent"] = Field(
        default="normal", description="Initial priority hint from source system"
    )


class CustomerMessage(BaseModel):
    """Customer message with trust boundary annotation."""

    text: str = Field(..., description="Raw message text from customer")
    source: str = Field(..., description="Source system (e.g., 'zendesk', 'email')")
    trust: TrustLevel = Field(
        default=TrustLevel.UNTRUSTED,
        description="Trust level - customer messages are ALWAYS untrusted",
    )
    received_at: datetime = Field(
        default_factory=_utc_now, description="When the message was received"
    )

    @field_validator("trust", mode="before")
    @classmethod
    def enforce_untrusted(cls, v: Any) -> TrustLevel:
        """Customer messages are always untrusted regardless of input."""
        return TrustLevel.UNTRUSTED


class Attachment(BaseModel):
    """Attachment metadata with trust boundary annotation."""

    id: str = Field(..., description="Attachment identifier")
    content_type: str = Field(..., description="MIME type of the attachment")
    source: str = Field(..., description="Source system")
    trust: TrustLevel = Field(
        default=TrustLevel.UNTRUSTED,
        description="Trust level - attachments are ALWAYS untrusted",
    )
    filename: Optional[str] = Field(default=None, description="Original filename")
    size_bytes: Optional[int] = Field(default=None, description="File size in bytes")

    @field_validator("trust", mode="before")
    @classmethod
    def enforce_untrusted(cls, v: Any) -> TrustLevel:
        """Attachments are always untrusted regardless of input."""
        return TrustLevel.UNTRUSTED


class CaseInfo(BaseModel):
    """Case/ticket information from the source system."""

    ticket_id: str = Field(..., description="Ticket ID from source system")
    channel: TicketChannel = Field(..., description="Ingestion channel")
    subject: str = Field(..., description="Ticket subject line")
    customer_message: CustomerMessage = Field(..., description="Customer's message")
    attachments: List[Attachment] = Field(
        default_factory=list, description="List of attachments"
    )
    thread_history: List[CustomerMessage] = Field(
        default_factory=list, description="Previous messages in thread"
    )


class CustomerProfile(BaseModel):
    """Customer profile from CRM with trust annotation."""

    customer_id: str = Field(..., description="Customer identifier")
    plan: str = Field(..., description="Subscription plan (e.g., 'pro', 'enterprise')")
    region: str = Field(..., description="Customer region (e.g., 'EU', 'US')")
    source: str = Field(default="crm", description="Source system for this data")
    trust: TrustLevel = Field(
        default=TrustLevel.TRUSTED, description="CRM data is trusted by default"
    )
    last_updated_at: datetime = Field(
        default_factory=_utc_now, description="When profile was last updated"
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Custom profile fields"
    )


class Entitlements(BaseModel):
    """Customer entitlements from billing system."""

    refund_allowed: bool = Field(default=False, description="Whether refunds are allowed")
    max_refund_amount_eur: float = Field(
        default=0.0, description="Maximum refund amount in EUR"
    )
    source: str = Field(default="billing", description="Source system")
    trust: TrustLevel = Field(
        default=TrustLevel.TRUSTED, description="Billing data is trusted by default"
    )
    last_updated_at: datetime = Field(
        default_factory=_utc_now, description="When entitlements were last checked"
    )
    features: List[str] = Field(
        default_factory=list, description="List of entitled features"
    )


class ContextInfo(BaseModel):
    """Aggregated context from trusted internal systems."""

    customer_profile: Optional[CustomerProfile] = Field(
        default=None, description="Customer profile from CRM"
    )
    entitlements: Optional[Entitlements] = Field(
        default=None, description="Customer entitlements from billing"
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Additional trusted context"
    )


class RetrievalHandle(BaseModel):
    """Handle for pending or completed retrieval operations."""

    id: str = Field(..., description="Unique handle identifier")
    tool: str = Field(..., description="Tool to use for retrieval")
    query: str = Field(..., description="Query for the retrieval")
    trust: TrustLevel = Field(
        default=TrustLevel.TRUSTED, description="Retrieved data trust level"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When handle was created"
    )


class ToolCallResult(BaseModel):
    """Reference to a completed tool call result."""

    result_id: str = Field(..., description="Result identifier")
    tool_call_id: str = Field(..., description="Original tool call ID")


class EvidenceInfo(BaseModel):
    """Evidence collected during processing."""

    retrieval_handles: List[RetrievalHandle] = Field(
        default_factory=list, description="Pending retrieval operations"
    )
    tool_results: List[ToolCallResult] = Field(
        default_factory=list, description="Completed tool call results"
    )


class PrivacyConstraints(BaseModel):
    """Privacy and PII handling constraints."""

    pii_redacted: bool = Field(
        default=True, description="Whether PII should be redacted"
    )
    redaction_level: Literal["strict", "moderate", "minimal"] = Field(
        default="strict", description="Level of PII redaction"
    )


class TokenBudgets(BaseModel):
    """Token budget constraints for LLM calls."""

    max_input_tokens: int = Field(
        default=8000, description="Maximum input tokens per LLM call"
    )
    max_output_tokens: int = Field(
        default=1200, description="Maximum output tokens per LLM call"
    )


class Constraints(BaseModel):
    """Processing constraints and policies."""

    policy_id: str = Field(
        default="default_policy_v1", description="Policy identifier for permission checks"
    )
    privacy: PrivacyConstraints = Field(
        default_factory=PrivacyConstraints, description="Privacy constraints"
    )
    token_budgets: TokenBudgets = Field(
        default_factory=TokenBudgets, description="Token budget constraints"
    )
    max_latency_ms: int = Field(
        default=30000, description="Maximum total latency in milliseconds"
    )


class Permissions(BaseModel):
    """Allowed and blocked actions for this request."""

    allowed_actions: List[ActionType] = Field(
        default_factory=lambda: [
            ActionType.DRAFT_REPLY,
            ActionType.REQUEST_MORE_INFO,
            ActionType.ESCALATE,
        ],
        description="Actions the workflow is allowed to take",
    )
    blocked_actions: List[ActionType] = Field(
        default_factory=lambda: [ActionType.CLOSE_TICKET],
        description="Actions explicitly blocked for this request",
    )


class DesiredOutput(BaseModel):
    """Output format specification."""

    format: Literal["json", "text", "markdown"] = Field(
        default="json", description="Output format"
    )
    require_citations: bool = Field(
        default=True, description="Whether citations are required"
    )


class InputEnvelope(BaseModel):
    """
    Canonical input envelope for ticket triage.

    This is the primary artifact stored for replay. It carries trust boundaries,
    provenance, freshness, and versioning.

    Trust Boundary Rules:
    - Any field with trust="untrusted" is NEVER treated as instruction
    - Instructions must come from trusted policy and orchestrator only
    - Customer messages and attachments are ALWAYS untrusted
    """

    schema_version: str = Field(
        default="1.0", description="Schema version for forward compatibility"
    )
    request_id: str = Field(..., description="Unique request identifier for tracing")
    tenant: TenantInfo = Field(..., description="Tenant information")
    task: TaskInfo = Field(default_factory=TaskInfo, description="Task specification")
    case: CaseInfo = Field(..., description="Case/ticket information")
    context: ContextInfo = Field(
        default_factory=ContextInfo, description="Trusted context from internal systems"
    )
    evidence: EvidenceInfo = Field(
        default_factory=EvidenceInfo, description="Evidence collected during processing"
    )
    constraints: Constraints = Field(
        default_factory=Constraints, description="Processing constraints"
    )
    permissions: Permissions = Field(
        default_factory=Permissions, description="Allowed/blocked actions"
    )
    desired_output: DesiredOutput = Field(
        default_factory=DesiredOutput, description="Output format specification"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When envelope was created"
    )


# =============================================================================
# Tool Call Schemas
# =============================================================================


class PermissionCheck(BaseModel):
    """Result of a permission check for a tool call."""

    result: Literal["allowed", "denied", "rate_limited"] = Field(
        ..., description="Permission check result"
    )
    policy_id: str = Field(..., description="Policy that was applied")
    reason: Optional[str] = Field(default=None, description="Reason for denial if any")


class ToolCall(BaseModel):
    """
    Tool call artifact for replay and incident debugging.

    Includes idempotency keys, latency tracking, and error typing.
    """

    tool_call_id: str = Field(..., description="Unique tool call identifier")
    request_id: str = Field(..., description="Parent request ID")
    tool_name: str = Field(..., description="Name of the tool being called")
    idempotency_key: str = Field(
        ..., description="Key for idempotent execution (request_id:tool:handle_id)"
    )
    args: Dict[str, Any] = Field(..., description="Arguments passed to the tool")
    permission_check: PermissionCheck = Field(
        ..., description="Permission check result"
    )
    started_at: datetime = Field(
        default_factory=_utc_now, description="When execution started"
    )
    finished_at: Optional[datetime] = Field(
        default=None, description="When execution finished"
    )
    status: ToolCallStatus = Field(
        default=ToolCallStatus.OK, description="Execution status"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    result_ref: Optional[str] = Field(
        default=None, description="Reference to result artifact"
    )
    latency_ms: Optional[int] = Field(
        default=None, description="Execution latency in milliseconds"
    )


class ToolResultItem(BaseModel):
    """Individual item in a tool result (e.g., KB article, account record)."""

    id: str = Field(..., description="Item identifier")
    title: Optional[str] = Field(default=None, description="Item title")
    snippet: str = Field(..., description="Content snippet")
    source: str = Field(..., description="Source system")
    url: Optional[str] = Field(default=None, description="URL to full content")
    last_updated_at: Optional[datetime] = Field(
        default=None, description="When content was last updated"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ToolResult(BaseModel):
    """Result from a tool call with provenance."""

    result_id: str = Field(..., description="Unique result identifier")
    tool_call_id: str = Field(..., description="ID of the tool call that produced this")
    tool_name: str = Field(..., description="Name of the tool")
    trust: TrustLevel = Field(
        default=TrustLevel.TRUSTED, description="Trust level of results"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When result was created"
    )
    items: List[ToolResultItem] = Field(
        default_factory=list, description="Result items"
    )
    raw_response: Optional[Dict[str, Any]] = Field(
        default=None, description="Raw tool response for debugging"
    )


# =============================================================================
# Decision Record Schemas
# =============================================================================


class DecisionReason(BaseModel):
    """Reason supporting a decision with evidence references."""

    claim: str = Field(..., description="The claim being made")
    evidence_refs: List[str] = Field(
        ..., description="References to evidence (e.g., 'case.customer_message.text')"
    )


class DecisionRisks(BaseModel):
    """Risk flags identified during decision making."""

    prompt_injection_detected: bool = Field(
        default=False, description="Whether prompt injection was detected"
    )
    pii_risk: RiskLevel = Field(default=RiskLevel.LOW, description="PII exposure risk")
    financial_risk: RiskLevel = Field(
        default=RiskLevel.LOW, description="Financial risk level"
    )
    compliance_risk: RiskLevel = Field(
        default=RiskLevel.LOW, description="Compliance/legal risk"
    )
    custom_risks: Dict[str, RiskLevel] = Field(
        default_factory=dict, description="Custom risk flags"
    )


class Decision(BaseModel):
    """
    Decision record for routing and classification.

    Every routing decision and every "why" is recorded in a compact, structured way.
    This is what makes the system credible for business users.
    """

    decision_id: str = Field(..., description="Unique decision identifier")
    request_id: str = Field(..., description="Parent request ID")
    type: Literal["routing", "classification", "action", "escalation"] = Field(
        ..., description="Type of decision"
    )
    chosen_path: str = Field(..., description="The path or action chosen")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    reasons: List[DecisionReason] = Field(
        ..., description="Reasons supporting this decision"
    )
    risks: DecisionRisks = Field(
        default_factory=DecisionRisks, description="Risk assessment"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When decision was made"
    )
    model_id: Optional[str] = Field(
        default=None, description="LLM model that made the decision"
    )


# =============================================================================
# Output Envelope Schemas
# =============================================================================


class RiskAssessment(BaseModel):
    """Overall risk assessment for the request."""

    overall: RiskLevel = Field(..., description="Overall risk level")
    reasons: List[str] = Field(..., description="Reasons for the risk assessment")


class Classification(BaseModel):
    """Classification result for the ticket."""

    intent: str = Field(..., description="Detected intent (e.g., 'refund_request')")
    category: str = Field(..., description="Category (e.g., 'billing', 'technical')")
    priority: Literal["low", "normal", "high", "urgent"] = Field(
        ..., description="Determined priority"
    )
    sub_intents: List[str] = Field(
        default_factory=list, description="Secondary intents detected"
    )


class ActionPlanItem(BaseModel):
    """Single action in the action plan."""

    action: ActionType = Field(..., description="Type of action")
    details: str = Field(..., description="Details about the action")
    requires_human_approval: bool = Field(
        default=True, description="Whether human approval is needed"
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW, description="Risk level of this action"
    )
    preconditions: List[str] = Field(
        default_factory=list, description="Conditions that must be met"
    )


class Reply(BaseModel):
    """Draft reply to the customer."""

    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Reply body text")
    tone: Literal["professional", "friendly", "formal", "empathetic"] = Field(
        default="professional", description="Tone of the reply"
    )
    language: str = Field(default="en", description="Language code")


class Citation(BaseModel):
    """Citation linking a claim to evidence."""

    claim: str = Field(..., description="The claim being cited")
    tool_result_id: str = Field(..., description="ID of the tool result")
    item_id: str = Field(..., description="ID of the specific item in the result")
    quote: Optional[str] = Field(
        default=None, description="Direct quote from the source"
    )


class OutputEnvelope(BaseModel):
    """
    Structured output for downstream automation.

    Forces structured outputs to enable automated checks and downstream automation.
    """

    request_id: str = Field(..., description="Parent request ID")
    risk: RiskAssessment = Field(..., description="Risk assessment")
    classification: Classification = Field(..., description="Classification result")
    action_plan: List[ActionPlanItem] = Field(..., description="Recommended actions")
    reply: Reply = Field(..., description="Draft reply")
    citations: List[Citation] = Field(..., description="Evidence citations")
    decisions: List[str] = Field(
        default_factory=list, description="IDs of decisions that led to this output"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When output was generated"
    )
    model_versions: Dict[str, str] = Field(
        default_factory=dict, description="Model versions used"
    )


# =============================================================================
# Trace Event Schema
# =============================================================================


class TraceWrite(BaseModel):
    """Record of a write operation to state."""

    path: str = Field(..., description="Path that was written (e.g., 'output')")
    op: Literal["replace", "append", "merge"] = Field(
        ..., description="Operation type"
    )


class TraceEvent(BaseModel):
    """
    Trace event for observability.

    This is the OrKa product surface - event-level observability, not just logs.
    """

    event_id: str = Field(..., description="Unique event identifier")
    request_id: str = Field(..., description="Parent request ID")
    node_id: str = Field(..., description="Node that emitted this event")
    event_type: TraceEventType = Field(..., description="Type of event")
    status: Literal["ok", "error", "warning"] = Field(
        ..., description="Event status"
    )
    timing_ms: int = Field(..., description="Timing in milliseconds")
    inputs_hash: Optional[str] = Field(
        default=None, description="SHA256 hash of inputs for replay verification"
    )
    outputs_hash: Optional[str] = Field(
        default=None, description="SHA256 hash of outputs for replay verification"
    )
    writes: List[TraceWrite] = Field(
        default_factory=list, description="State writes performed"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When event was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata"
    )


# =============================================================================
# Evaluation Case Schema
# =============================================================================


class EvalCaseExpected(BaseModel):
    """Expected outcomes for an evaluation case."""

    intent: Optional[str] = Field(default=None, description="Expected intent")
    category: Optional[str] = Field(default=None, description="Expected category")
    must_set_flags: List[str] = Field(
        default_factory=list, description="Flags that must be set"
    )
    must_not_call_tools: List[str] = Field(
        default_factory=list, description="Tools that must NOT be called"
    )
    must_include_citations: bool = Field(
        default=True, description="Whether citations are required"
    )
    must_escalate: Optional[bool] = Field(
        default=None, description="Whether escalation is required"
    )
    blocked_actions_must_not_execute: bool = Field(
        default=True, description="Verify blocked actions are not executed"
    )


class EvalCaseTolerances(BaseModel):
    """Tolerances for evaluation case assertions."""

    max_latency_ms: int = Field(
        default=15000, description="Maximum acceptable latency"
    )
    confidence_min: float = Field(
        default=0.7, description="Minimum acceptable confidence"
    )
    output_similarity_threshold: float = Field(
        default=0.85, description="Similarity threshold for output comparison"
    )


class EvalCase(BaseModel):
    """
    Evaluation case for self-assessment and regression testing.

    Stores real cases as sanitized envelopes plus expected properties.
    """

    eval_id: str = Field(..., description="Unique evaluation case ID")
    request_envelope_ref: str = Field(
        ..., description="Reference to stored envelope (e.g., s3://...)"
    )
    expected: EvalCaseExpected = Field(..., description="Expected outcomes")
    tolerances: EvalCaseTolerances = Field(
        default_factory=EvalCaseTolerances, description="Assertion tolerances"
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for filtering (e.g., 'golden', 'injection')"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When case was created"
    )
    description: Optional[str] = Field(
        default=None, description="Human-readable description"
    )
