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
This master file runs all domain-specific test modules.
Running pytest on this file will run all tests in the domain test files.
"""

# Set environment variables
import os
import sys
from pathlib import Path

# Ensure the test directory is in the Python path
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))

# Set testing environment variables
os.environ["PYTEST_RUNNING"] = "true"

# No imports here - when running pytest on this file,
# it automatically discovers and runs all test_*.py files in the directory

# This file is intentionally kept empty of imports to avoid circular dependencies
# The individual test files should be run directly or via pytest's test discovery
