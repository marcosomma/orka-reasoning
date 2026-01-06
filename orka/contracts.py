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
        formatted_prompt: Optional rendered prompt with template variables resolved
    """

    input: str
    previous_outputs: Dict[str, Any]
    metadata: Dict[str, Any]
    trace_id: Optional[str]
    timestamp: datetime
    formatted_prompt: Optional[str]

    # Agent-specific fields
    prompt: Optional[str]
    model: Optional[str]
    temperature: Optional[float]
    parse_json: Optional[bool]
    error_tracker: Optional[Any]
    agent_id: Optional[str]

    # Additional context fields
    question: Optional[str]
    full_context: Optional[str]
    latest_answer: Optional[str]
    store_structure: Optional[Any]


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
        category: Category for memory separation (log, stored, etc.)
    """

    content: str
    importance: float
    timestamp: datetime
    metadata: Dict[str, Any]
    is_summary: bool
    category: Optional[str]


class OrkaResponse(TypedDict, total=False):
    """
    Universal response format for all Orka components (agents, nodes, tools).

    This standardized response structure ensures consistent data flow throughout
    the OrKa framework, simplifying logging, template rendering, and debugging.
    All components must return this format to enable seamless composition.

    Core fields (required):
        result: The primary output data from the component
        status: Execution status - "success", "error", or "partial"
        component_id: Unique identifier of the component that generated this response
        component_type: Type of component - "agent", "node", or "tool"
        timestamp: When this response was generated

    Optional fields:
        error: Error message if status is "error"
        metadata: Additional information about the execution
        execution_time_ms: How long the execution took in milliseconds
        token_usage: Token consumption statistics for LLM calls
        cost_usd: Estimated cost in USD for this execution
        formatted_prompt: The actual prompt sent to LLMs after template rendering
        confidence: Confidence level in the result ("high", "medium", "low")
        internal_reasoning: Chain-of-thought or reasoning process
        trace_id: Unique identifier for tracing execution paths
        memory_entries: Memories created or accessed during execution
        sources: Source documents or references used
        metrics: Additional metrics and performance data
    """

    # Core fields (required)
    result: Any
    status: str  # "success" | "error" | "partial"
    component_id: str
    component_type: str  # "agent" | "node" | "tool"
    timestamp: datetime

    # Optional fields
    error: Optional[str]
    metadata: Dict[str, Any]
    execution_time_ms: Optional[float]
    token_usage: Optional[Dict[str, int]]
    cost_usd: Optional[float]
    formatted_prompt: Optional[str]
    confidence: Optional[str]
    internal_reasoning: Optional[str]
    trace_id: Optional[str]
    memory_entries: Optional[list]
    sources: Optional[list]
    metrics: Dict[str, Any]
