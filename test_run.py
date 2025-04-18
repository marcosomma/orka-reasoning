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

from orka.orchestrator import Orchestrator

if __name__ == "__main__":
    orchestrator = Orchestrator("./example.yml")
    test_input = "who is Marco Somma in software engineering?"
    results = orchestrator.run(test_input)
    print("\nFinal Results:")
    for agent_id, result in results.items():
        print(f"{agent_id}: {result}")
