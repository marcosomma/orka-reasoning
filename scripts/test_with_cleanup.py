#!/usr/bin/env python3
"""
Test runner script that automatically cleans up memory after tests complete.

This script runs pytest and then executes the delete_memory.py script to ensure
proper cleanup of test data from memory backends.

Usage:
    python scripts/test_with_cleanup.py [pytest_args...]

Examples:
    python scripts/test_with_cleanup.py
    python scripts/test_with_cleanup.py -v
    python scripts/test_with_cleanup.py test/test_memory_decay.py
    python scripts/test_with_cleanup.py -k "test_memory"
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run pytest followed by memory cleanup."""
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Change to project root directory
    os.chdir(project_root)

    print("🧪 Running OrKa tests...")
    print("=" * 50)

    # Run pytest with all passed arguments
    pytest_args = [sys.executable, "-m", "pytest"] + sys.argv[1:]
    pytest_result = subprocess.run(pytest_args, check=False)

    print("\n" + "=" * 50)
    print(f"[OK] Tests completed with exit code: {pytest_result.returncode}")

    # Always run cleanup, regardless of test results
    print("\n🧹 Running memory cleanup...")
    print("-" * 30)

    try:
        cleanup_script = project_root / "scripts" / "delete_memory.py"
        cleanup_result = subprocess.run(
            [sys.executable, str(cleanup_script)],
            check=False,
            timeout=30,
        )

        if cleanup_result.returncode == 0:
            print("[OK] Memory cleanup completed successfully")
        else:
            print(f"[WARN] Memory cleanup finished with return code: {cleanup_result.returncode}")

    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Memory cleanup timed out after 30 seconds")
    except Exception as e:
        print(f"[ERROR] Error during memory cleanup: {e}")

    print("\n[DONE] Test session complete!")

    # Exit with the same code as pytest
    sys.exit(pytest_result.returncode)


if __name__ == "__main__":
    main()
