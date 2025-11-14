# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Structured Logging for OrKa
============================

Structured logging utilities for consistent, parseable logs across
the OrKa orchestration system.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredLogger:
    """Logger that outputs structured JSON logs for better observability."""
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__ from calling module)
        """
        self.logger = logging.getLogger(name)
        self.component = name.split(".")[-1]  # Extract component name
    
    def log_event(
        self,
        level: int,
        event_type: str,
        message: str = "",
        **context: Any
    ):
        """
        Log a structured event.
        
        Args:
            level: Logging level (logging.INFO, logging.ERROR, etc.)
            event_type: Type of event (e.g., "graphscout_decision", "path_execution")
            message: Human-readable message
            **context: Additional context as key-value pairs
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "component": self.component,
            "event_type": event_type,
            "message": message,
            **context
        }
        
        # Log as JSON string for parsing by log aggregators
        self.logger.log(level, json.dumps(log_entry))
    
    def log_graphscout_decision(
        self,
        decision_type: str,
        target: list,
        confidence: float,
        run_id: str,
        **context
    ):
        """Log GraphScout routing decision."""
        self.log_event(
            logging.INFO,
            "graphscout_decision",
            message=f"GraphScout selected {len(target)} agents with {confidence:.2f} confidence",
            decision_type=decision_type,
            target=target,
            confidence=confidence,
            run_id=run_id,
            **context
        )
    
    def log_path_execution(
        self,
        path: list,
        status: str,
        run_id: str,
        execution_time_ms: float,
        **context
    ):
        """Log path execution completion."""
        self.log_event(
            logging.INFO,
            "path_execution",
            message=f"Executed {len(path)} agents in {execution_time_ms:.0f}ms: {status}",
            path=path,
            status=status,
            run_id=run_id,
            execution_time_ms=execution_time_ms,
            **context
        )
    
    def log_validation_result(
        self,
        path: list,
        score: float,
        passed: bool,
        run_id: str,
        **context
    ):
        """Log validation result."""
        self.log_event(
            logging.INFO,
            "validation_result",
            message=f"Path validation: {score:.3f} ({'PASSED' if passed else 'FAILED'})",
            path=path,
            score=score,
            passed=passed,
            run_id=run_id,
            **context
        )
    
    def log_llm_fallback(
        self,
        reason: str,
        fallback_type: str,
        run_id: str,
        **context
    ):
        """Log LLM fallback event."""
        self.log_event(
            logging.WARNING,
            "llm_fallback",
            message=f"LLM failed ({reason}), using {fallback_type} fallback",
            reason=reason,
            fallback_type=fallback_type,
            run_id=run_id,
            **context
        )
    
    def log_agent_error(
        self,
        agent_id: str,
        error: str,
        run_id: str,
        **context
    ):
        """Log agent execution error."""
        self.log_event(
            logging.ERROR,
            "agent_error",
            message=f"Agent {agent_id} failed: {error}",
            agent_id=agent_id,
            error=error,
            run_id=run_id,
            **context
        )
    
    def log_performance_metrics(
        self,
        operation: str,
        duration_ms: float,
        run_id: str,
        **metrics
    ):
        """Log performance metrics."""
        self.log_event(
            logging.DEBUG,
            "performance_metrics",
            message=f"{operation} completed in {duration_ms:.2f}ms",
            operation=operation,
            duration_ms=duration_ms,
            run_id=run_id,
            **metrics
        )
    
    def log_configuration(
        self,
        config_name: str,
        config_values: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        """Log configuration settings."""
        context = {"config_name": config_name, "config": config_values}
        if run_id:
            context["run_id"] = run_id
        
        self.log_event(
            logging.DEBUG,
            "configuration",
            message=f"Configuration loaded: {config_name}",
            **context
        )
    
    # Convenience methods for common log levels
    
    def info(self, message: str, **context):
        """Log info level message."""
        self.log_event(logging.INFO, "info", message=message, **context)
    
    def warning(self, message: str, **context):
        """Log warning level message."""
        self.log_event(logging.WARNING, "warning", message=message, **context)
    
    def error(self, message: str, **context):
        """Log error level message."""
        self.log_event(logging.ERROR, "error", message=message, **context)
    
    def debug(self, message: str, **context):
        """Log debug level message."""
        self.log_event(logging.DEBUG, "debug", message=message, **context)

