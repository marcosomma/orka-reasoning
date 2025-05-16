#!/usr/bin/env python3
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
Script to mark deprecated test files.
This script adds a header to each specified test file indicating that it is deprecated
and that the tests have been moved to a domain-specific test file.
"""

import argparse
import os
import sys

# List of test files that are now consolidated into domain-specific tests
DEPRECATED_TEST_FILES = [
    "test_agents.py",
    "test_agents_basic.py",
    "test_base_agent.py",
    "test_llm_agents.py",
    "test_fork_join_nodes.py",
    "test_memory.py",
    "test_memory_logger.py",
    "test_orka_agent_base.py",
    "test_orka_cli.py",
    "test_orka_orchestrator.py",
]

# The header to add to each deprecated file
DEPRECATION_HEADER = """
# [DEPRECATED] This test file has been replaced by domain-specific tests
# Please use the following domain files instead:
# - test_domain_agents.py - For all agent-related tests
# - test_domain_nodes.py - For all node-related tests including fork/join
# - test_domain_memory.py - For all memory-related tests
# - test_domain_cli_orchestration.py - For CLI and orchestration tests
# 
# This file is kept for reference only and should not be run or modified.
# All its tests have been migrated to the appropriate domain files.
import pytest

# Skip all tests in this file
pytestmark = pytest.mark.skip(reason="Tests migrated to domain-specific test files")

"""


def mark_file_as_deprecated(file_path):
    """
    Add the deprecation header to the specified file.

    Args:
        file_path (str): Path to the file to mark as deprecated

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the file content
        with open(file_path, "r") as f:
            content = f.read()

        # Check if the file is already marked as deprecated
        if "DEPRECATED" in content[:500]:
            print(f"File {file_path} is already marked as deprecated.")
            return True

        # Add the deprecation header at the top, after any license headers
        license_end = content.find("Required attribution:")
        if license_end > 0:
            # Find the end of the license header
            insert_pos = content.find("\n", license_end) + 1
            new_content = (
                content[:insert_pos] + DEPRECATION_HEADER + content[insert_pos:]
            )
        else:
            # No license header, add at the beginning
            new_content = DEPRECATION_HEADER + content

        # Write the modified content back
        with open(file_path, "w") as f:
            f.write(new_content)

        print(f"Successfully marked {file_path} as deprecated.")
        return True

    except Exception as e:
        print(f"Error marking {file_path} as deprecated: {str(e)}")
        return False


def main():
    """Main function to mark all deprecated test files."""
    parser = argparse.ArgumentParser(description="Mark deprecated test files")
    parser.add_argument(
        "--test-dir", default="test", help="Directory containing test files"
    )
    args = parser.parse_args()

    marked_count = 0
    failed_count = 0

    for file_name in DEPRECATED_TEST_FILES:
        file_path = os.path.join(args.test_dir, file_name)
        if os.path.exists(file_path):
            if mark_file_as_deprecated(file_path):
                marked_count += 1
            else:
                failed_count += 1
        else:
            print(f"File {file_path} does not exist.")

    print("\nSummary:")
    print(f"Successfully marked {marked_count} files as deprecated.")
    if failed_count > 0:
        print(f"Failed to mark {failed_count} files.")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
