# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""Error handling for the OrKa orchestrator.

Comprehensive error tracking, reporting, and recovery mechanisms.
"""

import json
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union

# Type aliases
ErrorEntry = Dict[str, Any]
RetryCounters = Dict[str, int]
StatusCodes = Dict[str, int]
RecoveryAction = Dict[str, str]
ErrorTelemetry = Dict[
    str, Union[str, List[ErrorEntry], RetryCounters, StatusCodes, List[RecoveryAction]]
]
MemorySnapshot = Dict[str, Union[int, List[Any], str]]
MetaReport = Dict[str, Any]
ExecutionLog = Dict[str, Any]


class ErrorHandler:
    """Handles error tracking, reporting, and recovery mechanisms."""

    def __init__(self) -> None:
        """Initialize the error handler."""
        self.step_index: int = 0
        self.run_id: str = ""
        self.error_telemetry: Dict[str, Any] = {
            "execution_status": "pending",
            "errors": [],
            "retry_counters": {},
            "status_codes": {},
            "recovery_actions": [],
            "partial_successes": [],
            "silent_degradations": [],
            "critical_failures": [],
        }
        self.memory: Any = None  # Will be set by the orchestrator

    def _generate_meta_report(self, logs: List[ExecutionLog]) -> MetaReport:
        """
        Generate a meta report from execution logs.

        Args:
            logs: List of execution logs

        Returns:
            Meta report containing execution statistics
        """
        return {
            "total_agents_executed": len(logs),
            "run_id": self.run_id,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _record_error(
        self,
        error_type: str,
        agent_id: str,
        error_msg: str,
        exception: Optional[Exception] = None,
        step: Optional[int] = None,
        status_code: Optional[int] = None,
        recovery_action: Optional[str] = None,
    ) -> None:
        """
        Record an error in the error telemetry system.

        Args:
            error_type: Type of error (agent_failure, json_parsing, api_error, etc.)
            agent_id: ID of the agent that failed
            error_msg: Human readable error message
            exception: The actual exception object
            step: Step number where error occurred
            status_code: HTTP status code if applicable
            recovery_action: Action taken to recover (retry, fallback, etc.)
        """
        error_entry: ErrorEntry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": error_type,
            "agent_id": agent_id,
            "message": error_msg,
            "step": step or self.step_index,
            "run_id": self.run_id,
        }

        if exception:
            error_entry["exception"] = {
                "type": str(type(exception).__name__),
                "message": str(exception),
                "traceback": (
                    str(exception.__traceback__) if hasattr(exception, "__traceback__") else None
                ),
            }

        if status_code:
            error_entry["status_code"] = status_code
            if isinstance(self.error_telemetry["status_codes"], dict):
                self.error_telemetry["status_codes"][agent_id] = status_code

        if recovery_action:
            error_entry["recovery_action"] = recovery_action
            if isinstance(self.error_telemetry["recovery_actions"], list):
                self.error_telemetry["recovery_actions"].append(
                    {
                        "timestamp": error_entry["timestamp"],
                        "agent_id": agent_id,
                        "action": recovery_action,
                    },
                )

        if isinstance(self.error_telemetry["errors"], list):
            self.error_telemetry["errors"].append(error_entry)

        # Log error to console
        print(f"🚨 [ORKA-ERROR] {error_type} in {agent_id}: {error_msg}")

    def _record_retry(self, agent_id: str) -> None:
        """
        Record a retry attempt for an agent.

        Args:
            agent_id: ID of the agent being retried
        """
        if isinstance(self.error_telemetry["retry_counters"], dict):
            if agent_id not in self.error_telemetry["retry_counters"]:
                self.error_telemetry["retry_counters"][agent_id] = 0
            self.error_telemetry["retry_counters"][agent_id] += 1

    def _record_partial_success(self, agent_id: str, retry_count: int) -> None:
        """
        Record that an agent succeeded after retries.

        Args:
            agent_id: ID of the agent that succeeded
            retry_count: Number of retries before success
        """
        if isinstance(self.error_telemetry["partial_successes"], list):
            self.error_telemetry["partial_successes"].append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "agent_id": agent_id,
                    "retry_count": retry_count,
                },
            )

    def _record_silent_degradation(
        self, agent_id: str, degradation_type: str, details: Dict[str, Any]
    ) -> None:
        """
        Record silent degradations like JSON parsing failures.

        Args:
            agent_id: ID of the agent that experienced degradation
            degradation_type: Type of degradation
            details: Additional details about the degradation
        """
        if isinstance(self.error_telemetry["silent_degradations"], list):
            self.error_telemetry["silent_degradations"].append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "agent_id": agent_id,
                    "type": degradation_type,
                    "details": details,
                },
            )

    def _save_error_report(
        self, logs: List[ExecutionLog], final_error: Optional[Exception] = None
    ) -> str:
        """
        Save comprehensive error report with all logged data up to the failure point.

        Args:
            logs: List of execution logs
            final_error: Final error that caused execution to stop

        Returns:
            Path to the saved error report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Determine final execution status
        if final_error:
            self.error_telemetry["execution_status"] = "failed"
            if isinstance(self.error_telemetry["critical_failures"], list):
                self.error_telemetry["critical_failures"].append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "error": str(final_error),
                        "step": self.step_index,
                    },
                )
        elif isinstance(self.error_telemetry["errors"], list) and self.error_telemetry["errors"]:
            self.error_telemetry["execution_status"] = "partial"
        else:
            self.error_telemetry["execution_status"] = "completed"

        # Generate meta report even on failure
        try:
            meta_report = self._generate_meta_report(logs)
        except Exception as e:
            self._record_error(
                "meta_report_generation",
                "meta_report",
                f"Failed to generate meta report: {e}",
                e,
            )
            meta_report = {
                "error": "Failed to generate meta report",
                "partial_data": {
                    "total_agents_executed": len(logs),
                    "run_id": self.run_id,
                },
            }

        # Create comprehensive error report
        error_report = {
            "orka_execution_report": {
                "run_id": self.run_id,
                "timestamp": timestamp,
                "execution_status": self.error_telemetry["execution_status"],
                "error_telemetry": self.error_telemetry,
                "meta_report": meta_report,
                "execution_logs": logs,
                "total_steps_attempted": self.step_index,
                "total_errors": (
                    len(self.error_telemetry["errors"])
                    if isinstance(self.error_telemetry["errors"], list)
                    else 0
                ),
                "total_retries": (
                    sum(self.error_telemetry["retry_counters"].values())
                    if isinstance(self.error_telemetry["retry_counters"], dict)
                    else 0
                ),
                "agents_with_errors": (
                    {
                        error["agent_id"]
                        for error in self.error_telemetry["errors"]
                        if isinstance(error, dict) and "agent_id" in error
                    }
                    if isinstance(self.error_telemetry["errors"], list)
                    else set()
                ),
                "memory_snapshot": self._capture_memory_snapshot(),
            },
        }

        # Save error report
        error_report_path = os.path.join(log_dir, f"orka_error_report_{timestamp}.json")
        try:
            with open(error_report_path, "w") as f:
                json.dump(error_report, f, indent=2, default=str)
            print(f"Error report saved: {error_report_path}")
        except Exception as e:
            print(f"Failed to save error report: {e}")

        # Also save to memory backend
        try:
            trace_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
            self.memory.save_to_file(trace_path)
            print(f"Execution trace saved: {trace_path}")
        except Exception as e:
            print(f"Failed to save trace to memory backend: {e}")

        return error_report_path

    def _capture_memory_snapshot(self) -> MemorySnapshot:
        """
        Capture current state of memory backend for debugging.

        Returns:
            Dictionary containing memory state information
        """
        try:
            if hasattr(self.memory, "memory") and self.memory.memory:
                return {
                    "total_entries": len(self.memory.memory),
                    "last_10_entries": (
                        self.memory.memory[-10:]
                        if len(self.memory.memory) >= 10
                        else self.memory.memory
                    ),
                    "backend_type": type(self.memory).__name__,
                }
        except Exception as e:
            return {"error": f"Failed to capture memory snapshot: {e}"}
        return {"status": "no_memory_data"}
