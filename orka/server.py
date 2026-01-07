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
OrKa Server - FastAPI Web Server
===============================

FastAPI server that exposes OrKa workflows through RESTful APIs. This server is provided as an example deployment; production hardening is required prior to use in critical environments.

Core Features
------------

**API Gateway Functionality**
- RESTful endpoints for workflow execution
- JSON request/response handling with intelligent sanitization
- CORS middleware for cross-origin requests
- Comprehensive error handling and logging

**Data Processing**
- Intelligent JSON sanitization for complex Python objects
- Automatic handling of bytes, datetime, and custom objects
- Base64 encoding for binary data transmission
- Type preservation with metadata for complex structures

**Deployment Considerations**

Assumptions: See `docs/production-readiness.md` for hardening guidance.
- FastAPI framework with automatic OpenAPI documentation
- Uvicorn ASGI server for high-performance async handling
- Configurable port binding with environment variable support
- Graceful error handling with fallback responses

Architecture Details
-------------------

**Request Processing Flow**
1. **Request Reception**: FastAPI receives POST requests at `/api/run`
2. **Data Extraction**: Extract input text and YAML configuration
3. **Temporary File Creation**: Create temporary YAML file with UTF-8 encoding
4. **Orchestrator Instantiation**: Initialize orchestrator with configuration
5. **Workflow Execution**: Run orchestrator with input data
6. **Response Sanitization**: Convert complex objects to JSON-safe format
7. **Cleanup**: Remove temporary files and return response

**JSON Sanitization System**
The server includes a data sanitization system for API responses.

- **Primitive Types**: Direct passthrough for strings, numbers, booleans
- **Bytes Objects**: Base64 encoding with type metadata
- **DateTime Objects**: ISO format conversion for universal compatibility
- **Custom Objects**: Introspection and dictionary conversion
- **Collections**: Recursive processing of lists and dictionaries
- **Fallback Handling**: Safe string representations for non-serializable objects

**Error Handling**
- Comprehensive exception catching with detailed logging
- Graceful degradation for serialization failures
- Fallback responses with error context
- HTTP status codes for different error types

Assumptions:
- This server is an example deployment and requires TLS, secrets management, and load balancing to be production-ready.

Proof: See `docs/INTEGRATION_EXAMPLES.md` and `docs/production-readiness.md` for required hardening and tests.

Implementation Details
---------------------

**FastAPI Configuration**

.. code-block:: python

    app = FastAPI(
        title="OrKa AI Orchestration API",
        description="High-performance API gateway for AI workflow orchestration",
        version="1.0.0"
    )

**CORS Configuration**
- Permissive CORS for development environments
- Configurable origins, methods, and headers
- Credential support for authenticated requests

**Temporary File Handling**
- UTF-8 encoding for international character support
- Secure temporary file creation with proper cleanup
- Error handling for file operations

API Endpoints
------------

**POST /api/run**
Execute OrKa workflows with dynamic configuration.

**Request Format:**
```json
{
    "input": "Your input text here",
    "yaml_config": "orchestrator:\\n  id: example\\n  agents: [agent1]\\nagents:\\n  - id: agent1\\n    type: openai-answer"
}
```

**Response Format:**
```json
{
    "input": "Your input text here",
    "execution_log": {
        "orchestrator_result": "...",
        "agent_outputs": {...},
        "metadata": {...}
    },
    "log_file": {...}
}
```

**Error Response:**
```json
{
    "input": "Your input text here",
    "error": "Error description",
    "summary": "Error summary for debugging"
}
```

Data Sanitization Examples
--------------------------

**Bytes Handling:**

.. code-block:: python

    # Input: b"binary data"
    # Output: {"__type": "bytes", "data": "YmluYXJ5IGRhdGE="}

**DateTime Handling:**

.. code-block:: python

    # Input: datetime(2024, 1, 1, 12, 0, 0)
    # Output: "2024-01-01T12:00:00"

**Custom Object Handling:**

.. code-block:: python

    # Input: CustomClass(attr="value")
    # Output: {"__type": "CustomClass", "data": {"attr": "value"}}

Deployment Configuration
-----------------------

**Environment Variables**
- `ORKA_PORT`: Server port (default: 8001)
- Standard FastAPI/Uvicorn environment variables

