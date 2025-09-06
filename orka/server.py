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
OrKa Server - FastAPI Web Server
===============================

Production-ready FastAPI server that exposes OrKa workflows through RESTful APIs.
Transforms AI workflows into scalable web services with comprehensive data handling.

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

**Production Features**
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
The server includes sophisticated data sanitization for API responses:

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

**Production Deployment**

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

    import httpx

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
import logging
import os
import pprint
import tempfile
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orka.orchestrator import Orchestrator

app = FastAPI(
    title="OrKa AI Orchestration API",
    description="🚀 High-performance API gateway for AI workflow orchestration",
    version="1.0.0",
)
logger = logging.getLogger(__name__)

# Ensure server logs are visible when launched via orka-start or as a module
try:
    # Configure logging only if nothing has configured it yet
    if not logging.root.handlers:
        from orka.cli.utils import setup_logging as _orka_setup_logging

        _orka_setup_logging()
except Exception:
    # Never fail server startup due to logging configuration issues
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
    🧹 **Intelligent JSON sanitizer** - handles complex objects for API responses.

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


# API endpoint at /api/run
@app.post("/api/run")
async def run_execution(request: Request):
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

    # Clean up the temporary file
    try:
        os.remove(tmp_path)
    except Exception:
        logger.info(f"Warning: Failed to remove temporary file {tmp_path}")

    logger.info("\n========== [DEBUG] Orchestrator Result ==========")
    print(result)

    # Sanitize the result data for JSON serialization
    sanitized_result = sanitize_for_json(result)

    try:
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
                "input": input_text,
                "error": f"Error creating response: {e!s}",
                "summary": "Execution completed but response contains non-serializable data",
            },
            status_code=500,
        )


if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port = int(os.environ.get("ORKA_PORT", 8001))  # Default to 8001 to avoid conflicts
    uvicorn.run(app, host="0.0.0.0", port=port)
