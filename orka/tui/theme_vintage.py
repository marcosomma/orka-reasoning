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
OrKa Vintage Theme - Classic Green Phosphor CRT Aesthetic
Register this theme with Textual for user selection.
"""
from textual.theme import Theme

# Define the vintage CRT theme
VINTAGE = Theme(
    name="orka-vintage",
    primary="#00ff00",
    secondary="#00ff00", 
    warning="#ffaa00",
    error="#ff3333",
    success="#00ff00",
    accent="#ccffcc",
    foreground="#aaffaa",
    background="#000000",
    surface="#001100",
    panel="#002200",
)
