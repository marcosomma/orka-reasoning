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
CLI Utilities
============

This module contains shared utility functions used across the OrKa CLI system.
"""

from orka.utils.logging_utils import (
    setup_logging,  # Re-export for backward compatibility
)

__all__ = ["setup_logging"]
