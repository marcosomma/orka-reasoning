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
Metrics Collection for GraphScout Operations
=============================================

Structured metrics collection for monitoring and debugging GraphScout
path discovery and evaluation.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class GraphScoutMetrics:
    """Metrics for a GraphScout execution."""
    
    run_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Path discovery metrics
    candidates_discovered: int = 0
    candidates_after_budget: int = 0
    candidates_after_safety: int = 0
    
    # Evaluation metrics
    llm_evaluation_time_ms: float = 0.0
    llm_evaluation_failed: bool = False
    used_deterministic_fallback: bool = False
    
    # Scoring metrics
    final_scores: Dict[str, float] = field(default_factory=dict)
    selected_path: List[str] = field(default_factory=list)
    selection_confidence: float = 0.0
    selection_reasoning: str = ""
    
    # Performance metrics
    total_time_ms: float = 0.0
    budget_filter_time_ms: float = 0.0
    safety_filter_time_ms: float = 0.0
    scoring_time_ms: float = 0.0
    decision_time_ms: float = 0.0
    
    # Resource usage
    estimated_total_cost: float = 0.0
    estimated_total_latency_ms: int = 0
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dict for logging."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "path_discovery": {
                "candidates_discovered": self.candidates_discovered,
                "candidates_after_budget": self.candidates_after_budget,
                "candidates_after_safety": self.candidates_after_safety,
                "reduction_rate": self._calculate_reduction_rate()
            },
            "evaluation": {
                "llm_evaluation_time_ms": self.llm_evaluation_time_ms,
                "llm_evaluation_failed": self.llm_evaluation_failed,
                "used_deterministic_fallback": self.used_deterministic_fallback
            },
            "selection": {
                "selected_path": self.selected_path,
                "confidence": self.selection_confidence,
                "reasoning_preview": self.selection_reasoning[:100] if self.selection_reasoning else ""
            },
            "performance": {
                "total_time_ms": self.total_time_ms,
                "breakdown": {
                    "budget_filter_ms": self.budget_filter_time_ms,
                    "safety_filter_ms": self.safety_filter_time_ms,
                    "scoring_ms": self.scoring_time_ms,
                    "decision_ms": self.decision_time_ms
                }
            },
            "resources": {
                "estimated_cost_usd": self.estimated_total_cost,
                "estimated_latency_ms": self.estimated_total_latency_ms
            },
            "issues": {
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
                "errors": self.errors,
                "warnings": self.warnings
            }
        }
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def _calculate_reduction_rate(self) -> float:
        """Calculate candidate reduction rate through filtering."""
        if self.candidates_discovered == 0:
            return 0.0
        remaining = self.candidates_after_safety
        return 1.0 - (remaining / self.candidates_discovered)
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
    
    def summary(self) -> str:
        """Generate a one-line summary."""
        return (
            f"GraphScout[{self.run_id}]: "
            f"{self.candidates_discovered} candidates -> {len(self.selected_path)} selected "
            f"in {self.total_time_ms:.0f}ms "
            f"(confidence: {self.selection_confidence:.2f}, "
            f"fallback: {self.used_deterministic_fallback})"
        )


@dataclass
class PathExecutorMetrics:
    """Metrics for PathExecutor execution."""
    
    run_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Execution metrics
    planned_path: List[str] = field(default_factory=list)
    executed_path: List[str] = field(default_factory=list)
    successful_agents: int = 0
    failed_agents: int = 0
    skipped_agents: int = 0
    
    # Timing
    total_execution_time_ms: float = 0.0
    agent_execution_times: Dict[str, float] = field(default_factory=dict)
    
    # Results
    agent_statuses: Dict[str, str] = field(default_factory=dict)  # agent_id -> "success"|"failed"|"skipped"
    error_messages: Dict[str, str] = field(default_factory=dict)  # agent_id -> error_message
    
    def to_dict(self) -> Dict:
        """Convert to dict for logging."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "execution": {
                "planned_path": self.planned_path,
                "executed_path": self.executed_path,
                "completion_rate": self._calculate_completion_rate()
            },
            "results": {
                "successful": self.successful_agents,
                "failed": self.failed_agents,
                "skipped": self.skipped_agents,
                "agent_statuses": self.agent_statuses
            },
            "performance": {
                "total_time_ms": self.total_execution_time_ms,
                "average_agent_time_ms": self._calculate_average_time(),
                "agent_times": self.agent_execution_times
            },
            "errors": self.error_messages
        }
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def _calculate_completion_rate(self) -> float:
        """Calculate path completion rate."""
        if not self.planned_path:
            return 0.0
        return len(self.executed_path) / len(self.planned_path)
    
    def _calculate_average_time(self) -> float:
        """Calculate average agent execution time."""
        if not self.agent_execution_times:
            return 0.0
        return sum(self.agent_execution_times.values()) / len(self.agent_execution_times)
    
    def summary(self) -> str:
        """Generate a one-line summary."""
        return (
            f"PathExecutor[{self.run_id}]: "
            f"{len(self.executed_path)}/{len(self.planned_path)} agents executed "
            f"in {self.total_execution_time_ms:.0f}ms "
            f"({self.successful_agents} success, {self.failed_agents} failed)"
        )

