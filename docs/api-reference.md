# OrKa API Reference

Complete API documentation for OrKa's core components, including classes, methods, and configuration options.

## Table of Contents

1. [Core Components](#core-components)
   - [Orchestrator](#orchestrator)
   - [Memory System](#memory-system)
   - [Nodes](#nodes)
   - [Agents](#agents)
2. [Configuration](#configuration)
   - [YAML Schema](#yaml-schema)
   - [Environment Variables](#environment-variables)
3. [Memory Backend](#memory-backend)
   - [RedisStack](#redisstack)
4. [CLI Reference](#cli-reference)
5. [HTTP API](#http-api)

## Core Components

### Orchestrator

The orchestrator is the central component that manages workflow execution, agent coordination, and memory operations.

#### OrchestratorBase

Base class providing core infrastructure and configuration management.

```python
class OrchestratorBase:
    """
    Base orchestrator class that handles initialization and configuration.

    Attributes:
        loader (YAMLLoader): Configuration file loader and validator
        orchestrator_cfg (dict): Orchestrator-specific configuration
        agent_cfgs (list): List of agent configuration objects
        memory: Memory backend instance
        fork_manager: Fork group manager for parallel execution
        queue (list): Current agent execution queue
        run_id (str): Unique identifier for this run
        step_index (int): Current step counter
        error_telemetry (dict): Error tracking and metrics
    """

    def __init__(self, config_path: str) -> None:
        """Initialize with YAML config file."""

    def enqueue_fork(self, agent_ids: list[str], fork_group_id: str) -> None:
        """Enqueue a fork group for parallel execution."""
```

### Memory System

OrKa's memory system provides intelligent storage and retrieval with 100x faster vector search.

#### RedisStackMemoryLogger

Enterprise-grade memory management with HNSW indexing.

```python
class RedisStackMemoryLogger(BaseMemoryLogger):
    """
    Enhanced memory logger using RedisStack with HNSW indexing.

    Features:
        - 100x faster vector search with HNSW
        - Intelligent memory classification
        - Automatic index optimization
        - Comprehensive metadata management
    """

    def write(
        self,
        namespace: str,
        content: str,
        vector: bool = True,
        metadata: dict = None
    ) -> str:
        """
        Store information with vector embeddings.

        Args:
            namespace: Memory namespace
            content: Content to store
            vector: Enable vector embeddings
            metadata: Additional metadata

        Returns:
            str: Memory entry ID
        """

    def search(
        self,
        namespace: str,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.8
    ) -> list[dict]:
        """
        Perform semantic search with HNSW indexing.

        Args:
            namespace: Memory namespace to search
            query: Search query
            limit: Maximum results
            similarity_threshold: Minimum similarity

        Returns:
            list[dict]: Matching memories with scores
        """
```

### Nodes

Specialized components for workflow operations.

#### LoopNode

Enables iterative improvement workflows.

```python
class LoopNode(BaseNode):
    """
    Executes an internal workflow repeatedly until conditions are met.

    Features:
        - Iterative execution with thresholds
        - Cognitive insight extraction
        - Learning from past iterations
        - Automatic termination
    """

    def run(self, input_data: dict) -> dict:
        """
        Execute the loop workflow.

        Args:
            input_data: Input for the workflow

        Returns:
            dict: Final results with learning insights
        """
```

#### MemoryWriterNode

Stores information with intelligent classification.

```python
class MemoryWriterNode(BaseNode):
    """
    Stores information in OrKa's memory system.

    Features:
        - Automatic memory classification
        - Vector embeddings for search
        - Configurable metadata
        - Intelligent decay
    """

    def run(self, input_data: dict) -> dict:
        """
        Store information in memory.

        Args:
            input_data: Content and metadata to store

        Returns:
            dict: Storage results and metadata
        """
```

#### MemoryReaderNode

Retrieves information using semantic search.

```python
class MemoryReaderNode(BaseNode):
    """
    Retrieves information using semantic search.

    Features:
        - 100x faster semantic search
        - Context-aware retrieval
        - Temporal ranking
        - Configurable thresholds
    """

    def run(self, input_data: dict) -> dict:
        """
        Search memory with vector similarity.

        Args:
            input_data: Search query and parameters

        Returns:
            dict: Search results with metadata
        """
```

### Agents

AI agents that perform specific tasks in workflows.

#### OpenAIAgent

Interacts with OpenAI's API for various tasks.

```python
class OpenAIAgent(BaseAgent):
    """
    OpenAI-powered agent for various tasks.

    Features:
        - Multiple task types (classification, Q&A, etc.)
        - Context management
        - Error handling
        - Rate limiting
    """

    def run(self, input_data: dict) -> dict:
        """
        Execute the agent's task.

        Args:
            input_data: Task input and parameters

        Returns:
            dict: Task results
        """
```

## Configuration

### YAML Schema

OrKa workflows are defined in YAML with the following structure:

```yaml
meta:
  version: "1.0"
  description: "Workflow description"

orchestrator:
  id: workflow-name
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168

agents:
  - id: agent-name
    type: agent-type
    params:
      key: value
    prompt: "Agent prompt template"
```

### Environment Variables

Key environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| OPENAI_API_KEY | OpenAI API key | Required |
| REDIS_URL | Redis connection URL | redis://localhost:6380/0 |
| ORKA_MEMORY_BACKEND | Memory backend type | redisstack |
| ORKA_MEMORY_DECAY_ENABLED | Enable memory decay | false |
| ORKA_MEMORY_DECAY_SHORT_TERM_HOURS | Short-term retention | 2 |
| ORKA_MEMORY_DECAY_LONG_TERM_HOURS | Long-term retention | 168 |
| ORKA_MAX_CONCURRENT_REQUESTS | Max concurrent operations | 100 |
| ORKA_TIMEOUT_SECONDS | Operation timeout | 300 |

## Memory Backend

### RedisStack

Primary memory backend with HNSW vector search.

Configuration:
```yaml
memory_config:
  backend: redisstack
  redis_url: redis://localhost:6380/0
  enable_hnsw: true
  vector_params:
    M: 16
    ef_construction: 200
    ef_runtime: 10
```

Performance:
- Vector Search: 0.5-5ms
- Memory Usage: 40% of basic Redis
- Concurrent Searches: 1000+
- Index Updates: Automatic

```

Features:
- Streaming memory operations
- Schema validation
- High availability
- Scalable throughput

## CLI Reference

### Core Commands

```bash
# Run a workflow
orka run workflow.yml "input text"

# Monitor memory performance
orka memory watch
orka memory stats

# Clean up expired memories
orka memory cleanup

# Start OrKa services
orka-start      # Development (Redis)
orka-start      # Deployment example (RedisStack)

# Check system health
orka system status
```

### Memory Management

```bash
# View memory configuration
orka memory configure

# Search memories
orka memory search "query"

# Export memories
orka memory export namespace

# Import memories
orka memory import namespace file.json
```

### Workflow Management

```bash
# Validate workflow
orka validate workflow.yml

# List running workflows
orka list workflows

# Stop workflow
orka stop workflow-id

# Show workflow status
orka status workflow-id
```

For more detailed information about specific components or features, check the following guides:
- [Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)
- [Agent Development Guide](./agents.md)
- [Production Deployment Guide](./runtime-modes.md)
- [Security Guide](./security.md)

## HTTP API

The OrKa FastAPI server exposes endpoints for orchestration and health monitoring. Default port is 8001 (configurable via `ORKA_PORT`).

### POST /api/run

Execute a workflow.

Request body:

```json
{
    "input": "Your input text here",
    "yaml_config": "orchestrator:\n  id: example\n  agents: [agent1]\nagents:\n  - id: agent1\n    type: openai-answer"
}
```

Response: JSON object containing sanitized execution logs.

### GET /api/health

Deep health report for server and memory backend.

Example response:

```json
{
    "status": "healthy",
    "version": { "orka": "unknown" },
    "system": {
        "python": "3.12.12",
        "platform": "Windows-10-10.0.19045-SP0",
        "pid": 12345,
        "uptime_seconds": 42,
        "rss_mb": 123.45,
        "threads": 12,
        "cpu_percent": 3.1,
        "memory": { "percent": 45.6, "total_mb": 16384.0, "available_mb": 8921.2 },
        "disk": { "percent": 70.2, "total_mb": 512000.0, "free_mb": 152000.0 }
    },
    "memory": {
        "backend": "redisstack",
        "url": "redis://localhost:6380/0",
        "connected": true,
        "ping_ms": 2.1,
        "set_get_ms": 3.4,
        "roundtrip_ok": true,
        "search_module": true,
        "index_list": ["orka_enhanced_memory"],
        "errors": []
    }
}
```

Status rules:
- `critical`: Redis not connected
- `degraded`: Connected but SET/GET roundtrip failed
- `healthy`: Connected and roundtrip OK

Notes:
- Redis URL is sanitized (credentials removed).
- Extended metrics are best-effort and may be omitted if `psutil` is unavailable.

### GET /health

Lightweight liveness probe. Returns `{ "status": "healthy|degraded|critical" }` with HTTP 200 unless `critical` (503).