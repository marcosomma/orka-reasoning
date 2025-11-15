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
Boolean-Based Scoring System
============================

Provides deterministic, auditable scoring based on boolean evaluation criteria.
"""

from .calculator import BooleanScoreCalculator
from .presets import PRESETS, load_preset

__all__ = ["BooleanScoreCalculator", "PRESETS", "load_preset"]

