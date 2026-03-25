# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Context Analyzer
================

Decomposes execution contexts into abstract, domain-agnostic features.

This is the key to cross-context skill transfer: by analyzing *what kind*
of problem we're facing (regardless of domain), we can find skills that
solved structurally similar problems in other domains.

Feature Categories
------------------

1. **Task Structure** — Is the task decomposable? Sequential? Parallel?
   Does it require aggregation? Comparison? Transformation?

2. **Input/Output Shape** — What kind of data flows in and out?
   Text? Structured data? Multiple inputs? Single output?

3. **Cognitive Pattern** — What kind of thinking is needed?
   Analysis? Synthesis? Evaluation? Generation? Classification?

4. **Complexity Signals** — How complex is the task?
   Number of steps, depth of reasoning, breadth of context needed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


# Abstract task structure types
TASK_STRUCTURES = [
    "decomposition",       # Break input into parts
    "sequential",          # Steps must happen in order
    "parallel",            # Steps can happen concurrently
    "aggregation",         # Combine multiple inputs into one output
    "comparison",          # Compare two or more items
    "transformation",      # Convert from one form to another
    "filtering",           # Select subset based on criteria
    "routing",             # Direct to different paths based on conditions
    "iteration",           # Repeat until convergence
    "validation",          # Check correctness
]

# Abstract cognitive patterns
COGNITIVE_PATTERNS = [
    "analysis",            # Break down and understand
    "synthesis",           # Combine into new whole
    "evaluation",          # Judge quality or correctness
    "generation",          # Create new content
    "classification",      # Categorize into groups
    "extraction",          # Pull specific info from larger context
    "reasoning",           # Draw conclusions from evidence
    "planning",            # Create action sequences
    "optimization",        # Improve existing solution
    "abstraction",         # Generalize from specific to general
]


