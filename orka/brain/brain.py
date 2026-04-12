# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Brain — Executional Learning Engine
====================================

The Brain is the top-level orchestrator of the learning-and-transfer cycle.
It ties together the SkillGraph, ContextAnalyzer, and SkillTransferEngine
to provide a complete learn → recall → execute → feedback loop.

Lifecycle
---------

1. **Execute** — Run a task. The Brain first recalls relevant skills,
   adapts them to the current context, and uses them to guide execution.

2. **Observe** — After execution, the Brain observes the outcome
   (success/failure, quality metrics, execution trace).

3. **Learn** — From successful executions, the Brain abstracts new skills
   or reinforces existing ones. It stores abstract procedures, not
   domain-specific implementations.

4. **Transfer** — When facing a new task in a different domain, the Brain
   recognizes structural and semantic similarities to known skills and
   adapts them for the new context.

This cycle is continuous. Each execution makes the Brain smarter,
and skills improve with every successful transfer.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from .context_analyzer import ContextAnalyzer, ContextFeatures
from .constants import ACTION_VERB_CANONICAL
from .skill import Skill, SkillCondition, SkillStep, SkillTransferRecord, SkillType, generate_search_tokens
from .skill_graph import SkillGraph
from .transfer_engine import SkillTransferEngine, TransferCandidate

logger = logging.getLogger(__name__)

_CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour


