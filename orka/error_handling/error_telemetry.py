# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Error type constants
ERROR_TYPES = {
    "AGENT_FAILURE": "agent_failure",
    "JSON_PARSING": "json_parsing",
    "API_ERROR": "api_error",
    "MEMORY_ERROR": "memory_error",
    "EXECUTION_ERROR": "execution_error",
    "CRITICAL_FAILURE": "critical_failure",
    "STEP_EXECUTION": "step_execution",
    "METRICS_EXTRACTION": "metrics_extraction",
    "MEMORY_LOGGING": "memory_logging",
    "META_REPORT_GENERATION": "meta_report_generation",
}

# Error severity levels
ERROR_SEVERITY = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}


class ErrorTelemetry:
    """
    Handles error tracking and telemetry for the orchestrator.
    Provides methods to record, track, and analyze errors during execution.
    """

    def __init__(self, run_id):
        """
        Initialize error telemetry system.

        Args:
            run_id: Unique identifier for the current run
        """
        self.run_id = run_id
        self.error_telemetry = {
            "errors": [],  # List of all errors encountered
            "retry_counters": {},  # Per-agent retry counts
            "partial_successes": [],  # Agents that succeeded after retries
            "silent_degradations": [],  # JSON parsing failures that fell back to raw text
            "status_codes": {},  # HTTP status codes for API calls
            "execution_status": "running",  # overall status: running, completed, failed, partial
            "critical_failures": [],  # Failures that stopped execution
            "recovery_actions": [],  # Actions taken to recover from errors
        }

    def record_error(
        self,
        error_type,
        agent_id,
        error_msg,
        exception=None,
        step=None,
        status_code=None,
        recovery_action=None,
        severity=ERROR_SEVERITY["MEDIUM"],
    ):
        """
        Record an error in the error telemetry system.

        Args:
            error_type: Type of error (agent_failure, json_parsing, api_error, etc.)
            agent_id: ID of the agent that failed
            error_msg: Human readable error message
            exception: The actual exception object (optional)
            step: Step number where error occurred
            status_code: HTTP status code if applicable
            recovery_action: Action taken to recover (retry, fallback, etc.)
            severity: Error severity level
        """
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "agent_id": agent_id,
            "message": error_msg,
            "step": step,
            "run_id": self.run_id,
            "severity": severity,
        }

        if exception:
            error_entry["exception"] = {
                "type": str(type(exception).__name__),
                "message": str(exception),
                "traceback": str(exception.__traceback__)
                if hasattr(exception, "__traceback__")
                else None,
            }

        if status_code:
            error_entry["status_code"] = status_code
            self.error_telemetry["status_codes"][agent_id] = status_code

        if recovery_action:
            error_entry["recovery_action"] = recovery_action
            self.error_telemetry["recovery_actions"].append(
                {
                    "timestamp": error_entry["timestamp"],
                    "agent_id": agent_id,
                    "action": recovery_action,
                },
            )

        self.error_telemetry["errors"].append(error_entry)

        # Log error to console with appropriate emoji based on severity
        severity_emoji = {
            ERROR_SEVERITY["LOW"]: "⚠️",
            ERROR_SEVERITY["MEDIUM"]: "🚨",
            ERROR_SEVERITY["HIGH"]: "💥",
            ERROR_SEVERITY["CRITICAL"]: "🔥",
        }
        emoji = severity_emoji.get(severity, "🚨")
        print(f"{emoji} [ORKA-ERROR] {error_type} in {agent_id}: {error_msg}")

    def record_retry(self, agent_id):
        """Record a retry attempt for an agent."""
        if agent_id not in self.error_telemetry["retry_counters"]:
            self.error_telemetry["retry_counters"][agent_id] = 0
        self.error_telemetry["retry_counters"][agent_id] += 1

    def record_partial_success(self, agent_id, retry_count):
        """Record that an agent succeeded after retries."""
        self.error_telemetry["partial_successes"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "retry_count": retry_count,
            },
        )

    def record_silent_degradation(self, agent_id, degradation_type, details):
        """Record silent degradations like JSON parsing failures."""
        self.error_telemetry["silent_degradations"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "type": degradation_type,
                "details": details,
            },
        )

    def record_critical_failure(self, error, step):
        """Record a critical failure that stops execution."""
        self.error_telemetry["execution_status"] = "failed"
        self.error_telemetry["critical_failures"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(error),
                "step": step,
            },
        )

    def get_error_summary(self):
        """Get a summary of all errors encountered."""
        return {
            "total_errors": len(self.error_telemetry["errors"]),
            "total_retries": sum(self.error_telemetry["retry_counters"].values()),
            "agents_with_errors": list(
                set(error["agent_id"] for error in self.error_telemetry["errors"]),
            ),
            "execution_status": self.error_telemetry["execution_status"],
            "critical_failures_count": len(self.error_telemetry["critical_failures"]),
            "partial_successes_count": len(self.error_telemetry["partial_successes"]),
            "silent_degradations_count": len(self.error_telemetry["silent_degradations"]),
        }

    def has_critical_errors(self):
        """Check if there are any critical errors."""
        return len(self.error_telemetry["critical_failures"]) > 0

    def get_telemetry_data(self):
        """Get the complete telemetry data."""
        return self.error_telemetry.copy()

    def update_execution_status(self, status):
        """Update the overall execution status."""
        valid_statuses = ["running", "completed", "failed", "partial"]
        if status in valid_statuses:
            self.error_telemetry["execution_status"] = status
        else:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
