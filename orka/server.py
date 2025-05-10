# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

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

app = FastAPI()
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
    Recursively sanitize an object for JSON serialization.

    Args:
        obj: Object to sanitize

    Returns:
        JSON-serializable version of the object
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
                return f"<non-serializable object: {obj.__class__.__name__}, error: {str(e)}>"
        else:
            # Last resort - convert to string
            return f"<non-serializable: {type(obj).__name__}>"
    except Exception as e:
        logger.warning(f"Failed to sanitize object for JSON: {str(e)}")
        return f"<sanitization-error: {str(e)}>"


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
            }
        )
    except Exception as e:
        logger.error(f"Error creating JSONResponse: {str(e)}")
        # Fallback response with minimal data
        return JSONResponse(
            content={
                "input": input_text,
                "error": f"Error creating response: {str(e)}",
                "summary": "Execution completed but response contains non-serializable data",
            },
            status_code=500,
        )


if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port = int(os.environ.get("ORKA_PORT", 8001))  # Default to 8001 to avoid conflicts
    uvicorn.run(app, host="0.0.0.0", port=port)
