# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
# 
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

import os
import pytest
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_base_agent_fails():
    from orka.agents.agent_base import BaseAgent
    class Incomplete(BaseAgent): pass
    with pytest.raises(TypeError):
        Incomplete("id", "prompt", "queue")
