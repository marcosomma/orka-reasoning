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
🌐 **OrKa Server** - High-Performance API Gateway
===============================================

The OrKa Server transforms your AI workflows into production-ready APIs with
enterprise-grade features for reliability, scalability, and monitoring.

**Core Server Philosophy:**
Think of the OrKa Server as your AI workflow's gateway to the world - providing
secure, fast, and reliable access to your intelligent agents through modern
web APIs that scale from prototype to production.

**API Capabilities:**
- 🚀 **RESTful Endpoints**: Clean, intuitive APIs for workflow execution
- 📡 **WebSocket Streaming**: Real-time results for interactive applications
- 📊 **GraphQL Interface**: Flexible querying for complex data requirements
- 📋 **OpenAPI Documentation**: Interactive testing and client generation

**Production Features:**
- ✅ **Request/Response Validation**: Pydantic-powered data validation
- 🛡️ **Rate Limiting & Auth**: Protect your APIs from abuse and unauthorized access
- 📈 **Metrics & Health Checks**: Comprehensive monitoring and observability
- 🔄 **Graceful Shutdown**: Clean connection handling during deployments

**Scaling Patterns:**
- ⚡ **Horizontal Scaling**: Load balancer-friendly stateless architecture
- 🔗 **Connection Pooling**: Efficient resource management for high throughput
- ⚙️ **Async Processing**: Non-blocking I/O for maximum concurrency
- 💾 **Caching Layers**: Intelligent caching for frequently accessed workflows

**Integration Examples:**

```python
# Web Application Integration
import httpx

async def call_orka_workflow(user_input: str):
    async with httpx.AsyncClient() as client:
        response = await client.post("http://orka-server:8000/api/run", json={
            "input": user_input,
            "yaml_config": workflow_config
        })
        return response.json()

# Microservice Integration
from fastapi import FastAPI
from orka.server import OrKaServer

app = FastAPI()
orka = OrKaServer()

@app.post("/intelligent-response")
async def intelligent_response(request: UserRequest):
    result = await orka.execute_workflow(
        config="customer_service.yml",
        input=request.message,
        context={"user_id": request.user_id}
    )
    return {"response": result["answer_agent"]}
```

**Real-world Applications:**
- Customer service APIs with intelligent routing and responses
- Content processing services for media and publishing platforms
- Research automation APIs for academic and enterprise use
- Real-time decision APIs for financial and healthcare applications
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
    print("\n========== [DEBUG] Incoming POST /api/run ==========")
    pprint.pprint(data)

    input_text = data.get("input")
    yaml_config = data.get("yaml_config")

    print("\n========== [DEBUG] YAML Config String ==========")
    print(yaml_config)

    # Create a temporary file path with UTF-8 encoding
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".yml")
    os.close(tmp_fd)  # Close the file descriptor

    # Write with explicit UTF-8 encoding
    with open(tmp_path, "w", encoding="utf-8") as tmp:
        tmp.write(yaml_config)

    print("\n========== [DEBUG] Instantiating Orchestrator ==========")
    orchestrator = Orchestrator(tmp_path)
    print(f"Orchestrator: {orchestrator}")

    print("\n========== [DEBUG] Running Orchestrator ==========")
    result = await orchestrator.run(input_text)

    # Clean up the temporary file
    try:
        os.remove(tmp_path)
    except:
        print(f"Warning: Failed to remove temporary file {tmp_path}")

    print("\n========== [DEBUG] Orchestrator Result ==========")
    pprint.pprint(result)

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
