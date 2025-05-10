# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
OrKa: Orchestrator Kit Agents
=============================

OrKa is a flexible and powerful orchestration framework for AI agents. It provides
a structured way to build, connect, and manage various AI agents in a workflow.

Key Components:
--------------
- Orchestrator: Core engine that manages agent workflows and execution
- Agents: Various task-specific agents (LLM, search, classification, etc.)
- Nodes: Special components like routers, forks, and joins for workflow management
- Memory: Persistent storage system for agent outputs and workflow state
- Fork/Join: Advanced workflow patterns for parallel execution

Usage:
-----
1. Define your agent workflows in YAML configuration
2. Initialize the Orchestrator with your config
3. Run the workflow with your input data
4. Retrieve and process the results

Example:
-------
```python
from orka import Orchestrator

# Initialize with your YAML config
orchestrator = Orchestrator("my_workflow.yml")

# Run the workflow
result = await orchestrator.run({"input": "Your query here"})
```

For more details, see the documentation at https://github.com/marcosomma/orka-resoning
"""

from .agents import *
from .fork_group_manager import ForkGroupManager
from .loader import YAMLLoader
from .memory_logger import RedisMemoryLogger
from .nodes import *
from .orchestrator import Orchestrator
from .orka_cli import run_cli_entrypoint
