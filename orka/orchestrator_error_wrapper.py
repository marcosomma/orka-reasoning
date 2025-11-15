#!/usr/bin/env python3
"""
Error handling wrapper for OrKa Orchestrator.
Provides comprehensive error tracking and telemetry without modifying the core orchestrator logic.
"""

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, TypedDict

logger = logging.getLogger(__name__)


class ErrorTelemetry(TypedDict):
    errors: List[Dict[str, Any]]
    retry_counters: Dict[str, int]
    partial_successes: List[Any]
    silent_degradations: List[Dict[str, Any]]
    status_codes: Dict[str, int]
    execution_status: str
    critical_failures: List[Dict[str, Any]]
    recovery_actions: List[Dict[str, Any]]


class OrkaErrorHandler:
    """
    Comprehensive error handling system for OrKa orchestrator.
    Tracks errors, retries, status codes, and provides detailed debugging reports.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.error_telemetry: ErrorTelemetry = {
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
        error_type: str,
        agent_id: str,
        error_msg: str,
        exception: Exception | None = None,
        step: int | None = None,
        status_code: int | None = None,
        recovery_action: str | None = None,
    ):
        """Record an error in the error telemetry system."""
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "agent_id": str(agent_id),
            "message": error_msg,
            "step": step or getattr(self.orchestrator, "step_index", 0),
            "run_id": getattr(self.orchestrator, "run_id", "unknown"),
        }

        if exception:
            error_entry["exception"] = {
                "type": str(type(exception).__name__),
                "message": str(exception),
                "traceback": traceback.format_exc(),
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
        logger.info(f"🚨 [ORKA-ERROR] {error_type} in {agent_id}: {error_msg}")

    def record_silent_degradation(self, agent_id: str, degradation_type: str, details: str):
        """Record silent degradations like JSON parsing failures."""
        self.error_telemetry["silent_degradations"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "type": degradation_type,
                "details": details,
            },
        )

    def save_comprehensive_error_report(
        self, logs: List[Dict], final_error: Exception | None = None
    ):
        """Save comprehensive error report with all logged data up to the failure point."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Determine final execution status
        if final_error:
            self.error_telemetry["execution_status"] = "failed"
            self.error_telemetry["critical_failures"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": str(final_error),
                    "step": getattr(self.orchestrator, "step_index", 0),
                },
            )
        elif self.error_telemetry["errors"]:
            self.error_telemetry["execution_status"] = "partial"
        else:
            self.error_telemetry["execution_status"] = "completed"

        # Generate meta report even on failure
        try:
            meta_report = self.orchestrator._generate_meta_report(logs)
        except Exception as e:
            self.record_error(
                "meta_report_generation",
                "meta_report",
                f"Failed to generate meta report: {e}",
                e,
            )
            meta_report = {
                "error": "Failed to generate meta report",
                "partial_data": {
                    "total_agents_executed": len(logs),
                    "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                },
            }

        # Create comprehensive error report
        error_report = {
            "orka_execution_report": {
                "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                "timestamp": timestamp,
                "execution_status": self.error_telemetry["execution_status"],
                "error_telemetry": self.error_telemetry,
                "meta_report": meta_report,
                "execution_logs": logs,
                "total_steps_attempted": getattr(self.orchestrator, "step_index", 0),
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
            logger.info(f"📋 Comprehensive error report saved: {error_report_path}")
        except Exception as e:
            logger.info(f"❌ Failed to save error report: {e}")

        # Also save execution trace
        try:
            trace_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
            self.orchestrator.memory.save_to_file(trace_path)
            logger.info(f"📋 Execution trace saved: {trace_path}")
        except Exception as e:
            logger.info(f"⚠️ Failed to save trace to memory backend: {e}")

        return error_report_path

    def _capture_memory_snapshot(self):
        """Capture current state of memory backend for debugging."""
        try:
            if hasattr(self.orchestrator.memory, "memory") and self.orchestrator.memory.memory:
                return {
                    "total_entries": len(self.orchestrator.memory.memory),
                    "last_10_entries": (
                        self.orchestrator.memory.memory[-10:]
                        if len(self.orchestrator.memory.memory) >= 10
                        else self.orchestrator.memory.memory
                    ),
                    "backend_type": type(self.orchestrator.memory).__name__,
                }
        except Exception as e:
            return {"error": f"Failed to capture memory snapshot: {e}"}
        return {"status": "no_memory_data"}

    async def run_with_error_handling(self, input_data):
        """
        Run the orchestrator with comprehensive error handling.
        Always returns a JSON report, even on failure, for debugging purposes.
        """
        logs = []

        # Store original run method
        original_run = self.orchestrator.run

        try:
            # Monkey patch to capture logs and add error handling to individual agents
            self._patch_orchestrator_for_error_tracking()

            # Run the orchestrator normally
            result = await original_run(input_data)

            # Check if any errors occurred during execution
            if self.error_telemetry["errors"]:
                logger.info(
                    f"⚠️ [ORKA-WARNING] Execution completed with {len(self.error_telemetry['errors'])} errors",
                )
                self.error_telemetry["execution_status"] = "partial"
            else:
                self.error_telemetry["execution_status"] = "completed"

            # Enhance the result with error telemetry
            if isinstance(result, list):
                # Standard successful result - logs list
                enhanced_result = {
                    "status": "success",
                    "execution_logs": result,
                    "error_telemetry": self.error_telemetry,
                    "summary": self._get_execution_summary(result),
                }

                # Save the report even on success (with all telemetry)
                error_report_path = self.save_comprehensive_error_report(result)
                enhanced_result["report_path"] = error_report_path

                return enhanced_result
            else:
                # Already an error result from orchestrator
                result["error_telemetry"] = self.error_telemetry
                return result

        except Exception as critical_error:
            self.error_telemetry["execution_status"] = "failed" # Set status immediately on critical failure
            # Critical failure - save everything we have so far
            self.record_error(
                "critical_failure",
                "orchestrator",
                f"Critical orchestrator failure: {critical_error}",
                critical_error,
            )

            logger.info(f"💥 [ORKA-CRITICAL] Orchestrator failed: {critical_error}")

            # Try to get partial logs if possible
            try:
                if hasattr(self.orchestrator, "memory") and hasattr(
                    self.orchestrator.memory,
                    "memory",
                ):
                    logs = self.orchestrator.memory.memory[-50:]  # Get last 50 entries
            except Exception:
                logs = []

            error_report_path = self.save_comprehensive_error_report(logs, critical_error)

            # Try to cleanup memory backend
            try:
                self.orchestrator.memory.close()
            except Exception as cleanup_error:
                logger.info(f"⚠️ Failed to cleanup memory backend: {cleanup_error}")

            # Return error report for debugging instead of raising
            return {
                "status": "critical_failure",
                "error": str(critical_error),
                "error_report_path": error_report_path,
                "logs_captured": len(logs),
                "error_telemetry": self.error_telemetry,
                "traceback": traceback.format_exc(),
            }

    def _patch_orchestrator_for_error_tracking(self):
        """Add error tracking to orchestrator methods without breaking existing logic."""
        # This could be expanded to patch individual agent run methods
        # For now, we rely on the outer error handling

    def _get_execution_summary(self, logs):
        """Get a summary of the execution."""
        return {
            "total_agents_executed": len(logs),
            "total_errors": len(self.error_telemetry["errors"]),
            "total_retries": sum(self.error_telemetry["retry_counters"].values()),
            "execution_status": self.error_telemetry["execution_status"],
        }


# Enhanced orchestrator wrapper function
async def run_orchestrator_with_error_handling(orchestrator, input_data):
    """
    Enhanced wrapper function to run any orchestrator with comprehensive error handling.

    Usage:
        from orka.orchestrator_error_wrapper import run_orchestrator_with_error_handling

        orchestrator = Orchestrator("config.yml")
        result = await run_orchestrator_with_error_handling(orchestrator, input_data)
    """
    error_handler = OrkaErrorHandler(orchestrator)
    return await error_handler.run_with_error_handling(input_data)
