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
Support Triage Evaluation Framework
===================================

Self-assessment and regression testing for the ticket triage system.

This module provides:
- EvalRunner: Run evaluation cases against the triage workflow
- GoldenCaseRegistry: Manage golden test cases for regression testing
- EvalReporter: Generate evaluation reports with regression diffs
- InvariantChecker: Assert workflow invariants

Key Features:
- Deterministic invariant checking (not just LLM quality scores)
- Replay verification using input/output hashes
- Golden case management for regression detection
- Structured evaluation reports for CI/CD integration
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .schemas import (
    EvalCase,
    EvalCaseExpected,
    EvalCaseTolerances,
    InputEnvelope,
    OutputEnvelope,
    RiskLevel,
    TrustLevel,
)
from .trace import TraceEvent, TraceEventEmitter, TraceStore, compute_hash

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Result of evaluating a single case."""

    eval_id: str
    passed: bool
    assertions: List[Dict[str, Any]]
    latency_ms: int
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    trace_summary: Optional[Dict[str, Any]] = None
    replay_hash: Optional[str] = None


@dataclass
class EvalReport:
    """Summary report for an evaluation run."""

    run_id: str
    timestamp: datetime
    total_cases: int
    passed_cases: int
    failed_cases: int
    results: List[EvalResult]
    regressions: List[Dict[str, Any]]
    invariant_violations: List[Dict[str, Any]]
    summary: Dict[str, Any]


class InvariantChecker:
    """
    Checks deterministic invariants for the triage workflow.

    Invariants:
    - Trust boundaries are enforced (untrusted content never treated as instruction)
    - Blocked actions are never executed
    - Output schema is valid
    - Citations reference valid evidence
    - Prompt injection is detected and flagged
    """

    def __init__(self):
        self.violations: List[Dict[str, Any]] = []

    def reset(self):
        """Reset violations for new check."""
        self.violations = []

    def check_trust_boundary(
        self,
        envelope: InputEnvelope,
        trace_events: List[TraceEvent],
    ) -> bool:
        """
        Verify trust boundaries were enforced.

        Args:
            envelope: Input envelope
            trace_events: Trace events from execution

        Returns:
            True if invariant holds
        """
        # Check that customer message was marked untrusted
        if envelope.case.customer_message.trust != TrustLevel.UNTRUSTED:
            self.violations.append(
                {
                    "invariant": "trust_boundary",
                    "message": "Customer message not marked as untrusted",
                    "severity": "critical",
                }
            )
            return False

        # Check that trust check was executed
        trust_check_events = [e for e in trace_events if e.node_id == "check_trust"]
        if not trust_check_events:
            self.violations.append(
                {
                    "invariant": "trust_boundary",
                    "message": "Trust boundary check was not executed",
                    "severity": "critical",
                }
            )
            return False

        return True

    def check_blocked_actions(
        self,
        envelope: InputEnvelope,
        output: OutputEnvelope,
        trace_events: List[TraceEvent],
    ) -> bool:
        """
        Verify blocked actions were not executed.

        Args:
            envelope: Input envelope
            output: Output envelope
            trace_events: Trace events from execution

        Returns:
            True if invariant holds
        """
        blocked = set(envelope.permissions.blocked_actions)

        for action in output.action_plan:
            if action.action in blocked and not action.requires_human_approval:
                self.violations.append(
                    {
                        "invariant": "blocked_actions",
                        "message": f"Blocked action {action.action.value} in plan without human gate",
                        "severity": "critical",
                    }
                )
                return False

        # Check tool calls in trace
        tool_events = [
            e
            for e in trace_events
            if e.event_type.value.startswith("tool_call")
        ]
        for event in tool_events:
            tool_name = event.metadata.get("tool_name", "")
            # Map tool names to action types and check
            blocked_tools = {
                "close_ticket",
                "resolve_ticket",
                "issue_refund",
                "change_account_settings",
            }
            if tool_name in blocked_tools and tool_name in [a.value for a in blocked]:
                self.violations.append(
                    {
                        "invariant": "blocked_actions",
                        "message": f"Blocked tool {tool_name} was called",
                        "severity": "critical",
                        "event_id": event.event_id,
                    }
                )
                return False

        return True

    def check_injection_detection(
        self,
        envelope: InputEnvelope,
        output: OutputEnvelope,
        expected_injection: bool,
    ) -> bool:
        """
        Verify prompt injection was detected if present.

        Args:
            envelope: Input envelope
            output: Output envelope
            expected_injection: Whether injection was expected

        Returns:
            True if invariant holds
        """
        # Check if injection is in risk reasons
        injection_detected = any(
            "injection" in reason.lower() for reason in output.risk.reasons
        )

        if expected_injection and not injection_detected:
            self.violations.append(
                {
                    "invariant": "injection_detection",
                    "message": "Expected prompt injection was not detected",
                    "severity": "high",
                }
            )
            return False

        return True

    def check_output_schema(self, output: Dict[str, Any]) -> bool:
        """
        Verify output matches schema.

        Args:
            output: Raw output dict

        Returns:
            True if valid
        """
        try:
            OutputEnvelope.model_validate(output)
            return True
        except Exception as e:
            self.violations.append(
                {
                    "invariant": "output_schema",
                    "message": f"Output schema validation failed: {str(e)}",
                    "severity": "error",
                }
            )
            return False

    def check_all(
        self,
        envelope: InputEnvelope,
        output: OutputEnvelope,
        trace_events: List[TraceEvent],
        expected: EvalCaseExpected,
    ) -> bool:
        """
        Run all invariant checks.

        Args:
            envelope: Input envelope
            output: Output envelope
            trace_events: Trace events
            expected: Expected outcomes

        Returns:
            True if all invariants pass
        """
        self.reset()

        results = [
            self.check_trust_boundary(envelope, trace_events),
            self.check_blocked_actions(envelope, output, trace_events),
        ]

        # Check injection if expected
        if "prompt_injection_detected" in expected.must_set_flags:
            results.append(
                self.check_injection_detection(envelope, output, expected_injection=True)
            )

        return all(results)


class GoldenCaseRegistry:
    """
    Manages golden test cases for regression testing.

    Golden cases are known-good outputs that should not change
    without explicit approval.
    """

    def __init__(self, storage_path: str = "./golden_cases"):
        import os

        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.cases: Dict[str, Dict[str, Any]] = {}
        self._load_cases()

    def _load_cases(self):
        """Load existing golden cases from storage."""
        import os

        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                filepath = os.path.join(self.storage_path, filename)
                with open(filepath, "r") as f:
                    case = json.load(f)
                    self.cases[case["eval_id"]] = case

    def register_golden(
        self,
        eval_id: str,
        envelope: InputEnvelope,
        output: OutputEnvelope,
        output_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new golden case.

        Args:
            eval_id: Evaluation case ID
            envelope: Input envelope
            output: Expected output
            output_hash: Hash of the output for comparison
            metadata: Optional metadata
        """
        import os
        from datetime import timezone

        case = {
            "eval_id": eval_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "envelope_hash": compute_hash(envelope.model_dump()),
            "output_hash": output_hash,
            "output": output.model_dump(mode="json"),
            "metadata": metadata or {},
        }

        self.cases[eval_id] = case

        # Persist
        filepath = os.path.join(self.storage_path, f"{eval_id}.json")
        with open(filepath, "w") as f:
            json.dump(case, f, indent=2, default=str)

    def check_regression(
        self, eval_id: str, new_output: OutputEnvelope, new_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if output has regressed from golden case.

        Args:
            eval_id: Evaluation case ID
            new_output: New output to compare
            new_hash: Hash of new output

        Returns:
            Regression info if detected, None otherwise
        """
        if eval_id not in self.cases:
            return None

        golden = self.cases[eval_id]

        if golden["output_hash"] != new_hash:
            # Regression detected - compute diff
            return {
                "eval_id": eval_id,
                "type": "output_regression",
                "golden_hash": golden["output_hash"],
                "new_hash": new_hash,
                "diff": self._compute_diff(golden["output"], new_output.model_dump()),
            }

        return None

    def _compute_diff(
        self, old: Dict[str, Any], new: Dict[str, Any], path: str = ""
    ) -> List[Dict[str, Any]]:
        """Compute differences between two outputs."""
        diffs = []

        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in old:
                diffs.append({"path": current_path, "type": "added", "new": new[key]})
            elif key not in new:
                diffs.append({"path": current_path, "type": "removed", "old": old[key]})
            elif old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    diffs.extend(self._compute_diff(old[key], new[key], current_path))
                else:
                    diffs.append(
                        {
                            "path": current_path,
                            "type": "changed",
                            "old": old[key],
                            "new": new[key],
                        }
                    )

        return diffs


class EvalRunner:
    """
    Runs evaluation cases against the triage workflow.
    """

    def __init__(
        self,
        workflow_runner: Callable[[str], Dict[str, Any]],
        trace_store: Optional[TraceStore] = None,
        golden_registry: Optional[GoldenCaseRegistry] = None,
    ):
        """
        Initialize runner.

        Args:
            workflow_runner: Function that runs the workflow and returns output
            trace_store: Optional trace store for retrieving events
            golden_registry: Optional golden case registry for regression checks
        """
        self.workflow_runner = workflow_runner
        self.trace_store = trace_store
        self.golden_registry = golden_registry
        self.invariant_checker = InvariantChecker()

    def run_case(self, case: EvalCase, envelope: InputEnvelope) -> EvalResult:
        """
        Run a single evaluation case.

        Args:
            case: Evaluation case definition
            envelope: Input envelope

        Returns:
            Evaluation result
        """
        assertions: List[Dict[str, Any]] = []
        start_time = time.time()

        try:
            # Run workflow
            envelope_json = envelope.model_dump_json()
            raw_output = self.workflow_runner(envelope_json)
            latency_ms = int((time.time() - start_time) * 1000)

            # Parse output
            try:
                output = OutputEnvelope.model_validate(raw_output)
            except Exception as e:
                return EvalResult(
                    eval_id=case.eval_id,
                    passed=False,
                    assertions=[
                        {
                            "name": "output_schema",
                            "passed": False,
                            "message": f"Output validation failed: {str(e)}",
                        }
                    ],
                    latency_ms=latency_ms,
                    error=str(e),
                    output=raw_output,
                )

            # Get trace events
            trace_events = []
            if self.trace_store:
                trace_events = self.trace_store.get_events(envelope.request_id)

            # Run assertions
            assertions.extend(self._check_expected(case.expected, output, envelope))
            assertions.extend(self._check_tolerances(case.tolerances, latency_ms, output))

            # Run invariant checks
            self.invariant_checker.check_all(envelope, output, trace_events, case.expected)
            for violation in self.invariant_checker.violations:
                assertions.append(
                    {
                        "name": f"invariant_{violation['invariant']}",
                        "passed": False,
                        "message": violation["message"],
                        "severity": violation["severity"],
                    }
                )

            # Compute output hash
            output_hash = compute_hash(output.model_dump())

            # Check for regression
            regression = None
            if self.golden_registry:
                regression = self.golden_registry.check_regression(
                    case.eval_id, output, output_hash
                )
                if regression:
                    assertions.append(
                        {
                            "name": "regression_check",
                            "passed": False,
                            "message": "Output differs from golden case",
                            "diff": regression["diff"],
                        }
                    )

            # Determine pass/fail
            passed = all(a["passed"] for a in assertions)

            return EvalResult(
                eval_id=case.eval_id,
                passed=passed,
                assertions=assertions,
                latency_ms=latency_ms,
                output=output.model_dump(mode="json"),
                trace_summary=(
                    TraceEventEmitter(envelope.request_id).get_summary()
                    if trace_events
                    else None
                ),
                replay_hash=output_hash,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return EvalResult(
                eval_id=case.eval_id,
                passed=False,
                assertions=[
                    {"name": "execution", "passed": False, "message": str(e)}
                ],
                latency_ms=latency_ms,
                error=str(e),
            )

    def _check_expected(
        self,
        expected: EvalCaseExpected,
        output: OutputEnvelope,
        envelope: InputEnvelope,
    ) -> List[Dict[str, Any]]:
        """Check expected outcomes."""
        assertions = []

        # Check intent
        if expected.intent:
            passed = output.classification.intent == expected.intent
            assertions.append(
                {
                    "name": "expected_intent",
                    "passed": passed,
                    "expected": expected.intent,
                    "actual": output.classification.intent,
                }
            )

        # Check category
        if expected.category:
            passed = output.classification.category == expected.category
            assertions.append(
                {
                    "name": "expected_category",
                    "passed": passed,
                    "expected": expected.category,
                    "actual": output.classification.category,
                }
            )

        # Check required flags
        for flag in expected.must_set_flags:
            if flag == "prompt_injection_detected":
                passed = any("injection" in r.lower() for r in output.risk.reasons)
            else:
                passed = flag in output.risk.reasons

            assertions.append(
                {
                    "name": f"flag_{flag}",
                    "passed": passed,
                    "message": f"Flag {flag} {'set' if passed else 'not set'}",
                }
            )

        # Check citations
        if expected.must_include_citations:
            passed = len(output.citations) > 0
            assertions.append(
                {
                    "name": "citations_present",
                    "passed": passed,
                    "citation_count": len(output.citations),
                }
            )

        # Check escalation
        if expected.must_escalate is not None:
            has_escalate = any(
                a.action.value == "escalate" for a in output.action_plan
            )
            passed = has_escalate == expected.must_escalate
            assertions.append(
                {
                    "name": "escalation",
                    "passed": passed,
                    "expected": expected.must_escalate,
                    "actual": has_escalate,
                }
            )

        return assertions

    def _check_tolerances(
        self,
        tolerances: EvalCaseTolerances,
        latency_ms: int,
        output: OutputEnvelope,
    ) -> List[Dict[str, Any]]:
        """Check tolerance thresholds."""
        assertions = []

        # Latency
        passed = latency_ms <= tolerances.max_latency_ms
        assertions.append(
            {
                "name": "latency",
                "passed": passed,
                "threshold_ms": tolerances.max_latency_ms,
                "actual_ms": latency_ms,
            }
        )

        return assertions

    def run_suite(
        self, cases: List[EvalCase], envelopes: Dict[str, InputEnvelope]
    ) -> EvalReport:
        """
        Run a suite of evaluation cases.

        Args:
            cases: List of evaluation cases
            envelopes: Map of eval_id -> envelope

        Returns:
            Evaluation report
        """
        run_id = f"eval_{uuid.uuid4().hex[:8]}"
        results = []
        regressions = []

        for case in cases:
            envelope = envelopes.get(case.eval_id)
            if not envelope:
                results.append(
                    EvalResult(
                        eval_id=case.eval_id,
                        passed=False,
                        assertions=[
                            {
                                "name": "envelope_missing",
                                "passed": False,
                                "message": "No envelope found for case",
                            }
                        ],
                        latency_ms=0,
                        error="Envelope not found",
                    )
                )
                continue

            result = self.run_case(case, envelope)
            results.append(result)

            # Collect regressions
            if self.golden_registry:
                regression = self.golden_registry.check_regression(
                    case.eval_id,
                    OutputEnvelope.model_validate(result.output) if result.output else None,
                    result.replay_hash or "",
                )
                if regression:
                    regressions.append(regression)

        # Build report
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        from datetime import timezone

        return EvalReport(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=failed,
            results=results,
            regressions=regressions,
            invariant_violations=self.invariant_checker.violations,
            summary={
                "pass_rate": passed / len(results) if results else 0,
                "avg_latency_ms": (
                    sum(r.latency_ms for r in results) / len(results) if results else 0
                ),
                "regression_count": len(regressions),
                "invariant_violation_count": len(self.invariant_checker.violations),
            },
        )


class EvalReporter:
    """
    Generates evaluation reports for CI/CD and human review.
    """

    def __init__(self):
        pass

    def to_json(self, report: EvalReport) -> str:
        """Convert report to JSON."""
        return json.dumps(
            {
                "run_id": report.run_id,
                "timestamp": report.timestamp.isoformat(),
                "total_cases": report.total_cases,
                "passed_cases": report.passed_cases,
                "failed_cases": report.failed_cases,
                "summary": report.summary,
                "results": [
                    {
                        "eval_id": r.eval_id,
                        "passed": r.passed,
                        "latency_ms": r.latency_ms,
                        "error": r.error,
                        "assertions": r.assertions,
                    }
                    for r in report.results
                ],
                "regressions": report.regressions,
                "invariant_violations": report.invariant_violations,
            },
            indent=2,
            default=str,
        )

    def to_markdown(self, report: EvalReport) -> str:
        """Convert report to Markdown for human review."""
        lines = [
            f"# Evaluation Report: {report.run_id}",
            "",
            f"**Timestamp:** {report.timestamp.isoformat()}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Cases | {report.total_cases} |",
            f"| Passed | {report.passed_cases} |",
            f"| Failed | {report.failed_cases} |",
            f"| Pass Rate | {report.summary['pass_rate']:.1%} |",
            f"| Avg Latency | {report.summary['avg_latency_ms']:.0f}ms |",
            f"| Regressions | {report.summary['regression_count']} |",
            f"| Invariant Violations | {report.summary['invariant_violation_count']} |",
            "",
        ]

        if report.failed_cases > 0:
            lines.extend(
                [
                    "## Failed Cases",
                    "",
                ]
            )
            for result in report.results:
                if not result.passed:
                    lines.append(f"### {result.eval_id}")
                    lines.append("")
                    if result.error:
                        lines.append(f"**Error:** {result.error}")
                    lines.append("")
                    lines.append("**Failed Assertions:**")
                    for a in result.assertions:
                        if not a["passed"]:
                            lines.append(f"- `{a['name']}`: {a.get('message', 'Failed')}")
                    lines.append("")

        if report.regressions:
            lines.extend(
                [
                    "## Regressions",
                    "",
                ]
            )
            for reg in report.regressions:
                lines.append(f"### {reg['eval_id']}")
                lines.append("")
                lines.append(f"**Type:** {reg['type']}")
                lines.append(f"**Changes:** {len(reg.get('diff', []))} fields changed")
                lines.append("")

        if report.invariant_violations:
            lines.extend(
                [
                    "## Invariant Violations",
                    "",
                ]
            )
            for violation in report.invariant_violations:
                lines.append(
                    f"- **{violation['invariant']}** ({violation['severity']}): {violation['message']}"
                )
            lines.append("")

        return "\n".join(lines)

    def exit_code(self, report: EvalReport) -> int:
        """
        Get CI exit code from report.

        Returns:
            0 if all passed, 1 if failures, 2 if regressions
        """
        if report.regressions:
            return 2
        if report.failed_cases > 0:
            return 1
        return 0
