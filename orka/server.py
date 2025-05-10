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

import os
import pprint
import tempfile

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orka.orchestrator import Orchestrator

app = FastAPI()

# CORS (optional, but useful if UI and API are on different ports during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    # Create a temporary file path
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

    print("\n========== [DEBUG] Orchestrator Result ==========")
    pprint.pprint(result)

    return JSONResponse(
        content={"input": input_text, "execution_log": result, "log_file": result}
    )


if __name__ == "__main__":
    port = int(os.environ.get("ORKA_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
