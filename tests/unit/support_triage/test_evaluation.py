# OrKa: Orchestrator Kit Agents
# Test suite for support triage evaluation framework

"""
Unit tests for support triage evaluation framework.

Tests cover:
- EvalRunner: Test case execution
- GoldenCaseRegistry: Regression detection
- InvariantChecker: Safety invariant verification
- EvalReporter: Report generation
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone

from orka.support_triage.evaluation import (
    EvalRunner,
    GoldenCaseRegistry,
    InvariantChecker,
)
from orka.support_triage.schemas import (
    ActionPlanItem,
    ActionType,
    CaseInfo,
    Classification,
    CustomerMessage,
    Decision,
    EvalCase,
    EvalCaseExpected,
    InputEnvelope,
    OutputEnvelope,
    Reply,
    RiskAssessment,
    RiskLevel,
    TenantInfo,
    TicketChannel,
    TraceEventType,
    TrustLevel,
)
from orka.support_triage.trace import TraceEvent


def make_tenant():
    """Create a valid TenantInfo."""
    return TenantInfo(id="test_tenant")


def make_customer_message(text: str = "I need help"):
    """Create a valid CustomerMessage."""
    return CustomerMessage(
        text=text,
        source="test",
    )


def make_case_info(subject: str = "Test ticket", body: str = "I need help"):
    """Create a valid CaseInfo."""
    return CaseInfo(
        ticket_id="TKT-001",
        channel=TicketChannel.EMAIL,
        subject=subject,
        customer_message=make_customer_message(body),
    )


def make_input_envelope(
    request_id: str = "req_001",
    subject: str = "Test ticket",
    body: str = "I need help",
) -> InputEnvelope:
    """Create a valid InputEnvelope with all required fields."""
    return InputEnvelope(
        request_id=request_id,
        tenant=make_tenant(),
        case=make_case_info(subject, body),
    )


def make_risk_assessment() -> RiskAssessment:
    """Create a valid RiskAssessment."""
    return RiskAssessment(
        overall=RiskLevel.LOW,
        reasons=["Standard inquiry"],
    )


def make_decision() -> Decision:
    """Create a valid Decision."""
    return Decision(
        decision_id="dec_001",
        timestamp=datetime.now(timezone.utc),
        recommended_action="reply_only",
        risk_level="low",
        confidence_score=0.85,
        reasoning="Standard inquiry",
        citations=[],
    )


def make_output_envelope(
    request_id: str = "req_001",
    input_envelope: InputEnvelope = None,
) -> OutputEnvelope:
    """Create a valid OutputEnvelope with all required fields."""
    if input_envelope is None:
        input_envelope = make_input_envelope(request_id)
    return OutputEnvelope(
        request_id=request_id,
        risk=make_risk_assessment(),
        classification=Classification(
            intent="inquiry",
            category="support",
            priority="normal",
        ),
        action_plan=[],
        reply=Reply(
            subject="Re: Test",
            body="Thank you for contacting us.",
        ),
        citations=[],
    )


def make_trace_event(
    node_id: str = "test_node",
    event_type: TraceEventType = TraceEventType.NODE_COMPLETED,
    metadata: dict = None,
) -> TraceEvent:
    """Create a valid TraceEvent."""
    return TraceEvent(
        event_id="evt_001",
        request_id="req_001",
        timestamp=datetime.now(timezone.utc),
        node_id=node_id,
        event_type=event_type,
        status="ok",
        timing_ms=50,
        metadata=metadata or {},
    )


class TestInvariantChecker:
    """Test invariant checking for safety properties."""

    @pytest.fixture
    def checker(self):
        return InvariantChecker()

    def test_check_trust_boundary_passes_clean_input(self, checker):
        """Clean input should pass trust boundary check."""
        envelope = make_input_envelope()
        traces = [make_trace_event(node_id="check_trust")]

        result = checker.check_trust_boundary(envelope, traces)

        assert result is True

    def test_check_trust_boundary_fails_without_trust_check(self, checker):
        """Missing trust check should fail."""
        envelope = make_input_envelope()
        traces = []  # No trust check event

        result = checker.check_trust_boundary(envelope, traces)

        assert result is False
        assert len(checker.violations) > 0

    def test_check_blocked_actions_passes_allowed(self, checker):
        """Allowed actions should pass."""
        envelope = make_input_envelope()
        output = make_output_envelope(input_envelope=envelope)
        # Add a non-blocked action
        output.action_plan = [
            ActionPlanItem(
                action=ActionType.DRAFT_REPLY,
                details="Draft a reply",
                requires_human_approval=False,
            )
        ]
        traces = []

        result = checker.check_blocked_actions(envelope, output, traces)

        assert result is True

    def test_check_blocked_actions_fails_on_blocked_without_human_gate(self, checker):
        """Blocked action without human gate should fail."""
        envelope = make_input_envelope()
        # Explicitly block CLOSE_TICKET
        envelope.permissions.blocked_actions = [ActionType.CLOSE_TICKET]

        output = make_output_envelope(input_envelope=envelope)
        output.action_plan = [
            ActionPlanItem(
                action=ActionType.CLOSE_TICKET,
                details="Close the ticket",
                requires_human_approval=False,  # No human gate!
            )
        ]
        traces = []

        result = checker.check_blocked_actions(envelope, output, traces)

        assert result is False
        assert any(v["invariant"] == "blocked_actions" for v in checker.violations)

    def test_check_injection_detection_finds_injection(self, checker):
        """Should detect injection in risk reasons."""
        envelope = make_input_envelope()
        output = make_output_envelope(input_envelope=envelope)
        output.risk.reasons = ["Prompt injection attempt detected"]

        result = checker.check_injection_detection(
            envelope, output, expected_injection=True
        )

        assert result is True

    def test_check_injection_detection_fails_when_expected_not_found(self, checker):
        """Should fail when expected injection not detected."""
        envelope = make_input_envelope()
        output = make_output_envelope(input_envelope=envelope)
        output.risk.reasons = ["Standard inquiry"]

        result = checker.check_injection_detection(
            envelope, output, expected_injection=True
        )

        assert result is False
        assert any(v["invariant"] == "injection_detection" for v in checker.violations)

    def test_check_output_schema_passes_valid(self, checker):
        """Valid output should pass schema check."""
        output = make_output_envelope()
        result = checker.check_output_schema(output.model_dump(mode="json"))
        assert result is True

    def test_check_output_schema_fails_invalid(self, checker):
        """Invalid output should fail schema check."""
        invalid_output = {"invalid": "data"}
        result = checker.check_output_schema(invalid_output)
        assert result is False


class TestGoldenCaseRegistry:
    """Test golden case registry for regression detection."""

    @pytest.fixture
    def registry(self, tmp_path):
        return GoldenCaseRegistry(storage_path=str(tmp_path / "golden"))

    def test_register_and_retrieve_golden(self, registry):
        """Should register and retrieve golden case."""
        envelope = make_input_envelope()
        output = make_output_envelope(input_envelope=envelope)

        registry.register_golden(
            eval_id="case_001",
            envelope=envelope,
            output=output,
            output_hash="sha256:test123",
        )

        assert "case_001" in registry.cases

    def test_check_regression_no_change(self, registry):
        """Should not detect regression when hash matches."""
        envelope = make_input_envelope()
        output = make_output_envelope(input_envelope=envelope)

        registry.register_golden(
            eval_id="case_001",
            envelope=envelope,
            output=output,
            output_hash="sha256:test123",
        )

        result = registry.check_regression(
            eval_id="case_001",
            new_output=output,
            new_hash="sha256:test123",
        )

        assert result is None  # No regression

    def test_check_regression_detects_change(self, registry):
        """Should detect regression when hash differs."""
        envelope = make_input_envelope()
        output = make_output_envelope(input_envelope=envelope)

        registry.register_golden(
            eval_id="case_001",
            envelope=envelope,
            output=output,
            output_hash="sha256:original",
        )

        result = registry.check_regression(
            eval_id="case_001",
            new_output=output,
            new_hash="sha256:changed",
        )

        assert result is not None
        assert result["type"] == "output_regression"


class TestEvalRunner:
    """Test evaluation runner."""

    @pytest.fixture
    def mock_runner(self):
        """Create a mock workflow runner."""
        def runner(envelope_json: str):
            return {
                "request_id": "req_001",
                "risk": {"overall": "low", "reasons": ["Standard inquiry"]},
                "classification": {
                    "intent": "inquiry",
                    "category": "support",
                    "priority": "normal",
                },
                "action_plan": [],
                "reply": {
                    "subject": "Re: Test",
                    "body": "Thank you for contacting us.",
                },
                "citations": [],
            }
        return runner

    @pytest.fixture
    def runner(self, mock_runner):
        return EvalRunner(workflow_runner=mock_runner)

    def test_run_case_parses_output(self, runner):
        """Should run case and parse output."""
        case = EvalCase(
            eval_id="case_001",
            request_envelope_ref="s3://bucket/envelope.json",
            expected=EvalCaseExpected(
                intent="inquiry",
            ),
            tags=["test"],
        )
        envelope = make_input_envelope()

        result = runner.run_case(case, envelope)

        assert result.eval_id == "case_001"
        assert result.output is not None