**Production Deployment (requires hardening and validation)**

.. code-block:: bash

    # Direct execution
    python -m orka.server

# With custom port
ORKA_PORT=8080 python -m orka.server

# Production deployment with Uvicorn
uvicorn orka.server:app --host 0.0.0.0 --port 8000 --workers 4
```

**Docker Deployment**
```dockerfile
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "orka.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Integration Examples
-------------------

**Client Integration**

.. code-block:: python



    async def call_orka_api(input_text: str, workflow_config: str):
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8001/api/run", json={
                "input": input_text,
                "yaml_config": workflow_config
            })
            return response.json()

**Microservice Integration**

.. code-block:: python

    from fastapi import FastAPI
    import httpx

    app = FastAPI()

    @app.post("/process")
    async def process_request(request: dict):
        # Forward to OrKa server
        async with httpx.AsyncClient() as client:
            orka_response = await client.post("http://orka-server:8001/api/run", json={
                "input": request["text"],
                "yaml_config": request["workflow"]
            })
            return orka_response.json()

Performance Considerations
-------------------------

**Scalability Features**
- Async request handling for high concurrency
- Stateless design for horizontal scaling
- Efficient memory management with temporary file cleanup
- Fast JSON serialization with optimized sanitization

**Resource Management**
- Temporary file cleanup prevents disk space leaks
- Memory-efficient processing of large responses
- Connection pooling through FastAPI/Uvicorn
- Graceful error handling prevents resource locks

**Monitoring and Debugging**
- Comprehensive request/response logging
- Detailed error context for troubleshooting
- Performance metrics through FastAPI integration
- OpenAPI documentation for API exploration
"""

import base64
import time
import sys
import platform
from urllib.parse import urlparse, urlunparse
import logging
import os
import pprint
import tempfile
from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Optional

# Optional imports guarded to avoid hard failures in constrained environments
try:  # psutil is in project dependencies; guard anyway for robustness
    import psutil  # type: ignore
except Exception:  # pragma: no cover - fallback if psutil import fails
    psutil = None  # type: ignore

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore

from orka.orchestrator import Orchestrator
from orka.startup.banner import get_version as _get_orka_version

app = FastAPI(
    title="OrKa AI Orchestration API",
    description="[START] High-performance API gateway for AI workflow orchestration",
    version="1.0.0",
)
logger = logging.getLogger(__name__)

# Track server start time for uptime reporting
app.state.start_time = time.time()

# Ensure server logs are visible when launched via orka-start or as a module
try:
    # Configure logging only if nothing has configured it yet
    if not logging.root.handlers:
        from orka.cli.utils import setup_logging as _orka_setup_logging

        _orka_setup_logging()
except Exception:
    # Aim to avoid server startup failures due to logging configuration issues; verify logging configuration in deployment.
    pass

# CORS (optional, but useful if UI and API are on different ports during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sanitize_for_json(obj: Any) -> Any:
    """
    [CLEAN] **Intelligent JSON sanitizer** - handles complex objects for API responses.

    **What makes sanitization smart:**
    - **Type Intelligence**: Automatically handles datetime, bytes, and custom objects
    - **Recursive Processing**: Deep sanitization of nested structures
    - **Fallback Safety**: Graceful handling of non-serializable objects
    - **Performance Optimized**: Efficient processing of large data structures

    **Sanitization Patterns:**
    - **Bytes**: Converted to base64-encoded strings with type metadata
    - **Datetime**: ISO format strings for universal compatibility
    - **Custom Objects**: Introspected and converted to structured dictionaries
    - **Non-serializable**: Safe string representations with type information

    **Perfect for:**
    - API responses containing complex agent outputs
    - Memory objects with mixed data types
    - Debug information with arbitrary Python objects
    - Cross-platform data exchange requirements
    """
    try:
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, bytes):
            # Convert bytes to base64-encoded string
            return {"__type": "bytes", "data": base64.b64encode(obj).decode("utf-8")}
        elif isinstance(obj, (list, tuple)):
            return [sanitize_for_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {str(k): sanitize_for_json(v) for k, v in obj.items()}
        elif hasattr(obj, "isoformat"):  # Handle datetime-like objects
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):  # Handle custom objects
            try:
                # Handle custom objects by converting to dict
                return {
                    "__type": obj.__class__.__name__,
                    "data": sanitize_for_json(obj.__dict__),
                }
            except Exception as e:
                return f"<non-serializable object: {obj.__class__.__name__}, error: {e!s}>"
        else:
            # Last resort - convert to string
            return f"<non-serializable: {type(obj).__name__}>"
    except Exception as e:
        logger.warning(f"Failed to sanitize object for JSON: {e!s}")
        return f"<sanitization-error: {e!s}>"


def _sanitize_url(url: str) -> str:
    """
    Remove credentials from URLs to avoid leaking secrets in health output.

    Examples:
        redis://:password@localhost:6380/0 -> redis://localhost:6380/0
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
            # Rebuild ParseResult without userinfo
            sanitized = parsed._replace(netloc=netloc)
        return urlunparse(sanitized)
    except Exception:
        return "<redacted>"


