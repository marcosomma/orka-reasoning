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
Type Contracts
=============

This module defines the core data structures and type contracts used throughout the
OrKa framework. These TypedDict classes establish a consistent interface for data
exchange between components, ensuring type safety and providing documentation on
the expected structure of data objects.

The contracts defined here serve several purposes:
1. Type checking and validation at development time
2. Documentation of data structure requirements
3. Standardization of interfaces between components
4. Support for IDE autocompletion and code navigation

These contracts are essential for maintaining a clean architecture and ensuring
that components can be composed reliably with predictable data formats.
"""

from datetime import datetime
from typing import Any, Dict, Optional, TypedDict


class Context(TypedDict, total=False):
    """
    Core context passed to all nodes during execution.

    This is the primary data structure that flows through the OrKa pipeline,
    containing input data, accumulated outputs from previous nodes, and
    execution metadata.

    Attributes:
        input: The original query or input text to process
        previous_outputs: Results from previously executed nodes in the pipeline
        metadata: Additional information about the execution context
        trace_id: Unique identifier for tracing the execution path
        timestamp: When this context was created or last updated
    """

    input: str
    previous_outputs: Dict[str, Any]
    metadata: Dict[str, Any]
    trace_id: Optional[str]
    timestamp: datetime


class Output(TypedDict):
    """
    Standard output format for all nodes.

    Defines a consistent structure for node execution results, including
    success/failure status and relevant metadata.

    Attributes:
        result: The primary output data from the node execution
        status: Execution status - "success" or "error"
        error: Error message if status is "error", otherwise None
        metadata: Additional information about the execution result
    """

    result: Any
    status: str  # "success" | "error"
    error: Optional[str]
    metadata: Dict[str, Any]


class ResourceConfig(TypedDict):
    """
    Configuration for a resource in the registry.

    Defines how external resources like LLMs, embedders, and databases
    should be initialized and configured.

    Attributes:
        type: The resource type identifier (e.g., "openai", "sentence-transformer")
        config: Configuration parameters specific to the resource type
    """

    type: str
    config: Dict[str, Any]


class Registry(TypedDict):
    """
    Resource registry containing all available resources.

    Provides a central location for accessing shared resources like
    language models, embedding models, and memory systems.

    Attributes:
        embedder: Text embedding model (e.g., SentenceTransformer)
        llm: Language model client
        memory: Memory storage and retrieval system
        tools: Dictionary of additional tool resources
    """

    embedder: Any  # SentenceTransformer or similar
    llm: Any  # LLM client
    memory: Any  # Memory client
    tools: Dict[str, Any]  # Custom tools


class Trace(TypedDict):
    """
    Execution trace for debugging and monitoring.

    Records detailed information about each step in the execution pipeline
    for auditing, debugging, and performance analysis.

    Attributes:
        v: Schema version number
        trace_id: Unique identifier for this trace
        agent_id: Identifier of the agent/node that generated this trace
        timestamp: When this trace was created
        input: The input data provided to the agent/node
        output: The output produced by the agent/node
        metadata: Additional contextual information
    """

    v: int  # Schema version
    trace_id: str
    agent_id: str
    timestamp: datetime
    input: Dict[str, Any]
    output: Dict[str, Any]
    metadata: Dict[str, Any]


class MemoryEntry(TypedDict):
    """
    Single memory entry with importance score.

    Represents a piece of information stored in the memory system,
    with metadata about its importance and origin.

    Attributes:
        content: The actual text content of the memory
        importance: Numerical score indicating the memory's importance (0.0-1.0)
        timestamp: When this memory was created or last updated
        metadata: Additional information about the memory's source and context
        is_summary: Whether this entry is a summary of other memories
    """

    content: str
    importance: float
    timestamp: datetime
    metadata: Dict[str, Any]
    is_summary: bool
