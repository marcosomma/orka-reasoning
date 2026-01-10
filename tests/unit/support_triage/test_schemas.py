# OrKa: Orchestrator Kit Agents
# Test suite for support triage schemas

"""
Unit tests for support triage schema models.

Tests cover:
- Input envelope validation
- Trust boundary enforcement
- Tool call schemas
- Decision record schemas
- Output envelope validation
- Trace event schemas
- Evaluation case schemas
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from orka.support_triage.schemas import (
    ActionType,
    Attachment,
    CaseInfo,
    Citation,
    Classification,
    Constraints,
    CustomerMessage,
    CustomerProfile,
    Decision,
    DecisionReason,
    DecisionRisks,
    DesiredOutput,
    Entitlements,
    EvalCase,
    EvalCaseExpected,
    EvalCaseTolerances,
    InputEnvelope,
    OutputEnvelope,
    Permissions,
    PermissionCheck,
    Reply,
    RetrievalHandle,
    RiskAssessment,
    RiskLevel,
    TaskInfo,
    TenantInfo,
    TicketChannel,
    ToolCall,
    ToolCallStatus,
    ToolResult,
    ToolResultItem,
    TraceEvent,
    TraceEventType,
    TrustLevel,
)


class TestTrustLevelEnforcement:
    """Test that trust levels are correctly enforced."""

    def test_customer_message_always_untrusted(self):
        """Customer messages must always be untrusted."""
        # Even if you try to set trust to "trusted"
        msg = CustomerMessage(
            text="Hello",
            source="zendesk",
            trust="trusted",  # Should be overridden
        )
        assert msg.trust == TrustLevel.UNTRUSTED

    def test_attachment_always_untrusted(self):
        """Attachments must always be untrusted."""
        att = Attachment(
            id="att_01",
            content_type="image/png",
            source="zendesk",
            trust="trusted",  # Should be overridden
        )
        assert att.trust == TrustLevel.UNTRUSTED

    def test_customer_profile_default_trusted(self):
        """Customer profile from CRM is trusted by default."""
        profile = CustomerProfile(
            customer_id="cust_001",
            plan="pro",
            region="EU",
        )
        assert profile.trust == TrustLevel.TRUSTED

    def test_entitlements_default_trusted(self):
        """Entitlements from billing are trusted by default."""
        entitlements = Entitlements()
        assert entitlements.trust == TrustLevel.TRUSTED


class TestInputEnvelopeValidation:
    """Test input envelope schema validation."""

    def test_minimal_valid_envelope(self):
        """Test creating a minimal valid envelope."""
        envelope = InputEnvelope(
            request_id="req_001",
            tenant=TenantInfo(id="acme"),
            case=CaseInfo(
                ticket_id="ZD-001",
                channel=TicketChannel.EMAIL,
                subject="Test",
                customer_message=CustomerMessage(
                    text="Hello",
                    source="zendesk",
                ),
            ),
        )
        assert envelope.request_id == "req_001"
        assert envelope.schema_version == "1.0"

    def test_full_envelope(self):
        """Test creating a full envelope with all fields."""
        envelope = InputEnvelope(
            schema_version="1.0",
            request_id="req_002",
            tenant=TenantInfo(id="acme_eu", environment="prod"),
            task=TaskInfo(
                type="support_ticket",
                goal="draft_reply_and_plan",
                locale="en-GB",
            ),
            case=CaseInfo(
                ticket_id="ZD-12345",
                channel=TicketChannel.ZENDESK,
                subject="Refund request",
                customer_message=CustomerMessage(
                    text="I want a refund",
                    source="zendesk",
                ),
                attachments=[
                    Attachment(
                        id="att_01",
                        content_type="image/png",
                        source="zendesk",
                    )
                ],
            ),
            permissions=Permissions(
                allowed_actions=[ActionType.DRAFT_REPLY, ActionType.ESCALATE],
                blocked_actions=[ActionType.CLOSE_TICKET],
            ),
        )
        assert len(envelope.permissions.allowed_actions) == 2
        assert ActionType.CLOSE_TICKET in envelope.permissions.blocked_actions


class TestToolCallSchemas:
    """Test tool call and result schemas."""

    def test_tool_call_creation(self):
        """Test creating a tool call record."""
        tool_call = ToolCall(
            tool_call_id="tc_001",
            request_id="req_001",
            tool_name="kb_search",
            idempotency_key="req_001:kb_search:rh_01",
            args={"query": "refund policy"},
            permission_check=PermissionCheck(
                result="allowed",
                policy_id="support_policy_v3",
            ),
        )
        assert tool_call.status == ToolCallStatus.OK
        assert tool_call.error is None

    def test_tool_result_creation(self):
        """Test creating a tool result."""
        result = ToolResult(
            result_id="tr_001",
            tool_call_id="tc_001",
            tool_name="kb_search",
            items=[
                ToolResultItem(
                    id="kb_doc_77",
                    title="Refund Policy",
                    snippet="Refunds are available within 14 days...",
                    source="internal_kb",
                )
            ],
        )
        assert result.trust == TrustLevel.TRUSTED
        assert len(result.items) == 1


class TestDecisionSchemas:
    """Test decision record schemas."""

    def test_decision_creation(self):
        """Test creating a decision record."""
        decision = Decision(
            decision_id="d_01",
            request_id="req_001",
            type="routing",
            chosen_path="refund_flow",
            confidence=0.82,
            reasons=[
                DecisionReason(
                    claim="Customer requests refund",
                    evidence_refs=["case.customer_message.text"],
                )
            ],
            risks=DecisionRisks(
                prompt_injection_detected=True,
                pii_risk=RiskLevel.MEDIUM,
            ),
        )
        assert decision.confidence == 0.82
        assert decision.risks.prompt_injection_detected

    def test_decision_confidence_bounds(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Decision(
                decision_id="d_01",
                request_id="req_001",
                type="routing",
                chosen_path="test",
                confidence=1.5,  # Invalid
                reasons=[],
            )


class TestOutputEnvelopeValidation:
    """Test output envelope schema validation."""

    def test_valid_output_envelope(self):
        """Test creating a valid output envelope."""
        output = OutputEnvelope(
            request_id="req_001",
            risk=RiskAssessment(
                overall=RiskLevel.MEDIUM,
                reasons=["Potential injection detected"],
            ),
            classification=Classification(
                intent="refund_request",
                category="billing",
                priority="normal",
            ),
            action_plan=[
                {
                    "action": ActionType.DRAFT_REPLY,
                    "details": "Send refund information",
                    "requires_human_approval": False,
                }
            ],
            reply=Reply(
                subject="Re: Refund request",
                body="Thank you for contacting us...",
            ),
            citations=[
                Citation(
                    claim="Refunds available within 14 days",
                    tool_result_id="tr_001",
                    item_id="kb_doc_77",
                )
            ],
        )
        assert output.classification.intent == "refund_request"
        assert len(output.citations) == 1


class TestTraceEventSchemas:
    """Test trace event schemas."""

    def test_trace_event_creation(self):
        """Test creating a trace event."""
        event = TraceEvent(
            event_id="ev_001",
            request_id="req_001",
            node_id="classify_intent",
            event_type=TraceEventType.NODE_COMPLETED,
            status="ok",
            timing_ms=150,
            inputs_hash="sha256:abc123",
            outputs_hash="sha256:def456",
        )
        assert event.timing_ms == 150
        assert event.event_type == TraceEventType.NODE_COMPLETED


class TestEvalCaseSchemas:
    """Test evaluation case schemas."""

    def test_eval_case_creation(self):
        """Test creating an evaluation case."""
        case = EvalCase(
            eval_id="ec_001",
            request_envelope_ref="s3://bucket/envelope.json",
            expected=EvalCaseExpected(
                intent="refund_request",
                must_set_flags=["prompt_injection_detected"],
                must_not_call_tools=["close_ticket"],
            ),
            tolerances=EvalCaseTolerances(
                max_latency_ms=15000,
            ),
            tags=["golden", "injection"],
        )
        assert "prompt_injection_detected" in case.expected.must_set_flags
        assert case.tolerances.max_latency_ms == 15000
