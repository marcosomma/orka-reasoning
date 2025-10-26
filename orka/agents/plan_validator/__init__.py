# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Plan Validator Agent Module
============================

Meta-cognitive agent that validates and critiques proposed agent execution paths.
Designed to work in feedback loops with GraphScout or other planning agents.

The PlanValidatorAgent evaluates proposed paths across multiple dimensions:
- Completeness: Does the path address all aspects of the query?
- Efficiency: Is it optimal in terms of cost and latency?
- Safety: Are there any risky agent combinations or data flows?
- Coherence: Do the agents work well together in this sequence?
- Fallback: Are error cases and edge cases handled?
"""

from .agent import PlanValidatorAgent

__all__ = ["PlanValidatorAgent"]
