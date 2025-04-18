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

import argparse
from orka.orchestrator import Orchestrator
import os

def main():
    parser = argparse.ArgumentParser(description="Run OrKa with a YAML configuration.")
    parser.add_argument("config", help="Path to the YAML configuration file.")
    parser.add_argument("input", help="Input question or statement for the orchestrator.")
    parser.add_argument("--log-to-file", action="store_true", help="Save the orchestration trace to a JSON log file.")
    args = parser.parse_args()

    orchestrator = Orchestrator(config_path=args.config)
    orchestrator.run(args.input)

def run_cli_entrypoint(config_path, input_text, log_to_file=False):
    from orka.orchestrator import Orchestrator

    orchestrator = Orchestrator(config_path)
    result = orchestrator.run(input_text)

    if log_to_file:
        with open("orka_trace.log", "w") as f:
            f.write(str(result))
    else:
        for agent_id, value in result.items():
            print(f"{agent_id}: {value}")

    return result  # ← this is crucial for test assertion

if __name__ == "__main__":
    main()
