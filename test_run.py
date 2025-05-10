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

from orka.orchestrator import Orchestrator

if __name__ == "__main__":
    orchestrator = Orchestrator("./example.yml")
    test_input = "who is Marco Somma in software engineering?"
    results = orchestrator.run(test_input)
    print("\nFinal Results:")
    for agent_id, result in results.items():
        print(f"{agent_id}: {result}")