async def _check_memory_health() -> Dict[str, Any]:
    """Perform connectivity and basic performance checks against Redis/RedisStack.

    Returns a JSON-serializable dict with connection status, latencies, and optional
    RedisStack index visibility if the module is available.
    """
    details: Dict[str, Any] = {
        "backend": os.getenv("ORKA_MEMORY_BACKEND", "redisstack"),
        "url": None,
        "connected": False,
        "ping_ms": None,
        "set_get_ms": None,
        "roundtrip_ok": None,
        "search_module": None,
        "index_list": None,
        "errors": [],
    }

    # Determine target URL (same defaults used across the project)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    details["url"] = _sanitize_url(redis_url)

    if aioredis is None:
        details["errors"].append("redis.asyncio not available")
        return details

    client: Optional[aioredis.Redis] = None  # type: ignore[name-defined]
    try:
        # Use default UTF-8 encoding to avoid encode() errors from redis-py when handling str keys
        # (passing encoding=None can break key encoding on some redis-py versions)
        # Use default encoding; avoid passing None which can cause runtime encode errors
        client = aioredis.from_url(redis_url, decode_responses=False)  # type: ignore[attr-defined]

        # 1) Ping latency
        t0 = time.perf_counter()
        pong = await client.ping()
        t1 = time.perf_counter()
        details["ping_ms"] = round((t1 - t0) * 1000.0, 2)
        details["connected"] = bool(pong)

        # 2) Small SET/GET roundtrip
        key = f"orka:health:probe:{int(time.time()*1000)}"
        t0 = time.perf_counter()
        await client.set(key, b"ok", ex=5)
        val = await client.get(key)
        t1 = time.perf_counter()
        details["set_get_ms"] = round((t1 - t0) * 1000.0, 2)
        details["roundtrip_ok"] = val == b"ok"

        # 3) Try to check RediSearch availability (RedisStack)
        try:
            idx = await client.execute_command("FT._LIST")  # type: ignore[no-untyped-call]
            # idx can be a list of bytes index names
            if isinstance(idx, (list, tuple)):
                details["search_module"] = True
                try:
                    details["index_list"] = [i.decode("utf-8") if isinstance(i, (bytes, bytearray)) else str(i) for i in idx]
                except Exception:
                    details["index_list"] = "<unavailable>"
            else:
                details["search_module"] = False
        except Exception as e:  # Module may not be loaded
            details["search_module"] = False
            details["errors"].append(f"FT._LIST failed: {e!s}")

    except Exception as e:
        details["errors"].append(f"connection failed: {e!s}")
        details["connected"] = False
    finally:
        try:
            if client is not None:
                await client.close()  # type: ignore[func-returns-value]
        except Exception:
            pass

    return details


def _overall_status(memory: Dict[str, Any]) -> str:
    """Derive overall health from memory metrics."""
    if not memory.get("connected"):
        return "critical"
    # Prefer functional signal over timing to avoid false degradations in CI
    roundtrip_ok = memory.get("roundtrip_ok")
    if roundtrip_ok is False:
        return "degraded"
    return "healthy"


