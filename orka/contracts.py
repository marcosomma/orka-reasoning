from datetime import datetime
from typing import Any, Dict, Optional, TypedDict


class Context(TypedDict, total=False):
    """Core context passed to all nodes during execution."""

    input: str
    previous_outputs: Dict[str, Any]
    metadata: Dict[str, Any]
    trace_id: Optional[str]
    timestamp: datetime


class Output(TypedDict):
    """Standard output format for all nodes."""

    result: Any
    status: str  # "success" | "error"
    error: Optional[str]
    metadata: Dict[str, Any]


class ResourceConfig(TypedDict):
    """Configuration for a resource in the registry."""

    type: str
    config: Dict[str, Any]


class Registry(TypedDict):
    """Resource registry containing all available resources."""

    embedder: Any  # SentenceTransformer or similar
    llm: Any  # LLM client
    memory: Any  # Memory client
    tools: Dict[str, Any]  # Custom tools


class Trace(TypedDict):
    """Execution trace for debugging and monitoring."""

    v: int  # Schema version
    trace_id: str
    agent_id: str
    timestamp: datetime
    input: Dict[str, Any]
    output: Dict[str, Any]
    metadata: Dict[str, Any]


class MemoryEntry(TypedDict):
    """Single memory entry with importance score."""

    content: str
    importance: float
    timestamp: datetime
    metadata: Dict[str, Any]
    is_summary: bool
