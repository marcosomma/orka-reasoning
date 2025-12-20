# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Data Classes for Path Evaluation
================================

Structured results for LLM-powered path evaluation and validation.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PathEvaluation:
    """Result of LLM path evaluation."""

    node_id: str
    relevance_score: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    reasoning: str
    expected_output: str
    estimated_tokens: int
    estimated_cost: float
    estimated_latency_ms: int
    risk_factors: List[str]
    efficiency_rating: str  # "high", "medium", "low"


@dataclass
class ValidationResult:
    """Result of LLM validation."""

    is_valid: bool
    confidence: float
    efficiency_score: float  # 0.0 - 1.0
    validation_reasoning: str
    suggested_improvements: List[str]
    risk_assessment: str

