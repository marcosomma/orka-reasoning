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

"""
Error Handling
==============

Comprehensive error tracking, reporting, and recovery mechanisms.
"""

import json
import os
from datetime import UTC, datetime


class ErrorHandler:
    """
    Handles error tracking, reporting, and recovery mechanisms.
    """

    def _record_error(
        self,
        error_type,
        agent_id,
        error_msg,
        exception=None,
        step=None,
        status_code=None,
        recovery_action=None,
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
        """
        error_entry = {
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

        # Log error to console
        logger.error(f"🚨 [ORKA-ERROR] {error_type} in {agent_id}: {error_msg}")

    def _record_retry(self, agent_id):
        """Record a retry attempt for an agent."""
        if agent_id not in self.error_telemetry["retry_counters"]:
            self.error_telemetry["retry_counters"][agent_id] = 0
        self.error_telemetry["retry_counters"][agent_id] += 1

    def _record_partial_success(self, agent_id, retry_count):
        """Record that an agent succeeded after retries."""
        self.error_telemetry["partial_successes"].append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "agent_id": agent_id,
                "retry_count": retry_count,
            },
        )

    def _record_silent_degradation(self, agent_id, degradation_type, details):
        """Record silent degradations like JSON parsing failures."""
        self.error_telemetry["silent_degradations"].append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "agent_id": agent_id,
                "type": degradation_type,
                "details": details,
            },
        )

    def _save_error_report(self, logs, final_error=None):
        """
        Save comprehensive error report with all logged data up to the failure point.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Determine final execution status
        if final_error:
            self.error_telemetry["execution_status"] = "failed"
            self.error_telemetry["critical_failures"].append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": str(final_error),
                    "step": self.step_index,
                },
            )
        elif self.error_telemetry["errors"]:
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
                "total_errors": len(self.error_telemetry["errors"]),
                "total_retries": sum(self.error_telemetry["retry_counters"].values()),
                "agents_with_errors": list(
                    set(error["agent_id"] for error in self.error_telemetry["errors"]),
                ),
                "memory_snapshot": self._capture_memory_snapshot(),
            },
        }

        # Save error report
        error_report_path = os.path.join(log_dir, f"orka_error_report_{timestamp}.json")
        try:
            with open(error_report_path, "w") as f:
                json.dump(error_report, f, indent=2, default=str)
            logger.info(f"Error report saved: {error_report_path}")
        except Exception as e:
            logger.error(f"Failed to save error report: {e}")

        # Also save to memory backend
        try:
            trace_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
            self.memory.save_to_file(trace_path)
            logger.info(f"Execution trace saved: {trace_path}")
        except Exception as e:
            logger.error(f"Failed to save trace to memory backend: {e}")

        return error_report_path

    def _capture_memory_snapshot(self):
        """Capture current state of memory backend for debugging."""
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
