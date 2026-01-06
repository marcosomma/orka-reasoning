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
OrKa Dark Theme - Modern Sleek Dark Mode
Register this theme with Textual for user selection.
"""
from textual.theme import Theme

# Define the dark modern theme
DARK = Theme(
    name="orka-dark",
    primary="#58a6ff",
    secondary="#bc8cff",
    warning="#d29922",
    error="#f85149",
    success="#3fb950",
    accent="#79c0ff",
    foreground="#c9d1d9",
    background="#0d1117",
    surface="#161b22",
    panel="#161b22",
)
