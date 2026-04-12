# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Brain Constants
===============

Shared constants for skill abstraction and action normalization.

The ``ACTION_VERBS`` set and ``ACTION_VERB_CANONICAL`` mapping are used by
both ``brain_agent.py`` (procedure abstraction from raw LLM output) and
``brain.py`` (action abstraction in ``_extract_procedure``).

Derived from frequency analysis of 100 real brain outputs.
"""

from __future__ import annotations

MAX_ACTION_LENGTH: int = 60
"""Maximum allowed length for a ``SkillStep.action`` string.

Actions exceeding this length are warning-logged and truncated in
``SkillStep.__post_init__``.
"""

# ── Action Verb Set ──────────────────────────────────────────────────
# Organized by cognitive category for maintainability.
# Counts reflect frequency in production brain traces (top verbs annotated).

ACTION_VERBS: frozenset[str] = frozenset(
    {
        # Discovery & investigation (top: identify=22, collect=7, gather=6)
        "identify",
        "detect",
        "discover",
        "investigate",
        "inspect",
        "explore",
        "scan",
        "survey",
        "probe",
        "research",
        # Data acquisition (collect=7, gather=6, extract=5, catalog=3)
        "collect",
        "gather",
        "extract",
        "fetch",
        "retrieve",
        "parse",
        "catalog",
        "inventory",
        "compile",
        "mine",
        # Analysis & evaluation (assess=7, evaluate=3, review=6, audit=6)
        "analyze",
        "evaluate",
        "assess",
        "review",
        "audit",
        "diagnose",
        "profile",
        "benchmark",
        "measure",
        "quantify",
        "examine",
        "interpret",
        "characterize",
        "study",
        # Planning & design (design=11, define=19, plan=4, establish=4)
        "design",
        "define",
        "plan",
        "establish",
        "architect",
        "outline",
        "draft",
        "formulate",
        "specify",
        "scope",
        "schedule",
        "prioritize",
        "budget",
        "allocate",
        "assign",
        # Creation & implementation (implement=28, create=10, develop=3)
        "implement",
        "create",
        "build",
        "construct",
        "develop",
        "generate",
        "produce",
        "compose",
        "synthesize",
        "author",
        "introduce",
        "provision",
        "configure",
        "set",
        # Transformation & processing (normalize=2, refactor=2, migrate=1)
        "transform",
        "convert",
        "translate",
        "normalize",
        "standardize",
        "adapt",
        "modify",
        "refactor",
        "restructure",
        "migrate",
        "deduplicate",
        "merge",
        "consolidate",
        "aggregate",
        "align",
        # Validation & verification (validate=14, verify=3, test=3)
        "validate",
        "verify",
        "check",
        "confirm",
        "test",
        "assert",
        "ensure",
        "certify",
        "reconcile",
        # Classification & organization (classify=2, map=6, select=2)
        "classify",
        "categorize",
        "group",
        "cluster",
        "sort",
        "rank",
        "label",
        "tag",
        "index",
        "organize",
        "map",
        "segment",
        "partition",
        "select",
        "filter",
        # Computation & modeling
        "compute",
        "calculate",
        "estimate",
        "derive",
        "simulate",
        "model",
        "predict",
        "forecast",
        "project",
        "interpolate",
        # Optimization & improvement (optimize=1, refine=1, iterate=5)
        "optimize",
        "improve",
        "enhance",
        "tune",
        "calibrate",
        "adjust",
        "refine",
        "streamline",
        "iterate",
        # Communication & documentation (document=20, summarize=3, report=3)
        "document",
        "summarize",
        "report",
        "present",
        "explain",
        "describe",
        "annotate",
        "communicate",
        "recommend",
        "propose",
        "suggest",
        "provide",
        "offer",
        # Mitigation & resolution
        "mitigate",
        "resolve",
        "fix",
        "patch",
        "repair",
        "remediate",
        "address",
        "correct",
        "recover",
        "restore",
        # Execution & deployment (deploy=7, run=2, automate=3)
        "deploy",
        "execute",
        "run",
        "launch",
        "invoke",
        "trigger",
        "activate",
        "initiate",
        "automate",
        "perform",
        # Integration & composition (integrate=5, load=2)
        "integrate",
        "combine",
        "unify",
        "connect",
        "link",
        "load",
        "ingest",
        # Monitoring & observation (monitor=6, instrument=2, train=2)
        "monitor",
        "observe",
        "track",
        "trace",
        "instrument",
        "log",
        "watch",
        # Learning & iteration (train=2, apply=3, update=2)
        "train",
        "apply",
        "update",
        "replace",
        "rollback",
        "conduct",
        "prepare",
    }
)

# ── Verb Normalization Map ───────────────────────────────────────────
# Maps synonyms to a canonical form for consistent skill procedures.
# Keys MUST be members of ACTION_VERBS.

ACTION_VERB_CANONICAL: dict[str, str] = {
    # discovery synonyms → canonical
    "review": "evaluate",
    "check": "validate",
    "inspect": "evaluate",
    "examine": "analyze",
    "study": "analyze",
    "research": "investigate",
    "probe": "investigate",
    # creation synonyms → canonical
    "build": "construct",
    "create": "generate",
    "produce": "generate",
    "compose": "generate",
    "author": "generate",
    "develop": "implement",
    # mitigation synonyms → canonical
    "fix": "mitigate",
    "patch": "mitigate",
    "repair": "mitigate",
    "correct": "mitigate",
    "remediate": "mitigate",
    # optimization synonyms → canonical
    "improve": "optimize",
    "enhance": "optimize",
    "tune": "optimize",
    "refine": "optimize",
    "streamline": "optimize",
    # validation synonyms → canonical
    "test": "validate",
    "verify": "validate",
    "confirm": "validate",
    "assert": "validate",
    "ensure": "validate",
    # execution synonyms → canonical
    "deploy": "execute",
    "run": "execute",
    "launch": "execute",
    "invoke": "execute",
    "trigger": "execute",
}
