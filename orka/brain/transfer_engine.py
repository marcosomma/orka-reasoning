# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Skill Transfer Engine
=====================

The core intelligence of the Brain. Finds skills learned in one context
and adapts them for use in a completely different context.

Transfer Process
----------------

1. **Context Analysis** — Extract abstract features from the new context.
2. **Candidate Discovery** — Find skills whose features are similar:
   - Semantic search via embeddings (captures meaning)
   - Structural matching via ContextFeatures (captures shape)
   - Graph traversal via SkillGraph (captures relationships)
3. **Applicability Scoring** — Score each candidate on:
   - Structural similarity (how similar the task shapes are)
   - Semantic similarity (how similar the descriptions are)
   - Transfer track record (has this skill transferred before?)
   - Confidence (how reliable is this skill overall?)
4. **Adaptation** — For the best candidates, describe what adjustments
   are needed to apply the skill in the new context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .context_analyzer import ContextAnalyzer, ContextFeatures
from .skill import Skill
from .skill_graph import SkillGraph

logger = logging.getLogger(__name__)


@dataclass
class TransferCandidate:
    """A skill that might be applicable in a new context.

    Attributes:
        skill: The candidate skill.
        structural_score: How well the task structures match (0.0-1.0).
        semantic_score: How semantically similar the contexts are (0.0-1.0).
        transfer_score: How well this skill has transferred in the past (0.0-1.0).
        confidence_score: The skill's overall confidence (0.0-1.0).
        combined_score: Weighted combination of all scores (0.0-1.0).
        adaptations: Suggested modifications for the new context.
        reasoning: Human-readable explanation of why this skill fits.
    """

    skill: Skill
    structural_score: float = 0.0
    semantic_score: float = 0.0
    transfer_score: float = 0.0
    confidence_score: float = 0.0
    combined_score: float = 0.0
    adaptations: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


