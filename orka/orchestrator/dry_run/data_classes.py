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

