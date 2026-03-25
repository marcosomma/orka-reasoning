# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
OrKa Brain — Executional Learning Engine
=========================================

The Brain module is an execution engine inspired by OrKa that learns skills
from successful executions and re-applies them in completely different contexts.

Core Concept
------------

Traditional workflow engines execute predefined procedures. The Brain goes further:
it *observes* what works, *abstracts* it into transferable skills, and *recalls*
those skills when facing new problems — even in entirely different domains.

**Example**: If the Brain learns a "divide-and-conquer" skill while processing
text analysis, it can recognize when that same pattern applies to data pipeline
orchestration, code review, or any other domain where decomposition is useful.

Architecture
------------

The Brain is built on four pillars:

1. **Skill Model** — Context-free representation of a learned capability.
   Each skill has abstract procedures, preconditions, postconditions, and
   vector embeddings for semantic matching.

2. **Skill Graph** — A knowledge graph of skills stored in Redis.
   Skills form a graph through relationships like DERIVES_FROM, COMPOSED_OF,
   SPECIALIZES, and TRANSFERRED_TO.

3. **Context Analyzer** — Decomposes any execution context into abstract
   features (task type, complexity, structure, patterns) so that skills
   can be matched across domains.

4. **Skill Transfer Engine** — The core intelligence. Finds relevant skills
   via semantic search, evaluates applicability, and adapts procedures from
   the source context to the target context.

Usage
-----

.. code-block:: python

    from orka.brain import Brain

    brain = Brain(memory=my_memory_logger)

    # Learn from a successful execution
    await brain.learn(
        execution_trace=trace,
        context={"domain": "text_analysis", "task": "summarization"},
        outcome={"success": True, "quality": 0.95},
    )

    # Later, in a completely different context...
    applicable_skills = await brain.recall(
        context={"domain": "code_review", "task": "identify key changes"},
    )

    # Execute with transferred skills
    result = await brain.execute(
        input_data="Review this PR",
        context={"domain": "code_review"},
    )
"""

from .skill import Skill, SkillStep, SkillCondition, SkillTransferRecord
from .skill_graph import SkillGraph
from .context_analyzer import ContextAnalyzer, ContextFeatures
from .transfer_engine import SkillTransferEngine, TransferCandidate
from .brain import Brain

__all__ = [
    "Brain",
    "ContextAnalyzer",
    "ContextFeatures",
    "Skill",
    "SkillCondition",
    "SkillGraph",
    "SkillStep",
    "SkillTransferEngine",
    "SkillTransferRecord",
    "TransferCandidate",
]