class Brain:
    """The executional learning engine.

    The Brain learns skills from successful executions and re-applies them
    in completely different contexts. It uses Redis-backed memory for persistence,
    vector embeddings for semantic matching, and a knowledge graph for skill
    relationships.

    Args:
        memory: A memory logger (RedisStackMemoryLogger or compatible) for persistence.
        embedder: Optional sentence embedding model for semantic skill matching.
        llm_client: Optional LLM client for advanced context analysis and
            skill abstraction (if not provided, uses rule-based heuristics).

    Example:
        .. code-block:: python

            from orka.brain import Brain

            brain = Brain(memory=memory_logger)

            # Learn from a successful execution
            skill = await brain.learn(
                execution_trace={
                    "agents": ["analyzer", "summarizer"],
                    "strategy": "sequential",
                    "steps": [
                        {"action": "decompose input", "result": "success"},
                        {"action": "process each part", "result": "success"},
                        {"action": "aggregate results", "result": "success"},
                    ],
                },
                context={"domain": "text_analysis", "task": "summarization"},
                outcome={"success": True, "quality": 0.95},
            )

            # Recall skills for a different context
            candidates = await brain.recall(
                context={"domain": "code_review", "task": "identify key changes"},
            )

            # Provide feedback after using a skill
            await brain.feedback(
                skill_id=skill.id,
                context={"domain": "code_review"},
                success=True,
            )
    """

    def __init__(
        self,
        memory: Any,
        embedder: Any | None = None,
        llm_client: Any | None = None,
    ) -> None:
        self._memory = memory
        self._embedder = embedder
        self._llm = llm_client

        # Core components
        self._analyzer = ContextAnalyzer(llm_client=llm_client)
        self._graph = SkillGraph(memory=memory)
        self._transfer = SkillTransferEngine(
            skill_graph=self._graph,
            context_analyzer=self._analyzer,
            embedder=embedder,
        )
        self._last_cleanup: datetime = datetime.now(UTC)

    @property
    def skill_graph(self) -> SkillGraph:
        """Access the underlying skill graph."""
        return self._graph

    @property
    def context_analyzer(self) -> ContextAnalyzer:
        """Access the context analyzer."""
        return self._analyzer

    @property
    def transfer_engine(self) -> SkillTransferEngine:
        """Access the transfer engine."""
        return self._transfer

    # ========== Learn ==========

    async def learn(
        self,
        execution_trace: dict[str, Any],
        context: dict[str, Any],
        outcome: dict[str, Any],
        skill_name: str | None = None,
    ) -> Skill | None:
        """Learn a new skill from a successful execution.

        Analyzes the execution trace and context to extract an abstract,
        transferable skill. Only learns from successful outcomes.

        Args:
            execution_trace: Record of what happened during execution.
                Expected keys: 'steps' (list of action dicts), 'agents' (list),
                'strategy' (str), 'duration_ms' (int).
            context: The execution context (domain, task, input description, etc.).
            outcome: Execution outcome. Must contain 'success' (bool).
                Optional: 'quality' (float 0-1), 'error' (str).
            skill_name: Optional name for the skill. If not provided,
                one is generated from the context.

        Returns:
            The newly created Skill, or None if the outcome was not successful
            or no skill could be abstracted.
        """
        # Analyze context early so we can look up existing skills
        features = self._analyzer.analyze(context)
        name = skill_name or self._generate_skill_name(features)
        success = outcome.get("success", False)

        # Check for existing similar skill — record both successes AND failures
        existing = self._find_existing_skill(features, name)
        if existing:
            existing.record_usage(success=bool(success))
            self._graph.save_skill(existing)
            if success:
                logger.info(f"Reinforced existing skill '{existing.name}' ({existing.id})")
            else:
                logger.info(f"Recorded failure for skill '{existing.name}' ({existing.id})")
            return existing

        if not success:
            logger.debug("Outcome was not successful, not learning")
            return None

        # Extract abstract procedure from execution trace
        procedure = self._extract_procedure(execution_trace)
        if not procedure:
            logger.debug("Could not extract procedure from trace")
            return None

        # Extract conditions
        preconditions = self._extract_preconditions(features, execution_trace)
        postconditions = self._extract_postconditions(features, outcome)

        # Generate description
        description = self._generate_description(features, procedure)

        # Generate tags
        tags = list(set(features.task_structures + features.cognitive_patterns + features.domain_hints))

        # Create new skill
        skill = Skill(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            skill_type=SkillType.PROCEDURAL.value,
            procedure=procedure,
            preconditions=preconditions,
            postconditions=postconditions,
            source_context=features.to_dict(),
            confidence=min(0.7, 0.5 + outcome.get("quality", 0.5) * 0.2),
            success_rate=1.0,
            usage_count=1,
            tags=tags,
            task_description=context.get("task", ""),
            domain_keywords=features.domain_hints or [context.get("domain", "general")],
            output_description=context.get("output_format", ""),
            search_tokens=generate_search_tokens(name),
        )
        skill.renew_ttl()

        # Save to graph
        self._graph.save_skill(skill)
        logger.info(f"Learned new skill '{skill.name}' ({skill.id})")

        # Log to memory for traceability
        self._log_learning_event(skill, context, outcome)

        return skill

    # ========== Recall ==========

    async def recall(
        self,
        context: dict[str, Any],
        top_k: int = 5,
        min_score: float = 0.3,
        skill_types: list[str] | None = None,
        domain_filter: str | None = None,
    ) -> list[TransferCandidate]:
        """Recall skills that might apply to a new context.

        Searches the skill graph for skills that structurally and
        semantically match the given context, even if they were learned
        in a completely different domain.

        Args:
            context: The new execution context.
            top_k: Maximum number of candidates to return.
            min_score: Minimum applicability score (0.0-1.0).
            skill_types: Optional list of :class:`SkillType` values to
                restrict retrieval (two-stage filter).
            domain_filter: Optional domain keyword to pre-filter.

        Returns:
            List of TransferCandidate objects, ranked by applicability.
        """
        candidates = self._transfer.find_transferable_skills(
            target_context=context,
            top_k=top_k,
            min_score=min_score,
            skill_types=skill_types,
            domain_filter=domain_filter,
        )

        # Lazy cleanup: run at most once per hour
        now = datetime.now(UTC)
        if (now - self._last_cleanup).total_seconds() >= _CLEANUP_INTERVAL_SECONDS:
            self._graph.cleanup_expired_skills()
            self._last_cleanup = now

        if candidates:
            logger.info(
                f"Recalled {len(candidates)} applicable skills for context "
                f"(top: '{candidates[0].skill.name}', score: {candidates[0].combined_score:.2f})"
            )
        else:
            logger.debug("No applicable skills found for context")

        return candidates

    # ========== Feedback ==========

    async def feedback(
        self,
        skill_id: str,
        context: dict[str, Any],
        success: bool,
        adaptations: dict[str, Any] | None = None,
    ) -> None:
        """Provide feedback after applying a skill in a new context.

        This is how the Brain learns about cross-context transfer.
        Successful transfers increase the skill's confidence and
        transfer track record. Failures decrease confidence.

        Args:
            skill_id: The skill that was applied.
            context: The context where it was applied.
            success: Whether the application was successful.
            adaptations: What modifications were made (if any).
        """
        skill = self._graph.get_skill(skill_id)
        if skill is None:
            logger.warning(f"Skill {skill_id} not found for feedback")
            return

        features = self._analyzer.analyze(context)

        record = SkillTransferRecord(
            target_context=features.to_dict(),
            success=success,
            confidence=skill.confidence,
            adaptations=adaptations or {},
        )

        skill.record_transfer(record)
        self._graph.save_skill(skill)

        # If transfer was successful, create a TRANSFERRED_TO edge
        if success:
            logger.info(f"Skill '{skill.name}' successfully transferred " f"(confidence now {skill.confidence:.2f})")
        else:
            logger.info(f"Skill '{skill.name}' transfer failed " f"(confidence now {skill.confidence:.2f})")

    # ========== Introspection ==========

    async def get_skills(self) -> list[Skill]:
        """List all learned skills."""
        return self._graph.list_skills()

    async def get_skill(self, skill_id: str) -> Skill | None:
        """Get a specific skill by ID."""
        return self._graph.get_skill(skill_id)

    def cleanup_expired_skills(self) -> dict[str, int]:
        """Remove expired skills from the graph."""
        return self._graph.cleanup_expired_skills()

    async def get_skill_summary(self) -> dict[str, Any]:
        """Get a summary of the Brain's knowledge.

        Returns:
            Dictionary with skill counts, transfer stats, and top skills.
        """
        skills = self._graph.list_skills()
        if not skills:
            return {
                "total_skills": 0,
                "transferable_skills": 0,
                "avg_confidence": 0.0,
                "total_transfers": 0,
                "top_skills": [],
            }

        transferable = [s for s in skills if s.is_transferable]
        total_transfers = sum(len(s.transfer_history) for s in skills)
        avg_confidence = sum(s.confidence for s in skills) / len(skills)

        # Top skills by usage
        top = sorted(skills, key=lambda s: s.usage_count, reverse=True)[:5]

        return {
            "total_skills": len(skills),
            "transferable_skills": len(transferable),
            "avg_confidence": round(avg_confidence, 3),
            "total_transfers": total_transfers,
            "top_skills": [
                {
                    "name": s.name,
                    "id": s.id,
                    "confidence": s.confidence,
                    "usage_count": s.usage_count,
                    "transfer_count": len(s.transfer_history),
                }
                for s in top
            ],
        }

    # ========== Specialised Learning ==========

    async def learn_recipe(
        self,
        agents: list[dict[str, Any]],
        pattern: str,
        context: dict[str, Any],
        outcome: dict[str, Any],
        skill_name: str | None = None,
    ) -> Skill | None:
        """Learn an execution recipe from a successful multi-agent run.

        Stores which agents were composed and how as deployment-specific
        knowledge the LLM cannot derive from its weights.

        Args:
            agents: List of agent descriptors (dicts with at least ``id``).
            pattern: Composition pattern (e.g. ``"sequential"``, ``"fork-join"``).
            context: Execution context (``domain``, ``task``, …).
            outcome: Must contain ``success`` (bool). Optional: ``quality``.
            skill_name: Optional explicit name.

        Returns:
            Newly created Skill, or None.
        """
        if not agents:
            return None

        features = self._analyzer.analyze(context)
        domain = context.get("domain", "general")
        agent_ids = [a["id"] if isinstance(a, dict) else str(a) for a in agents]
        name = skill_name or f"recipe:{domain}:{pattern}-{'+'.join(agent_ids[:3])}"
        success = outcome.get("success", False)

        # Record success or failure against existing skill
        existing = self._find_existing_skill(features, name)
        if existing:
            existing.record_usage(success=bool(success))
            self._graph.save_skill(existing)
            return existing

        if not success:
            return None

        desc = f"Agent composition for {domain}: {' → '.join(agent_ids)}"

        recipe_data: dict[str, Any] = {
            "pattern": pattern,
            "agents": agents,
            "total_agents": len(agents),
        }
        if "duration_ms" in outcome:
            recipe_data["avg_latency_ms"] = outcome["duration_ms"]
        if "quality" in outcome:
            recipe_data["success_rate"] = float(outcome["quality"])

        preconditions = [
            SkillCondition(
                predicate=f"agent '{aid}' is available",
                description=f"Requires agent '{aid}' in the workflow",
                required=True,
            )
            for aid in agent_ids
        ]
        preconditions.append(
            SkillCondition(
                predicate=f"pattern is {pattern}",
                description=f"Agents must be composed in '{pattern}' pattern",
                required=False,
            )
        )

        skill = Skill(
            name=name,
            description=desc,
            skill_type=SkillType.EXECUTION_RECIPE.value,
            procedure=[
                SkillStep(action=f"execute {aid}", description=f"Run agent {aid}", order=i)
                for i, aid in enumerate(agent_ids)
            ],
            preconditions=preconditions,
            source_context=features.to_dict(),
            confidence=min(0.7, 0.5 + outcome.get("quality", 0.5) * 0.2),
            success_rate=1.0,
            usage_count=1,
            tags=list(set(features.domain_hints + [pattern])),
            task_description=context.get("task", ""),
            domain_keywords=features.domain_hints or [domain],
            output_description=context.get("output_format", ""),
            search_tokens=generate_search_tokens(name),
            recipe=recipe_data,
        )
        skill.renew_ttl()
        self._graph.save_skill(skill)
        self._log_learning_event(skill, context, outcome)
        logger.info(f"Learned recipe '{skill.name}' ({skill.id})")
        return skill

    async def learn_anti_pattern(
        self,
        what_failed: str,
        why: str,
        context: dict[str, Any],
        severity: str = "warning",
    ) -> Skill:
        """Record a failure anti-pattern so the Brain avoids repeating it.

        Args:
            what_failed: Short description of the failed configuration.
            why: Root-cause explanation.
            context: Execution context (``domain``, ``task``, …).
            severity: ``"warning"`` or ``"critical"``.

        Returns:
            The anti-pattern skill (always created).
        """
        domain = context.get("domain", "general")
        # Slugify what_failed to produce a clean, compact identifier
        slug = re.sub(r"[^a-z0-9]+", "-", what_failed.lower()).strip("-")[:40]
        name = f"anti:{domain}:{slug}"
        features = self._analyzer.analyze(context)

        # Check for existing anti-pattern — reinforce instead of duplicating
        existing = self._find_existing_skill(features, name)
        if existing:
            existing.record_usage(success=False)
            self._graph.save_skill(existing)
            logger.info(f"Reinforced existing anti-pattern '{existing.name}' ({existing.id})")
            return existing

        skill = Skill(
            name=name,
            description=f"AVOID: {what_failed}. Reason: {why}",
            skill_type=SkillType.ANTI_PATTERN.value,
            source_context=features.to_dict(),
            confidence=0.9,
            success_rate=0.0,
            usage_count=1,
            tags=["anti-pattern", severity] + features.domain_hints,
            task_description=what_failed,
            domain_keywords=features.domain_hints or [domain],
            anti_signals=[why],
            search_tokens=generate_search_tokens(name),
        )
        skill.renew_ttl()
        self._graph.save_skill(skill)
        logger.info(f"Learned anti-pattern '{skill.name}' ({skill.id})")
        return skill

    async def learn_path(
        self,
        path_nodes: list[str],
        score: float,
        context: dict[str, Any],
        outcome: dict[str, Any],
        budget_used: dict[str, Any] | None = None,
    ) -> Skill | None:
        """Learn a GraphScout-discovered path as a reusable skill.

        Args:
            path_nodes: Ordered list of agent/node IDs in the path.
            score: GraphScout score for this path.
            context: Execution context.
            outcome: Execution outcome (must include ``success``).
            budget_used: Optional budget consumption (tokens, latency).

        Returns:
            Newly created Skill, or None if outcome was not successful.
        """
        if not path_nodes:
            return None

        domain = context.get("domain", "general")
        name = f"path:{domain}:{'→'.join(path_nodes[:4])}"
        features = self._analyzer.analyze(context)
        success = outcome.get("success", False)

        # Record success or failure against existing skill
        existing = self._find_existing_skill(features, name)
        if existing:
            existing.record_usage(success=bool(success))
            self._graph.save_skill(existing)
            return existing

        if not success:
            return None

        recipe: dict[str, Any] = {
            "pattern": "graphscout-path",
            "agents": [{"id": nid} for nid in path_nodes],
            "total_agents": len(path_nodes),
            "graphscout_score": score,
        }
        if budget_used:
            recipe["budget_used"] = budget_used

        preconditions = [
            SkillCondition(
                predicate=f"agent '{nid}' is available",
                description=f"Requires agent '{nid}' in the workflow",
                required=True,
            )
            for nid in path_nodes
        ]

        skill = Skill(
            name=name,
            description=f"GraphScout path for {domain}: {' → '.join(path_nodes)}",
            skill_type=SkillType.GRAPH_PATH.value,
            procedure=[SkillStep(action=f"execute {nid}", order=i) for i, nid in enumerate(path_nodes)],
            preconditions=preconditions,
            source_context=features.to_dict(),
            confidence=min(0.8, score),
            success_rate=1.0,
            usage_count=1,
            tags=features.domain_hints + ["graphscout"],
            task_description=context.get("task", ""),
            domain_keywords=features.domain_hints or [domain],
            search_tokens=generate_search_tokens(name),
            recipe=recipe,
        )
        skill.renew_ttl()
        self._graph.save_skill(skill)
        self._log_learning_event(skill, context, outcome)
        logger.info(f"Learned path '{skill.name}' ({skill.id})")
        return skill

    # ========== Internal Helpers ==========

    def _extract_procedure(self, trace: dict[str, Any]) -> list[SkillStep]:
        """Extract abstract procedure steps from an execution trace."""
        steps: list[SkillStep] = []
        raw_steps = trace.get("steps", [])

        for i, step in enumerate(raw_steps):
            if isinstance(step, dict):
                action = step.get("action", step.get("agent_id", f"step_{i}"))
                description = step.get("description", step.get("result", ""))
                if len(str(action)) > 80:
                    action = self._abstract_action(str(action))
                steps.append(
                    SkillStep(
                        action=str(action),
                        description=str(description),
                        order=i,
                        parameters=step.get("parameters", {}),
                        is_optional=step.get("optional", False),
                    )
                )
            elif isinstance(step, str):
                action = self._abstract_action(step) if len(step) > 80 else step
                steps.append(SkillStep(action=action, description=step, order=i))

        # Also extract from agents list if no explicit steps
        if not steps and "agents" in trace:
            agents = trace["agents"]
            if isinstance(agents, list):
                for i, agent in enumerate(agents):
                    agent_id = agent if isinstance(agent, str) else agent.get("id", f"agent_{i}")
                    steps.append(
                        SkillStep(
                            action=f"execute {agent_id}",
                            description=f"Run agent {agent_id}",
                            order=i,
                        )
                    )

        return steps

    @staticmethod
    def _abstract_action(text: str) -> str:
        """Reduce a verbose sentence to an abstract ``verb [target]`` phrase."""
        words = text.strip().split()
        if not words:
            return "process"
        verb = words[0].lower().rstrip(":.,-()")
        verb = ACTION_VERB_CANONICAL.get(verb, verb)
        if len(words) > 3:
            return f"{verb} [target]"
        return text

    def _extract_preconditions(self, features: ContextFeatures, trace: dict[str, Any]) -> list[SkillCondition]:
        """Extract preconditions from context features and trace."""
        conditions = []

        if features.input_shape != "unknown":
            conditions.append(
                SkillCondition(
                    predicate=f"input is {features.input_shape}",
                    description=f"The input must be in {features.input_shape} form",
                    required=True,
                )
            )

        for structure in features.task_structures:
            conditions.append(
                SkillCondition(
                    predicate=f"task supports {structure}",
                    description=f"The task must be amenable to {structure}",
                    required=False,
                )
            )

        return conditions

    def _extract_postconditions(self, features: ContextFeatures, outcome: dict[str, Any]) -> list[SkillCondition]:
        """Extract postconditions from outcome."""
        conditions = []

        if features.output_shape != "unknown":
            conditions.append(
                SkillCondition(
                    predicate=f"output is {features.output_shape}",
                    description=f"The output will be in {features.output_shape} form",
                    required=True,
                )
            )

        quality = outcome.get("quality")
        if quality is not None:
            conditions.append(
                SkillCondition(
                    predicate=f"quality >= {quality:.2f}",
                    description=f"Expected quality score of at least {quality:.2f}",
                    required=False,
                )
            )

        return conditions

    def _generate_skill_name(self, features: ContextFeatures) -> str:
        """Generate a descriptive skill name from features.

        Uses the v2 ``type:domain:specifics`` format when domain hints are
        available, otherwise falls back to the legacy cognitive-pattern name.
        """
        domain = features.domain_hints[0] if features.domain_hints else None
        pattern = features.cognitive_patterns[0].lower() if features.cognitive_patterns else None
        structure = features.task_structures[0].lower() if features.task_structures else None

        if domain and pattern:
            specifics = f"{pattern}-{structure}" if structure else pattern
            return f"procedural:{domain}:{specifics}"

        # Legacy fallback
        parts: list[str] = []
        if features.cognitive_patterns:
            parts.append(features.cognitive_patterns[0].title())
        if features.task_structures:
            parts.append(f"via {features.task_structures[0].title()}")
        if features.domain_hints:
            parts.append(f"({features.domain_hints[0]})")
        return " ".join(parts) if parts else "Unnamed Skill"

    def _generate_description(self, features: ContextFeatures, procedure: list[SkillStep]) -> str:
        """Generate a description of the skill."""
        parts = [features.abstract_goal]

        if procedure:
            step_names = [s.action for s in procedure[:3]]
            parts.append(f"Steps: {' → '.join(step_names)}")

        return ". ".join(parts)

    def _find_existing_skill(self, features: ContextFeatures, name: str) -> Skill | None:
        """Check if a structurally similar skill already exists.

        Uses exact fingerprint match first (fast path), then falls back
        to structural similarity via Jaccard on task structures, cognitive
        patterns, and I/O shapes.
        """
        existing_skills = self._graph.list_skills()
        fingerprint = features.fingerprint()

        best_match: Skill | None = None
        best_score: float = 0.0

        for skill in existing_skills:
            existing_features = ContextFeatures.from_dict(skill.source_context)

            # Exact fingerprint → definitely the same skill
            if existing_features.fingerprint() == fingerprint:
                return skill

            # Similarity-based match
            sim = features.similarity_to(existing_features)
            if sim > best_score:
                best_match = skill
                best_score = sim

        if best_match is not None and best_score >= 0.7:
            logger.info(f"Found similar skill '{best_match.name}' " f"(similarity: {best_score:.2f})")
            return best_match

        return None

    def _log_learning_event(
        self,
        skill: Skill,
        context: dict[str, Any],
        outcome: dict[str, Any],
    ) -> None:
        """Log a learning event to OrKa memory for traceability."""
        try:
            self._memory.log(
                agent_id="orka_brain",
                event_type="skill_learned",
                payload={
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "context_domain": context.get("domain", "unknown"),
                    "context_task": context.get("task", "unknown"),
                    "outcome_success": outcome.get("success", False),
                    "outcome_quality": outcome.get("quality"),
                    "num_steps": len(skill.procedure),
                    "tags": skill.tags,
                },
                log_type="stored",
            )
        except Exception as e:
            logger.debug(f"Could not log learning event: {e}")
