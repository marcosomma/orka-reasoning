# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
BrainAgent — Orchestrator-compatible wrapper for the Brain learning engine.

Supports two operations:

- **learn**: Extract a transferable skill from an LLM's reasoning trace.
- **recall**: Find previously learned skills that apply to a new context.

YAML example::

    agents:
      - id: brain_learn
        type: brain
        operation: learn
        prompt: "{{ previous_outputs.llm_reasoner }}"

      - id: brain_recall
        type: brain
        operation: recall
        prompt: "{{ previous_outputs.llm_new_context }}"
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from .base_agent import BaseAgent
from ..brain import Brain
from ..contracts import Context

logger = logging.getLogger(__name__)


class BrainAgent(BaseAgent):
    """Orchestrator agent that wraps the Brain learn/recall cycle.

    Args:
        agent_id: Unique id for this agent instance.
        operation: ``"learn"`` or ``"recall"`` (default ``"learn"``).
        memory_logger: RedisStackMemoryLogger (or compatible) injected by the factory.
        **kwargs: Forwarded to :class:`BaseAgent`.
    """

    def __init__(
        self,
        agent_id: str,
        operation: str = "learn",
        memory_logger: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(agent_id=agent_id, **kwargs)
        self.operation = operation.strip().lower()
        self._brain: Brain | None = None
        self._memory_logger = memory_logger

    def _ensure_brain(self, ctx: Context) -> Brain:
        """Lazy-init the Brain using the memory logger."""
        if self._brain is None:
            mem = self._memory_logger
            if mem is None:
                raise RuntimeError(
                    f"BrainAgent '{self.agent_id}' requires a memory_logger. "
                    "Ensure the orchestrator provides one."
                )
            self._brain = Brain(memory=mem)
        return self._brain

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_json_field(raw: Any) -> Dict[str, Any]:
        """Best-effort parse a value into a dict.

        Handles JSON strings and Python literal representations (as produced
        by Jinja2 when rendering a dict to a template string).
        """
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            # Try JSON first
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # Jinja2 renders dicts using Python repr (single quotes,
            # True/False instead of true/false). Try ast.literal_eval.
            import ast

            try:
                parsed = ast.literal_eval(raw)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, SyntaxError):
                pass
        return {}

    def _extract_llm_payload(self, ctx: Context) -> Dict[str, Any]:
        """Extract the LLM reasoning payload from the orchestrator context.

        The agent looks for data in this order:
        1. ``formatted_prompt`` — the rendered Jinja2 template (preferred)
        2. ``input`` — the raw input
        """
        raw = ctx.get("formatted_prompt") or ctx.get("input", "")
        parsed = self._parse_json_field(raw)
        if parsed:
            return parsed

        # If the raw value is a plain string, wrap it
        if isinstance(raw, str) and raw.strip():
            return {"response": raw}
        return {}

    # ------------------------------------------------------------------ #
    # learn
    # ------------------------------------------------------------------ #

    async def _handle_learn(self, ctx: Context) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        # Build execution trace from the LLM's reasoning
        response_text = str(payload.get("response", ""))
        reasoning = str(payload.get("internal_reasoning", ""))
        confidence = str(payload.get("confidence", "0.5"))

        # The LLM's reasoning becomes the execution trace
        steps_raw = payload.get("steps", [])
        if not steps_raw:
            # Prefer the richer response text over internal_reasoning
            source = reasoning if len(reasoning) > len(response_text) else response_text
            if source:
                sentences = [
                    s.strip()
                    for s in source.replace("\n", ". ").split(". ")
                    if len(s.strip()) > 20
                ]
                steps_raw = [{"action": s, "result": "success"} for s in sentences[:10]]

        execution_trace = {
            "steps": steps_raw,
            "agents": [self.agent_id],
            "strategy": "sequential",
        }

        # Build context from metadata in the payload
        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", response_text[:200]),
            "input": payload.get("input_description", response_text[:100]),
        }

        outcome = {
            "success": True,
            "quality": min(1.0, float(confidence)),
        }

        skill = await brain.learn(
            execution_trace=execution_trace,
            context=context,
            outcome=outcome,
            skill_name=payload.get("skill_name"),
        )

        if skill:
            return {
                "response": f"Learned skill: {skill.name}",
                "confidence": str(skill.confidence),
                "internal_reasoning": f"Abstracted {len(skill.procedure)} steps into transferable skill '{skill.name}'",
                "skill_id": skill.id,
                "skill_name": skill.name,
                "skill_steps": [s.action for s in skill.procedure],
                "skill_tags": skill.tags,
            }

        return {
            "response": "No skill could be learned from the provided trace.",
            "confidence": "0.0",
            "internal_reasoning": "The execution trace was insufficient for skill abstraction.",
        }

    # ------------------------------------------------------------------ #
    # recall
    # ------------------------------------------------------------------ #

    async def _handle_recall(self, ctx: Context) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        # Build context for recall
        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", str(payload.get("response", ""))[:200]),
            "input": payload.get("input_description", str(payload.get("response", ""))[:100]),
        }

        # V2 filters
        skill_types = payload.get("skill_types")
        domain_filter = payload.get("domain_filter")

        candidates = await brain.recall(
            context=context,
            top_k=int(payload.get("top_k", 3)),
            min_score=float(payload.get("min_score", 0.0)),
            skill_types=skill_types if isinstance(skill_types, list) else None,
            domain_filter=domain_filter if isinstance(domain_filter, str) else None,
        )

        if candidates:
            top = candidates[0]
            return {
                "response": (
                    f"Found applicable skill: '{top.skill.name}' (score: {top.combined_score:.2f}). "
                    f"Steps: {' → '.join(s.action for s in top.skill.procedure)}"
                ),
                "confidence": str(top.combined_score),
                "internal_reasoning": top.reasoning or "Matched by structural and semantic similarity.",
                "skill_id": top.skill.id,
                "skill_name": top.skill.name,
                "skill_steps": [s.action for s in top.skill.procedure],
                "skill_tags": top.skill.tags,
                "combined_score": top.combined_score,
                "structural_score": top.structural_score,
                "semantic_score": top.semantic_score,
                "adaptations": top.adaptations or {},
                "all_candidates": [
                    {
                        "skill_name": c.skill.name,
                        "score": c.combined_score,
                        "reasoning": c.reasoning,
                    }
                    for c in candidates
                ],
            }

        return {
            "response": "No applicable skills found for this context.",
            "confidence": "0.0",
            "internal_reasoning": "No learned skill matched the target context.",
            "all_candidates": [],
        }

    # ------------------------------------------------------------------ #
    # feedback
    # ------------------------------------------------------------------ #

    async def _handle_feedback(self, ctx: Context) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        skill_id = payload.get("skill_id", "")
        if not skill_id:
            return {
                "response": "No skill_id provided for feedback.",
                "confidence": "0.0",
                "internal_reasoning": "Feedback requires a skill_id from a previous recall.",
            }

        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", str(payload.get("skill_name", ""))[:200]),
            "input": payload.get("input_description", ""),
        }

        success = payload.get("success", True)
        if isinstance(success, str):
            success = success.lower() not in ("false", "0", "no")

        adaptations = payload.get("adaptations", {})

        await brain.feedback(
            skill_id=skill_id,
            context=context,
            success=bool(success),
            adaptations=adaptations if isinstance(adaptations, dict) else {},
        )

        skill = await brain.get_skill(skill_id)
        skill_name = skill.name if skill else "unknown"
        transfer_count = len(skill.transfer_history) if skill else 0
        confidence = skill.confidence if skill else 0.0

        return {
            "response": f"Recorded {'successful' if success else 'failed'} transfer for skill '{skill_name}'.",
            "confidence": str(confidence),
            "internal_reasoning": f"Transfer feedback recorded. Skill now has {transfer_count} transfer(s).",
            "skill_id": skill_id,
            "skill_name": skill_name,
            "transfer_count": transfer_count,
            "transfer_success": bool(success),
        }

    # ------------------------------------------------------------------ #
    # learn_recipe
    # ------------------------------------------------------------------ #

    async def _handle_learn_recipe(self, ctx: Context) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        agents_raw = payload.get("agents", [])
        if isinstance(agents_raw, str):
            try:
                agents_raw = json.loads(agents_raw)
            except (json.JSONDecodeError, TypeError):
                agents_raw = [{"id": agents_raw}]

        agents = [
            a if isinstance(a, dict) else {"id": str(a)} for a in agents_raw
        ]

        pattern = str(payload.get("pattern", payload.get("strategy", "sequential")))

        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", ""),
            "output_format": payload.get("output_format", ""),
        }

        success = payload.get("success", True)
        if isinstance(success, str):
            success = success.lower() not in ("false", "0", "no")

        outcome = {
            "success": bool(success),
            "quality": float(payload.get("quality", payload.get("confidence", 0.7))),
        }
        if "duration_ms" in payload:
            outcome["duration_ms"] = int(payload["duration_ms"])

        skill = await brain.learn_recipe(
            agents=agents,
            pattern=pattern,
            context=context,
            outcome=outcome,
            skill_name=payload.get("skill_name"),
        )

        if skill:
            return {
                "response": f"Learned recipe: {skill.name}",
                "confidence": str(skill.confidence),
                "internal_reasoning": f"Stored execution recipe with {len(skill.recipe.get('agents', []))} agents",
                "skill_id": skill.id,
                "skill_name": skill.name,
                "skill_type": skill.skill_type,
            }
        return {
            "response": "No recipe could be learned (missing agents or failed outcome).",
            "confidence": "0.0",
        }

    # ------------------------------------------------------------------ #
    # learn_anti_pattern
    # ------------------------------------------------------------------ #

    async def _handle_learn_anti(self, ctx: Context) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        what_failed = str(payload.get("what_failed", payload.get("response", "")))
        why = str(payload.get("why", payload.get("reason", "unknown")))
        severity = str(payload.get("severity", "warning"))

        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", what_failed[:200]),
        }

        skill = await brain.learn_anti_pattern(
            what_failed=what_failed,
            why=why,
            context=context,
            severity=severity,
        )
        return {
            "response": f"Recorded anti-pattern: {skill.name}",
            "confidence": str(skill.confidence),
            "internal_reasoning": f"Anti-pattern stored: {why}",
            "skill_id": skill.id,
            "skill_name": skill.name,
            "skill_type": skill.skill_type,
        }

    # ------------------------------------------------------------------ #
    # learn_path
    # ------------------------------------------------------------------ #

    async def _handle_learn_path(self, ctx: Context) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        path_nodes_raw = payload.get("path_nodes", payload.get("path", []))
        if isinstance(path_nodes_raw, str):
            path_nodes = [n.strip() for n in path_nodes_raw.split("→") if n.strip()]
        else:
            # Normalise: the LLM may return dicts (e.g. {"id": "agent1"}) instead of plain strings
            path_nodes = []
            for item in path_nodes_raw:
                if isinstance(item, str):
                    path_nodes.append(item)
                elif isinstance(item, dict):
                    path_nodes.append(
                        str(item.get("id") or item.get("name") or item.get("node_id") or item)
                    )
                else:
                    path_nodes.append(str(item))

        score = float(payload.get("score", payload.get("confidence", 0.5)))

        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", ""),
        }

        success = payload.get("success", True)
        if isinstance(success, str):
            success = success.lower() not in ("false", "0", "no")

        outcome = {
            "success": bool(success),
            "quality": float(payload.get("quality", score)),
        }

        budget_used = payload.get("budget_used")

        skill = await brain.learn_path(
            path_nodes=path_nodes,
            score=score,
            context=context,
            outcome=outcome,
            budget_used=budget_used if isinstance(budget_used, dict) else None,
        )

        if skill:
            return {
                "response": f"Learned path: {skill.name}",
                "confidence": str(skill.confidence),
                "internal_reasoning": f"GraphScout path stored with {len(path_nodes)} nodes",
                "skill_id": skill.id,
                "skill_name": skill.name,
                "skill_type": skill.skill_type,
            }
        return {
            "response": "No path could be learned (empty path or failed outcome).",
            "confidence": "0.0",
        }

    # ------------------------------------------------------------------ #
    # main dispatch
    # ------------------------------------------------------------------ #

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        operation = ctx.get("operation", self.operation)
        if operation == "recall":
            return await self._handle_recall(ctx)
        if operation == "feedback":
            return await self._handle_feedback(ctx)
        if operation == "learn_recipe":
            return await self._handle_learn_recipe(ctx)
        if operation == "learn_anti":
            return await self._handle_learn_anti(ctx)
        if operation == "learn_path":
            return await self._handle_learn_path(ctx)
        return await self._handle_learn(ctx)
