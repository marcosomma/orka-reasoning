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

    # Write YAML to a temp file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".yml") as tmp:
        tmp.write(yaml_config)
        tmp_path = tmp.name

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
