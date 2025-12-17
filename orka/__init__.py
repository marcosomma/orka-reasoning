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
OrKa: Orchestrator Kit Agents
==============================

OrKa is a comprehensive orchestration framework for AI agents that provides
structured workflows and intelligent memory management.

Purpose: High-level package overview and entrypoints.

Assumptions:
- Users should validate configuration and run integration tests before deploying to production.

Proof: See `docs/INTEGRATION_EXAMPLES.md` and `tests/integration/` for verified examples.

Architecture Overview
=====================

OrKa features a modular architecture with specialized components designed for
maintainability, testability, and extensibility while preserving complete
backward compatibility.

Core Components
===============

**Orchestrator System**
    Modular orchestration engine with specialized components:

    * :class:`~orka.orchestrator.base.OrchestratorBase` - Configuration and initialization
    * :class:`~orka.orchestrator.agent_factory.AgentFactory` - Agent registry and instantiation
    * :class:`~orka.orchestrator.execution_engine.ExecutionEngine` - Workflow execution
    * :class:`~orka.orchestrator.metrics.MetricsCollector` - Performance monitoring
    * :class:`~orka.orchestrator.error_handling.ErrorHandler` - Error management
    * :class:`~orka.orchestrator.simplified_prompt_rendering.SimplifiedPromptRenderer` - Template processing

**Agent Ecosystem**
    Comprehensive agent implementations for various AI tasks:

    * **LLM Agents**: OpenAI integration, local model support
    * **Decision Agents**: Binary decisions, classification, routing
    * **Memory Agents**: Intelligent storage and retrieval
    * **Search Agents**: Web search and information gathering
    * **Validation Agents**: Data validation and structuring

**Node System**
    Specialized workflow control components:

    * **Router Nodes**: Conditional branching and decision trees
    * **Fork/Join Nodes**: Parallel execution and synchronization
    * **Memory Nodes**: Data persistence and retrieval operations
    * **RAG Nodes**: Retrieval-augmented generation workflows

**Memory System**
    High-performance memory backends with vector search capabilities:

    * :class:`~orka.memory.redisstack_logger.RedisStackMemoryLogger` - HNSW vector indexing
    * :class:`~orka.memory.redis_logger.RedisMemoryLogger` - Redis-based storage
    * **Modular Components**: Serialization, compression, file operations

**Command Line Interface**
    Comprehensive CLI for development and production operations:

    * **Workflow Execution**: Run and debug AI workflows
    * **Memory Management**: Statistics, cleanup, monitoring
    * **Configuration Validation**: YAML validation and error reporting
    * **Development Tools**: Interactive testing and debugging

Key Features
============

**Deployment Considerations**

Assumptions: Production deployment requires operational hardening and validation. See `docs/production-readiness.md`.
- Thread-safe execution with concurrency control
- Comprehensive error handling and retry logic
- Performance metrics and monitoring
- Graceful shutdown and resource cleanup

**Intelligent Memory Management**
- Vector similarity search with HNSW indexing
- Automatic memory decay and lifecycle management
- Namespace isolation for multi-tenant scenarios
- Hybrid search combining semantic and metadata filtering

**Developer Experience**
- Declarative YAML configuration
- Interactive CLI with near real-time feedback (deployment and environment dependent)
- Comprehensive error reporting and debugging
- Hot-reload for development workflows

**Scalability and Performance**
- Async/await patterns for non-blocking operations
- Connection pooling and resource management
- Horizontal scaling with stateless architecture
- Optimized data structures and algorithms

Usage Patterns
==============

**Basic Workflow Execution**

.. code-block:: python

    from orka import Orchestrator

    # Initialize with YAML configuration
    orchestrator = Orchestrator("workflow.yml")

    # Execute workflow
    result = await orchestrator.run("input data")

**Memory Backend Configuration**

.. code-block:: python

    from orka.memory_logger import create_memory_logger

    # High-performance RedisStack backend with HNSW
    memory = create_memory_logger("redisstack")

    # Standard Redis backend
    memory = create_memory_logger("redis")

    # RedisStack backend for high-performance vector search
    memory = create_memory_logger("redisstack")

**Custom Agent Development**

.. code-block:: python

    from orka.agents.base_agent import BaseAgent

    class CustomAgent(BaseAgent):
        async def _run_impl(self, ctx):
            input_data = ctx.get("input")
            # Process input asynchronously
            return await self.process(input_data)

**CLI Operations**

.. code-block:: bash

    # Execute workflow
    orka run workflow.yml "input text" --verbose

    # Memory management
    orka memory stats
    orka memory cleanup --dry-run

    # Near real-time monitoring (subject to backend and deployment configuration)
    orka memory watch --run-id <run_id>

Backward Compatibility
======================

OrKa maintains 100% backward compatibility with existing code:

- All existing imports continue to work unchanged
- Legacy agent patterns are fully supported
- Configuration files remain compatible
- API interfaces are preserved

This ensures smooth migration paths and protects existing investments
while providing access to new features and performance improvements.

For More Information
====================

* **Documentation**: https://github.com/marcosomma/orka-reasoning
* **Issues**: https://github.com/marcosomma/orka-reasoning/issues
* **License**: Apache 2.0
* **Author**: Marco Somma (marcosomma.work@gmail.com)
"""

# Import minimal, commonly-used components lazily to avoid heavy import-time costs
# and unintended side-effects (e.g., deprecation warnings from legacy modules).
# Consumers can import specific agents/nodes directly from their modules when needed.
from .fork_group_manager import ForkGroupManager
from .loader import YAMLLoader
from .memory_logger import RedisMemoryLogger, MemoryLogger
from .orchestrator import Orchestrator
from .orka_cli import *

__all__ = [
    # From orka.agents
    "BinaryAgent",
    "ClassificationAgent",
    "BaseAgent",
    "OpenAIAnswerBuilder",
    "OpenAIBinaryAgent",
    "OpenAIClassificationAgent",
    "PlanValidatorAgent",
    "ValidationAndStructuringAgent",
    "AGENT_REGISTRY",
    # From orka.fork_group_manager
    "ForkGroupManager",
    # From orka.loader
    "YAMLLoader",
    # From orka.memory_logger
    "RedisMemoryLogger",
    "MemoryLogger",
    # From orka.nodes
    "BaseNode",
    "FailingNode",
    "FailoverNode",
    "ForkNode",
    "JoinNode",
    "LoopNode",
    "LoopValidatorNode",
    "MemoryReaderNode",
    "MemoryWriterNode",
    "PathExecutorNode",
    "RAGNode",
    "RouterNode",
    # From orka.orchestrator
    "Orchestrator",
    # From orka.orka_cli (which is orka.cli)
    "run_cli_entrypoint",
    "setup_logging",
    "memory_cleanup",
    "memory_configure",
    "memory_stats",
    "memory_watch",
    "_memory_watch_display",
    "_memory_watch_fallback",
    "_memory_watch_json",
    "run_orchestrator",
    "create_parser",
    "setup_subcommands",
    "Event",
    "EventPayload",
]