@dataclass
class ContextFeatures:
    """Abstract features extracted from an execution context.

    These features describe *what kind* of problem we're facing without
    being tied to any specific domain, enabling cross-context matching.

    Attributes:
        task_structures: Which structural patterns apply.
        cognitive_patterns: What kinds of thinking are needed.
        input_shape: Abstract description of input (e.g., "single_text", "list").
        output_shape: Abstract description of expected output.
        complexity: Estimated complexity (1-10 scale).
        domain_hints: Domain-specific terms (for boosting in-domain matches).
        abstract_goal: One-sentence description of the goal in abstract terms.
        metadata: Additional context-specific information.
    """

    task_structures: list[str] = field(default_factory=list)
    cognitive_patterns: list[str] = field(default_factory=list)
    input_shape: str = "unknown"
    output_shape: str = "unknown"
    complexity: int = 5
    domain_hints: list[str] = field(default_factory=list)
    abstract_goal: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_structures": self.task_structures,
            "cognitive_patterns": self.cognitive_patterns,
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "complexity": self.complexity,
            "domain_hints": self.domain_hints,
            "abstract_goal": self.abstract_goal,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextFeatures:
        return cls(
            task_structures=data.get("task_structures", []),
            cognitive_patterns=data.get("cognitive_patterns", []),
            input_shape=data.get("input_shape", "unknown"),
            output_shape=data.get("output_shape", "unknown"),
            complexity=data.get("complexity", 5),
            domain_hints=data.get("domain_hints", []),
            abstract_goal=data.get("abstract_goal", ""),
            metadata=data.get("metadata", {}),
        )

    def to_embedding_text(self) -> str:
        """Convert to text suitable for vector embedding."""
        parts = [
            self.abstract_goal,
            f"structures: {', '.join(self.task_structures)}",
            f"patterns: {', '.join(self.cognitive_patterns)}",
            f"input: {self.input_shape}",
            f"output: {self.output_shape}",
        ]
        return " | ".join(parts)

    def fingerprint(self) -> str:
        """Create a stable hash for deduplication."""
        canonical = json.dumps(
            {
                "structures": sorted(self.task_structures),
                "patterns": sorted(self.cognitive_patterns),
                "input": self.input_shape,
                "output": self.output_shape,
                "goal": self.abstract_goal,
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def similarity_to(self, other: ContextFeatures) -> float:
        """Compute structural similarity to another context (0.0-1.0).

        Uses Jaccard similarity on task structures and cognitive patterns,
        plus exact matches on shapes.
        """
        score = 0.0
        total_weight = 0.0

        # Task structure similarity (weight: 0.35)
        s1 = set(self.task_structures)
        s2 = set(other.task_structures)
        if s1 or s2:
            jaccard = len(s1 & s2) / len(s1 | s2) if (s1 | s2) else 0.0
            score += 0.35 * jaccard
        total_weight += 0.35

        # Cognitive pattern similarity (weight: 0.35)
        p1 = set(self.cognitive_patterns)
        p2 = set(other.cognitive_patterns)
        if p1 or p2:
            jaccard = len(p1 & p2) / len(p1 | p2) if (p1 | p2) else 0.0
            score += 0.35 * jaccard
        total_weight += 0.35

        # Shape matches (weight: 0.15 each)
        if self.input_shape == other.input_shape:
            score += 0.15
        total_weight += 0.15

        if self.output_shape == other.output_shape:
            score += 0.15
        total_weight += 0.15

        return score / total_weight if total_weight > 0 else 0.0


class ContextAnalyzer:
    """Analyzes execution contexts and extracts abstract features.

    The analyzer can work in two modes:

    1. **Rule-based** (default) — Uses heuristics to detect task structures
       and cognitive patterns from the context description and metadata.

    2. **LLM-assisted** — Uses a language model to analyze the context
       and extract richer abstract features. Set ``llm_client`` to enable.
    """

    def __init__(self, llm_client: Any | None = None) -> None:
        self._llm = llm_client

    def analyze(self, context: dict[str, Any]) -> ContextFeatures:
        """Extract abstract features from a raw execution context.

        Args:
            context: Dictionary with keys like 'domain', 'task', 'input',
                     'description', 'agents', 'strategy', etc.

        Returns:
            ContextFeatures describing the abstract structure of the task.
        """
        features = ContextFeatures()

        # Extract text to analyze
        text = self._build_analysis_text(context)
        text_lower = text.lower()

        # Detect task structures from keywords and context
        features.task_structures = self._detect_task_structures(text_lower, context)
        features.cognitive_patterns = self._detect_cognitive_patterns(text_lower, context)
        features.input_shape = self._detect_input_shape(context)
        features.output_shape = self._detect_output_shape(context)
        features.complexity = self._estimate_complexity(context, features)
        features.domain_hints = self._extract_domain_hints(context)
        features.abstract_goal = self._generate_abstract_goal(context, features)
        features.metadata = {
            k: v for k, v in context.items()
            if k in ("domain", "task", "strategy")
        }

        return features

    def _build_analysis_text(self, context: dict[str, Any]) -> str:
        """Combine relevant context fields into analysis text."""
        parts = []
        for key in ("task", "description", "input", "prompt", "goal"):
            val = context.get(key)
            if val and isinstance(val, str):
                parts.append(val)
        return " ".join(parts)

    def _detect_task_structures(
        self, text: str, context: dict[str, Any]
    ) -> list[str]:
        """Detect which abstract task structures are present."""
        detected: list[str] = []

        structure_keywords: dict[str, list[str]] = {
            "decomposition": ["break down", "split", "decompose", "divide", "parts", "components"],
            "sequential": ["then", "step by step", "first", "next", "after", "sequence", "pipeline"],
            "parallel": ["simultaneously", "parallel", "concurrent", "fork", "at the same time"],
            "aggregation": ["combine", "merge", "aggregate", "join", "collect", "summarize"],
            "comparison": ["compare", "versus", "difference", "contrast", "better", "worse"],
            "transformation": ["convert", "transform", "translate", "map", "rewrite", "format"],
            "filtering": ["filter", "select", "extract", "pick", "remove", "exclude", "subset"],
            "routing": ["route", "direct", "if", "decide", "branch", "choose", "switch"],
            "iteration": ["repeat", "loop", "iterate", "until", "converge", "refine"],
            "validation": ["validate", "verify", "check", "confirm", "ensure", "test", "assess"],
        }

        for structure, keywords in structure_keywords.items():
            if any(kw in text for kw in keywords):
                detected.append(structure)

        # Also detect from orchestrator strategy
        strategy = context.get("strategy", "")
        if strategy == "parallel":
            if "parallel" not in detected:
                detected.append("parallel")
        elif strategy == "sequential":
            if "sequential" not in detected:
                detected.append("sequential")

        return detected

    def _detect_cognitive_patterns(
        self, text: str, context: dict[str, Any]
    ) -> list[str]:
        """Detect which cognitive patterns are needed."""
        detected: list[str] = []

        pattern_keywords: dict[str, list[str]] = {
            "analysis": ["analyze", "understand", "examine", "investigate", "break down", "study"],
            "synthesis": ["synthesize", "combine", "integrate", "build", "compose", "create from"],
            "evaluation": ["evaluate", "judge", "assess", "rate", "score", "quality", "review"],
            "generation": ["generate", "create", "write", "produce", "draft", "compose"],
            "classification": ["classify", "categorize", "label", "sort", "type", "group"],
            "extraction": ["extract", "find", "locate", "identify", "pull out", "retrieve"],
            "reasoning": ["reason", "deduce", "conclude", "infer", "logic", "because", "therefore"],
            "planning": ["plan", "schedule", "organize", "prioritize", "strategy", "roadmap"],
            "optimization": ["optimize", "improve", "enhance", "best", "efficient", "faster"],
            "abstraction": ["abstract", "generalize", "pattern", "principle", "concept"],
        }

        for pattern, keywords in pattern_keywords.items():
            if any(kw in text for kw in keywords):
                detected.append(pattern)

        return detected

    def _detect_input_shape(self, context: dict[str, Any]) -> str:
        """Detect the abstract shape of the input."""
        if "input" not in context:
            return "unknown"
        input_data = context["input"]
        if isinstance(input_data, list):
            return "list"
        if isinstance(input_data, dict):
            return "structured"
        if isinstance(input_data, str):
            if len(input_data) > 1000:
                return "long_text"
            return "single_text"
        return "unknown"

    def _detect_output_shape(self, context: dict[str, Any]) -> str:
        """Detect the abstract shape of the expected output."""
        output_hint = context.get("output_format", context.get("expected_output", ""))
        if isinstance(output_hint, str):
            hint_lower = output_hint.lower()
            if "json" in hint_lower or "structured" in hint_lower:
                return "structured"
            if "list" in hint_lower or "array" in hint_lower:
                return "list"
            if "bool" in hint_lower or "yes/no" in hint_lower:
                return "boolean"
            if "number" in hint_lower or "score" in hint_lower:
                return "numeric"
        return "text"

    def _estimate_complexity(
        self, context: dict[str, Any], features: ContextFeatures
    ) -> int:
        """Estimate task complexity on a 1-10 scale."""
        score = 3  # baseline

        # More structures = more complex
        score += min(len(features.task_structures), 3)
        # More cognitive patterns = more complex
        score += min(len(features.cognitive_patterns), 3)
        # Many agents = more complex
        agents = context.get("agents", [])
        if isinstance(agents, list) and len(agents) > 3:
            score += 1

        return min(10, max(1, score))

    def _extract_domain_hints(self, context: dict[str, Any]) -> list[str]:
        """Extract domain-specific hints for boosting in-domain matches."""
        hints: list[str] = []
        domain = context.get("domain")
        if domain:
            hints.append(str(domain))
        task = context.get("task")
        if task:
            hints.append(str(task))
        return hints

    def _generate_abstract_goal(
        self, context: dict[str, Any], features: ContextFeatures
    ) -> str:
        """Generate a one-sentence abstract description of the goal."""
        parts = []

        if features.cognitive_patterns:
            parts.append(f"Apply {' and '.join(features.cognitive_patterns[:2])}")

        if features.task_structures:
            parts.append(f"using {' and '.join(features.task_structures[:2])}")

        parts.append(f"on {features.input_shape} input")
        parts.append(f"producing {features.output_shape} output")

        return " ".join(parts)
