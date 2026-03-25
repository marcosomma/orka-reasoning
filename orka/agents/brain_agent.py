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

    def _ensure_brain(self, ctx: Dict[str, Any]) -> Brain:
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

    def _extract_llm_payload(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _handle_learn(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _handle_recall(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        brain = self._ensure_brain(ctx)
        payload = self._extract_llm_payload(ctx)

        # Build context for recall
        context = {
            "domain": payload.get("domain", "general"),
            "task": payload.get("task", str(payload.get("response", ""))[:200]),
            "input": payload.get("input_description", str(payload.get("response", ""))[:100]),
        }

        candidates = await brain.recall(
            context=context,
            top_k=int(payload.get("top_k", 3)),
            min_score=float(payload.get("min_score", 0.0)),
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

    async def _handle_feedback(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
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
    # main dispatch
    # ------------------------------------------------------------------ #

    async def _run_impl(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        operation = ctx.get("operation", self.operation)
        if operation == "recall":
            return await self._handle_recall(ctx)
        if operation == "feedback":
            return await self._handle_feedback(ctx)
        return await self._handle_learn(ctx)
