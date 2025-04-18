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

def test_logger_write_and_read(monkeypatch):
    from orka.memory_logger import RedisMemoryLogger
    logger = RedisMemoryLogger()
    logger.log("test_agent", "output", {"foo": "bar"})
    items = logger.client.xrevrange("orka:memory", count=1)
    assert len(items[0][1]) == 4