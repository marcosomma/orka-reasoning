# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import json
import os
from datetime import datetime


class ErrorReporter:
    """
    Handles error report generation and persistence.
    Creates comprehensive error reports for debugging and analysis.
    """

    def __init__(self, run_id, memory_backend=None):
        """
        Initialize error reporter.

        Args:
            run_id: Unique identifier for the current run
            memory_backend: Memory backend instance for capturing snapshots
        """
        self.run_id = run_id
        self.memory_backend = memory_backend

    def save_error_report(self, logs, error_telemetry, meta_report=None, final_error=None):
        """
        Save comprehensive error report with all logged data up to the failure point.

        Args:
            logs: Execution logs
            error_telemetry: Error telemetry data
            meta_report: Meta report data (optional)
            final_error: Final error that caused failure (optional)

        Returns:
            str: Path to the saved error report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Determine final execution status
        execution_status = error_telemetry.get("execution_status", "unknown")
        if final_error:
            execution_status = "failed"
        elif error_telemetry.get("errors"):
            execution_status = "partial"
        else:
            execution_status = "completed"

        # Create comprehensive error report
        error_report = {
            "orka_execution_report": {
                "run_id": self.run_id,
                "timestamp": timestamp,
                "execution_status": execution_status,
                "error_telemetry": error_telemetry,
                "meta_report": meta_report or {"error": "Meta report not available"},
                "execution_logs": logs,
                "total_steps_attempted": len(logs),
                "total_errors": len(error_telemetry.get("errors", [])),
                "total_retries": sum(error_telemetry.get("retry_counters", {}).values()),
                "agents_with_errors": list(
                    set(error["agent_id"] for error in error_telemetry.get("errors", [])),
                ),
                "memory_snapshot": self._capture_memory_snapshot(),
                "final_error": str(final_error) if final_error else None,
            },
        }

        # Save error report
        error_report_path = os.path.join(log_dir, f"orka_error_report_{timestamp}.json")
        try:
            with open(error_report_path, "w") as f:
                json.dump(error_report, f, indent=2, default=str)
            print(f"📋 Error report saved: {error_report_path}")
        except Exception as e:
            print(f"❌ Failed to save error report: {e}")

        return error_report_path

    def save_trace_to_memory_backend(self, logs):
        """
        Save execution trace to memory backend.

        Args:
            logs: Execution logs to save

        Returns:
            str: Path to the saved trace file
        """
        if not self.memory_backend:
            print("⚠️ No memory backend available for trace saving")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        try:
            trace_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
            self.memory_backend.save_to_file(trace_path)
            print(f"📋 Execution trace saved: {trace_path}")
            return trace_path
        except Exception as e:
            print(f"⚠️ Failed to save trace to memory backend: {e}")
            return None

    def _capture_memory_snapshot(self):
        """Capture current state of memory backend for debugging."""
        if not self.memory_backend:
            return {"status": "no_memory_backend"}

        try:
            if hasattr(self.memory_backend, "memory") and self.memory_backend.memory:
                return {
                    "total_entries": len(self.memory_backend.memory),
                    "last_10_entries": self.memory_backend.memory[-10:]
                    if len(self.memory_backend.memory) >= 10
                    else self.memory_backend.memory,
                    "backend_type": type(self.memory_backend).__name__,
                }
        except Exception as e:
            return {"error": f"Failed to capture memory snapshot: {e}"}
        return {"status": "no_memory_data"}

    def generate_error_summary_report(self, error_telemetry):
        """
        Generate a summary report of errors for quick analysis.

        Args:
            error_telemetry: Error telemetry data

        Returns:
            dict: Summary report
        """
        errors = error_telemetry.get("errors", [])

        # Group errors by type
        error_types = {}
        for error in errors:
            error_type = error.get("type", "unknown")
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)

        # Group errors by agent
        agent_errors = {}
        for error in errors:
            agent_id = error.get("agent_id", "unknown")
            if agent_id not in agent_errors:
                agent_errors[agent_id] = []
            agent_errors[agent_id].append(error)

        # Calculate error rates
        total_errors = len(errors)
        unique_agents_with_errors = len(agent_errors)

        return {
            "summary": {
                "total_errors": total_errors,
                "unique_error_types": len(error_types),
                "agents_with_errors": unique_agents_with_errors,
                "execution_status": error_telemetry.get("execution_status", "unknown"),
            },
            "error_breakdown_by_type": {
                error_type: len(error_list) for error_type, error_list in error_types.items()
            },
            "error_breakdown_by_agent": {
                agent_id: len(error_list) for agent_id, error_list in agent_errors.items()
            },
            "most_problematic_agents": sorted(
                agent_errors.items(),
                key=lambda x: len(x[1]),
                reverse=True,
            )[:5],  # Top 5 agents with most errors
            "retry_statistics": error_telemetry.get("retry_counters", {}),
            "recovery_actions": len(error_telemetry.get("recovery_actions", [])),
        }

    def format_error_for_display(self, error):
        """
        Format an error entry for human-readable display.

        Args:
            error: Error entry dictionary

        Returns:
            str: Formatted error string
        """
        timestamp = error.get("timestamp", "unknown")
        error_type = error.get("type", "unknown")
        agent_id = error.get("agent_id", "unknown")
        message = error.get("message", "No message")
        severity = error.get("severity", "medium")

        severity_emoji = {
            "low": "⚠️",
            "medium": "🚨",
            "high": "💥",
            "critical": "🔥",
        }
        emoji = severity_emoji.get(severity, "🚨")

        formatted = f"{emoji} [{timestamp}] {error_type.upper()} in {agent_id}: {message}"

        if error.get("exception"):
            exception_info = error["exception"]
            formatted += f"\n   Exception: {exception_info.get('type', 'Unknown')} - {exception_info.get('message', 'No details')}"

        if error.get("recovery_action"):
            formatted += f"\n   Recovery: {error['recovery_action']}"

        return formatted
