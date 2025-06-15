# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

# Import the refactored orchestrator
import asyncio
import inspect

# Import other modules that tests might need
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from time import time
from uuid import uuid4

from jinja2 import Template

# Import components for backward compatibility
from . import agents
from .core.agent_manager import AGENT_TYPES
from .core.orchestrator import Orchestrator
from .error_handling import ErrorReporter, ErrorTelemetry
from .execution import AgentExecutor, ParallelExecutor
from .fork_group_manager import ForkGroupManager, SimpleForkGroupManager
from .loader import YAMLLoader
from .memory_logger import create_memory_logger
from .reporting import MetaReportGenerator
from .utils.common_utils import CommonUtils

# Maintain backward compatibility by re-exporting all classes and functions
__all__ = [
    "AGENT_TYPES",
    "AgentExecutor",
    "CommonUtils",
    "ErrorReporter",
    "ErrorTelemetry",
    "ForkGroupManager",
    "MetaReportGenerator",
    "Orchestrator",
    "ParallelExecutor",
    "SimpleForkGroupManager",
    "Template",
    "ThreadPoolExecutor",
    "YAMLLoader",
    "agents",
    "asyncio",
    "create_memory_logger",
    "datetime",
    "inspect",
    "json",
    "logging",
    "os",
    "time",
    "timezone",
    "uuid4",
]