class SkillTransferEngine:
    """Finds and adapts skills for cross-context application.

    The engine is the heart of the Brain's ability to learn in one domain
    and apply in another. It combines multiple matching strategies to find
    the best skills and scores them on applicability.

    Args:
        skill_graph: The skill knowledge graph.
        context_analyzer: Analyzer for extracting context features.
        embedder: Optional sentence embedding model for semantic search.
            If not provided, only structural matching is used.

    Scoring Weights:
        - structural: 0.35 — How similar the task shapes are
        - semantic: 0.25 — How similar the descriptions are
        - transfer: 0.25 — How well the skill has transferred before
        - confidence: 0.15 — How reliable the skill is overall
    """

    WEIGHT_STRUCTURAL = 0.35
    WEIGHT_SEMANTIC = 0.25
    WEIGHT_TRANSFER = 0.25
    WEIGHT_CONFIDENCE = 0.15

    def __init__(
        self,
        skill_graph: SkillGraph,
        context_analyzer: ContextAnalyzer | None = None,
        embedder: Any | None = None,
    ) -> None:
        self._graph = skill_graph
        self._analyzer = context_analyzer or ContextAnalyzer()
        self._embedder = embedder

    def find_transferable_skills(
        self,
        target_context: dict[str, Any],
        top_k: int = 5,
        min_score: float = 0.3,
        skill_types: list[str] | None = None,
        domain_filter: str | None = None,
    ) -> list[TransferCandidate]:
        """Find skills that could apply to a new context.

        This is the main entry point. It:
        1. Analyzes the target context into abstract features
        2. Retrieves candidate skills (optionally pre-filtered by type/domain)
        3. Scores each skill's transferability
        4. Returns the top candidates above the threshold

        Args:
            target_context: Dictionary describing the new execution context.
            top_k: Maximum number of candidates to return.
            min_score: Minimum combined score to be considered (0.0-1.0).
            skill_types: Optional list of skill type values to pre-filter
                (e.g. ``["execution_recipe", "graph_path"]``).
            domain_filter: Optional domain keyword to pre-filter.

        Returns:
            List of TransferCandidate objects, sorted by score descending.
        """
        target_features = self._analyzer.analyze(target_context)

        # Two-stage retrieval: narrow first if filters provided
        if skill_types or domain_filter:
            all_skills: list[Skill] = []
            if skill_types:
                for st in skill_types:
                    all_skills.extend(self._graph.find_by_type(st))
                if domain_filter:
                    # Intersect with domain
                    domain_ids = {s.id for s in self._graph.find_by_domain(domain_filter)}
                    all_skills = [s for s in all_skills if s.id in domain_ids]
            elif domain_filter:
                all_skills = self._graph.find_by_domain(domain_filter)
            # Deduplicate
            seen: set[str] = set()
            unique: list[Skill] = []
            for s in all_skills:
                if s.id not in seen:
                    seen.add(s.id)
                    unique.append(s)
            all_skills = unique
        else:
            all_skills = self._graph.list_skills()

        if not all_skills:
            logger.debug("No skills in graph, nothing to transfer")
            return []

        # Score each skill
        candidates: list[TransferCandidate] = []
        for skill in all_skills:
            candidate = self._score_skill(skill, target_features, target_context)
            if candidate.combined_score >= min_score:
                candidates.append(candidate)

        # Sort by combined score, descending
        candidates.sort(key=lambda c: c.combined_score, reverse=True)

        return candidates[:top_k]

    def _score_skill(
        self,
        skill: Skill,
        target_features: ContextFeatures,
        target_context: dict[str, Any],
    ) -> TransferCandidate:
        """Score a single skill's applicability to a target context.

        Args:
            skill: The skill to evaluate.
            target_features: Abstract features of the target context.
            target_context: Raw target context dictionary.

        Returns:
            A scored TransferCandidate.
        """
        # 1. Structural similarity
        source_features = ContextFeatures.from_dict(skill.source_context)
        structural = target_features.similarity_to(source_features)

        # 2. Semantic similarity (via embeddings if available)
        semantic = self._compute_semantic_similarity(skill, target_features)

        # Semantic floor — if content is unrelated, don't transfer
        if semantic < 0.1 and structural < 0.6:
            return TransferCandidate(
                skill=skill,
                structural_score=structural,
                semantic_score=semantic,
                transfer_score=0.0,
                confidence_score=0.0,
                combined_score=0.0,
                adaptations={},
                reasoning="Filtered: semantic similarity too low for meaningful transfer.",
            )

        # 3. Transfer track record
        transfer = skill.transfer_success_rate if skill.transfer_history else 0.5

        # 4. Confidence
        confidence = skill.confidence

        # Combined weighted score
        combined = (
            self.WEIGHT_STRUCTURAL * structural
            + self.WEIGHT_SEMANTIC * semantic
            + self.WEIGHT_TRANSFER * transfer
            + self.WEIGHT_CONFIDENCE * confidence
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(skill, target_features, structural, semantic, transfer)

        # Suggest adaptations
        adaptations = self._suggest_adaptations(skill, source_features, target_features)

        return TransferCandidate(
            skill=skill,
            structural_score=structural,
            semantic_score=semantic,
            transfer_score=transfer,
            confidence_score=confidence,
            combined_score=combined,
            adaptations=adaptations,
            reasoning=reasoning,
        )

    def _compute_semantic_similarity(self, skill: Skill, target_features: ContextFeatures) -> float:
        """Compute semantic similarity between a skill and target context.

        Uses vector embeddings if an embedder is available, otherwise
        falls back to keyword overlap.
        """
        if self._embedder is not None:
            try:
                skill_text = skill.to_embedding_text()
                target_text = target_features.to_embedding_text()
                skill_vec = self._embedder.encode(skill_text)
                target_vec = self._embedder.encode(target_text)
                # Cosine similarity
                import numpy as np

                dot = float(np.dot(skill_vec, target_vec))
                norm = float(np.linalg.norm(skill_vec) * np.linalg.norm(target_vec))
                if norm == 0:
                    return 0.0
                similarity = dot / norm
                # Normalize from [-1, 1] to [0, 1]
                return max(0.0, (similarity + 1.0) / 2.0)
            except Exception:
                logger.debug("Embedder failed, falling back to keyword overlap")

        # Fallback: keyword overlap
        return self._keyword_similarity(skill, target_features)

    def _keyword_similarity(self, skill: Skill, target_features: ContextFeatures) -> float:
        """Simple keyword overlap similarity as a fallback."""
        skill_words = set(skill.to_embedding_text().lower().split())
        target_words = set(target_features.to_embedding_text().lower().split())

        if not skill_words or not target_words:
            return 0.0

        overlap = skill_words & target_words
        union = skill_words | target_words
        return len(overlap) / len(union) if union else 0.0

    def _generate_reasoning(
        self,
        skill: Skill,
        target_features: ContextFeatures,
        structural: float,
        semantic: float,
        transfer: float,
    ) -> str:
        """Generate a human-readable explanation of why this skill fits."""
        parts = [f"Skill '{skill.name}'"]

        if structural > 0.7:
            parts.append("has very similar task structure")
        elif structural > 0.4:
            parts.append("shares some structural patterns")

        if semantic > 0.7:
            parts.append("is semantically close")
        elif semantic > 0.4:
            parts.append("has moderate semantic overlap")

        if skill.transfer_history:
            n = len(skill.transfer_history)
            rate = skill.transfer_success_rate
            parts.append(f"has been transferred {n} times ({rate:.0%} success)")

        # Matching structures
        source_features = ContextFeatures.from_dict(skill.source_context)
        common_structures = set(source_features.task_structures) & set(target_features.task_structures)
        if common_structures:
            parts.append(f"shares structures: {', '.join(common_structures)}")

        common_patterns = set(source_features.cognitive_patterns) & set(target_features.cognitive_patterns)
        if common_patterns:
            parts.append(f"shares patterns: {', '.join(common_patterns)}")

        return ". ".join(parts) + "."

    def _suggest_adaptations(
        self,
        skill: Skill,
        source_features: ContextFeatures,
        target_features: ContextFeatures,
    ) -> dict[str, Any]:
        """Suggest how to adapt the skill's procedure for the new context.

        Identifies differences between source and target contexts and
        proposes modifications to skill steps.
        """
        adaptations: dict[str, Any] = {}

        # Shape adaptations
        if source_features.input_shape != target_features.input_shape:
            adaptations["input_adaptation"] = {
                "from": source_features.input_shape,
                "to": target_features.input_shape,
                "suggestion": f"Adapt input handling from {source_features.input_shape} to {target_features.input_shape}",
            }

        if source_features.output_shape != target_features.output_shape:
            adaptations["output_adaptation"] = {
                "from": source_features.output_shape,
                "to": target_features.output_shape,
                "suggestion": f"Adapt output format from {source_features.output_shape} to {target_features.output_shape}",
            }

        # Structure adaptations
        missing_structures = set(target_features.task_structures) - set(source_features.task_structures)
        extra_structures = set(source_features.task_structures) - set(target_features.task_structures)

        if missing_structures:
            adaptations["add_structures"] = list(missing_structures)
        if extra_structures:
            adaptations["remove_structures"] = list(extra_structures)

        # Complexity adaptation
        if abs(source_features.complexity - target_features.complexity) > 2:
            if target_features.complexity > source_features.complexity:
                adaptations["complexity"] = "Target is more complex — may need additional steps"
            else:
                adaptations["complexity"] = "Target is simpler — some steps may be unnecessary"

        return adaptations
