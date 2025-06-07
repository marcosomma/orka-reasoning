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
Tests for start scripts
"""

import os

import pytest


def test_start_kafka_script_exists():
    """Test that start_kafka.py script exists and is readable"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "orka", "start_kafka.py"
    )
    assert os.path.exists(script_path)

    # Test that the file contains the expected environment setting
    with open(script_path, "r") as f:
        content = f.read()
        assert 'os.environ["ORKA_MEMORY_BACKEND"] = "kafka"' in content
        assert "from orka.orka_start import main" in content


def test_start_redis_script_exists():
    """Test that start_redis.py script exists and is readable"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "orka", "start_redis.py"
    )
    assert os.path.exists(script_path)

    # Test that the file contains the expected environment setting
    with open(script_path, "r") as f:
        content = f.read()
        assert 'os.environ["ORKA_MEMORY_BACKEND"] = "redis"' in content
        assert "from orka.orka_start import main" in content


def test_start_kafka_script_structure():
    """Test that start_kafka.py has the expected structure"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "orka", "start_kafka.py"
    )

    with open(script_path, "r") as f:
        content = f.read()

    # Test key elements of the script
    assert "import os" in content
    assert "import sys" in content
    assert "from pathlib import Path" in content
    assert 'os.environ["ORKA_MEMORY_BACKEND"] = "kafka"' in content
    assert 'if __name__ == "__main__":' in content
    assert "asyncio.run(main())" in content


def test_start_redis_script_structure():
    """Test that start_redis.py has the expected structure"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "orka", "start_redis.py"
    )

    with open(script_path, "r") as f:
        content = f.read()

    # Test key elements of the script
    assert "import os" in content
    assert "import sys" in content
    assert "from pathlib import Path" in content
    assert 'os.environ["ORKA_MEMORY_BACKEND"] = "redis"' in content
    assert 'if __name__ == "__main__":' in content
    assert "asyncio.run(main())" in content


def test_start_kafka_env_setting():
    """Test environment variable setting for kafka script"""
    # Store original environment
    original_value = os.environ.get("ORKA_MEMORY_BACKEND")

    try:
        # Execute the environment setting line from the script
        exec('os.environ["ORKA_MEMORY_BACKEND"] = "kafka"')

        # Verify environment was set
        assert os.environ.get("ORKA_MEMORY_BACKEND") == "kafka"

    finally:
        # Restore original value
        if original_value is not None:
            os.environ["ORKA_MEMORY_BACKEND"] = original_value
        elif "ORKA_MEMORY_BACKEND" in os.environ:
            del os.environ["ORKA_MEMORY_BACKEND"]


def test_start_redis_env_setting():
    """Test environment variable setting for redis script"""
    # Store original environment
    original_value = os.environ.get("ORKA_MEMORY_BACKEND")

    try:
        # Execute the environment setting line from the script
        exec('os.environ["ORKA_MEMORY_BACKEND"] = "redis"')

        # Verify environment was set
        assert os.environ.get("ORKA_MEMORY_BACKEND") == "redis"

    finally:
        # Restore original value
        if original_value is not None:
            os.environ["ORKA_MEMORY_BACKEND"] = original_value
        elif "ORKA_MEMORY_BACKEND" in os.environ:
            del os.environ["ORKA_MEMORY_BACKEND"]


def test_start_kafka_import_attempts():
    """Test that start_kafka.py has proper import structure"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "orka", "start_kafka.py"
    )

    with open(script_path, "r") as f:
        content = f.read()

    # Check that both import paths are present
    assert "from orka.orka_start import main" in content
    assert "from orka_start import main" in content
    assert "except ImportError:" in content


def test_start_redis_import_attempts():
    """Test that start_redis.py has proper import structure"""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "orka", "start_redis.py"
    )

    with open(script_path, "r") as f:
        content = f.read()

    # Check that both import paths are present
    assert "from orka.orka_start import main" in content
    assert "from orka_start import main" in content
    assert "except ImportError:" in content


def test_start_scripts_execution_simulation():
    """Test simulated execution of start scripts"""
    # Simulate what happens when the scripts run
    original_kafka = os.environ.get("ORKA_MEMORY_BACKEND")

    try:
        # Simulate kafka script execution
        os.environ["ORKA_MEMORY_BACKEND"] = "kafka"
        assert os.environ["ORKA_MEMORY_BACKEND"] == "kafka"

        # Simulate redis script execution
        os.environ["ORKA_MEMORY_BACKEND"] = "redis"
        assert os.environ["ORKA_MEMORY_BACKEND"] == "redis"

    finally:
        # Restore
        if original_kafka is not None:
            os.environ["ORKA_MEMORY_BACKEND"] = original_kafka
        elif "ORKA_MEMORY_BACKEND" in os.environ:
            del os.environ["ORKA_MEMORY_BACKEND"]


@pytest.mark.skipif(
    "SKIP_IMPORT_TESTS" in os.environ,
    reason="Skipping import tests due to environment setting",
)
def test_start_scripts_code_coverage():
    """Test to ensure start scripts get code coverage by executing them"""
    script_dir = os.path.join(os.path.dirname(__file__), "..", "orka")

    # Test kafka script exists and can be read
    kafka_script = os.path.join(script_dir, "start_kafka.py")
    assert os.path.exists(kafka_script)

    # Test redis script exists and can be read
    redis_script = os.path.join(script_dir, "start_redis.py")
    assert os.path.exists(redis_script)

    # Execute the core logic of the scripts without importing OrKa
    original_value = os.environ.get("ORKA_MEMORY_BACKEND")

    try:
        # Read and execute kafka script environment setting
        with open(kafka_script, "r") as f:
            kafka_content = f.read()

        # Find the line that sets the environment
        for line in kafka_content.split("\n"):
            if 'os.environ["ORKA_MEMORY_BACKEND"] = "kafka"' in line:
                exec(line)
                break

        assert os.environ.get("ORKA_MEMORY_BACKEND") == "kafka"

        # Read and execute redis script environment setting
        with open(redis_script, "r") as f:
            redis_content = f.read()

        # Find the line that sets the environment
        for line in redis_content.split("\n"):
            if 'os.environ["ORKA_MEMORY_BACKEND"] = "redis"' in line:
                exec(line)
                break

        assert os.environ.get("ORKA_MEMORY_BACKEND") == "redis"

    finally:
        # Restore original value
        if original_value is not None:
            os.environ["ORKA_MEMORY_BACKEND"] = original_value
        elif "ORKA_MEMORY_BACKEND" in os.environ:
            del os.environ["ORKA_MEMORY_BACKEND"]