@app.get("/api/health")
async def api_health() -> JSONResponse:
    """Deep health report for OrKa server and memory backend."""
    try:
        mem = await _check_memory_health()
        status = _overall_status(mem)

        # System info
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        try:
            ver = _get_orka_version()
        except Exception:
            ver = "unknown"

        uptime_s = max(0, time.time() - getattr(app.state, "start_time", time.time()))

        system_info = {
            "python": py_ver,
            "platform": platform.platform(),
            "pid": os.getpid(),
            "uptime_seconds": int(uptime_s),
        }

        if psutil is not None:
            try:
                proc = psutil.Process(os.getpid())
                with proc.oneshot():
                    mem_info = proc.memory_info()
                    system_info["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
                    system_info["threads"] = proc.num_threads()
                # Optional extended metrics (best-effort)
                try:
                    system_info["cpu_percent"] = psutil.cpu_percent(interval=0.0)
                except Exception:
                    pass
                try:
                    vm = psutil.virtual_memory()
                    system_info["memory"] = {
                        "percent": vm.percent,
                        "total_mb": round(vm.total / (1024 * 1024), 2),
                        "available_mb": round(vm.available / (1024 * 1024), 2),
                    }
                except Exception:
                    pass
                try:
                    # Pick current drive root for portability (Windows/Linux)
                    cwd = os.getcwd()
                    root = os.path.splitdrive(cwd)[0] + os.sep if os.name == "nt" else "/"
                    du = psutil.disk_usage(root)
                    system_info["disk"] = {
                        "percent": du.percent,
                        "total_mb": round(du.total / (1024 * 1024), 2),
                        "free_mb": round(du.free / (1024 * 1024), 2),
                    }
                except Exception:
                    pass
            except Exception:
                pass

        payload = {
            "status": status,
            "version": {"orka": ver},
            "system": system_info,
            "memory": mem,
        }

        return JSONResponse(content=payload, status_code=200 if status != "critical" else 503)
    except Exception as e:
        logger.error(f"Health endpoint error: {e!s}")
        return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)


@app.get("/health")
async def health_basic() -> JSONResponse:
    """Lightweight liveness probe. Returns overall status only."""
    mem = await _check_memory_health()
    status = _overall_status(mem)
    return JSONResponse(content={"status": status}, status_code=200 if status != "critical" else 503)


# API endpoint at /api/run
@app.post("/api/run")
async def run_execution(request: Request):
    tmp_path = None
    try:
        data = await request.json()
        logger.info("\n========== [DEBUG] Incoming POST /api/run ==========")
        print(data)

        input_text = data.get("input")
        yaml_config = data.get("yaml_config")

        logger.info("\n========== [DEBUG] YAML Config String ==========")
        logger.info(yaml_config)

        # Create a temporary file path with UTF-8 encoding
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".yml")
        os.close(tmp_fd)  # Close the file descriptor

        # Write with explicit UTF-8 encoding
        with open(tmp_path, "w", encoding="utf-8") as tmp:
            tmp.write(yaml_config)

        logger.info("\n========== [DEBUG] Instantiating Orchestrator ==========")
        orchestrator = Orchestrator(tmp_path)
        logger.info(f"Orchestrator: {orchestrator}")

        logger.info("\n========== [DEBUG] Running Orchestrator ==========")
        result = await orchestrator.run(input_text, return_logs=True)

        logger.info("\n========== [DEBUG] Orchestrator Result ==========")
        print(result)

        # Sanitize the result data for JSON serialization
        sanitized_result = sanitize_for_json(result)

        return JSONResponse(
            content={
                "input": input_text,
                "execution_log": sanitized_result,
                "log_file": sanitized_result,
            },
        )
    except Exception as e:
        logger.error(f"Error creating JSONResponse: {e!s}")
        # Fallback response with minimal data
        return JSONResponse(
            content={
                "input": data.get("input") if 'data' in locals() else 'N/A',
                "error": f"Error creating response: {e!s}",
                "summary": "Execution completed but response contains non-serializable data",
            },
            status_code=500,
        )
    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception as e:
                logger.warning(f"Warning: Failed to remove temporary file {tmp_path}: {e!s}")


def main():
    # Get port from environment variable, default to 8000
    port = int(os.environ.get("ORKA_PORT", 8001))  # Default to 8001 to avoid conflicts
    # Import uvicorn only when running the server to avoid test-time dependency on 'click'
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
