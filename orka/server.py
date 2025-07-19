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
```python
app = FastAPI(
    title="OrKa AI Orchestration API",
    description="High-performance API gateway for AI workflow orchestration",
    version="1.0.0"
)
```

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
```python
# Input: b"binary data"
# Output: {"__type": "bytes", "data": "YmluYXJ5IGRhdGE="}
```

**DateTime Handling:**
```python
# Input: datetime(2024, 1, 1, 12, 0, 0)
# Output: "2024-01-01T12:00:00"
```

**Custom Object Handling:**
```python
# Input: CustomClass(attr="value")
# Output: {"__type": "CustomClass", "data": {"attr": "value"}}
```

Deployment Configuration
-----------------------

**Environment Variables**
- `ORKA_PORT`: Server port (default: 8001)
- Standard FastAPI/Uvicorn environment variables

**Production Deployment**
```bash
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
```python
import httpx

async def call_orka_api(input_text: str, workflow_config: str):
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8001/api/run", json={
            "input": input_text,
            "yaml_config": workflow_config
        })
        return response.json()
```

**Microservice Integration**
```python
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
```

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
from datetime import datetime
from typing import Any, Dict

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize Python objects for JSON serialization.

    Args:
        obj: Any Python object to sanitize.

    Returns:
        JSON-serializable version of the object.
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, bytes):
        return {
            "__type": "bytes",
            "data": base64.b64encode(obj).decode("utf-8"),
        }
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__"):
        return {
            "__type": obj.__class__.__name__,
            "data": sanitize_for_json(obj.__dict__),
        }
    else:
        return str(obj)


@app.post("/api/run")
async def run_execution(request: Request) -> JSONResponse:
    """
    Execute an OrKa workflow with the provided input and configuration.

    Args:
        request: FastAPI request object containing input text and YAML configuration.

    Returns:
        JSONResponse containing the execution results or error information.
    """
    try:
        # Parse request body
        body: Dict[str, Any] = await request.json()
        input_text: str = body.get("input", "")
        yaml_config: str = body.get("yaml_config", "")

        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", encoding="utf-8", delete=False
        ) as temp_yaml:
            temp_yaml.write(yaml_config)
            temp_yaml_path: str = temp_yaml.name

        try:
            # Initialize and run orchestrator
            orchestrator = Orchestrator(temp_yaml_path)
            result: Dict[str, Any] = await orchestrator.run({"input": input_text})

            # Sanitize result for JSON serialization
            sanitized_result: Dict[str, Any] = sanitize_for_json(result)

            # Return successful response
            return JSONResponse(
                content={
                    "input": input_text,
                    "execution_log": sanitized_result,
                    "log_file": (
                        orchestrator.log_file if hasattr(orchestrator, "log_file") else None
                    ),
                },
                status_code=200,
            )

        except Exception as e:
            # Handle orchestrator execution errors
            err_msg: str = f"Error during orchestrator execution: {str(e)}"
            logger.error(err_msg)
            return JSONResponse(
                content={
                    "input": input_text,
                    "error": err_msg,
                    "summary": pprint.pformat(e.__dict__ if hasattr(e, "__dict__") else str(e)),
                },
                status_code=500,
            )

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_yaml_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary YAML file: {e}")

    except Exception as e:
        # Handle request parsing errors
        error_msg: str = f"Error parsing request: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(
            content={
                "error": error_msg,
                "summary": pprint.pformat(e.__dict__ if hasattr(e, "__dict__") else str(e)),
            },
            status_code=400,
        )


if __name__ == "__main__":
    # Get port from environment variable or use default
    port: int = int(os.getenv("ORKA_PORT", "8001"))

    # Run server
    uvicorn.run(
        "orka.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
    )
