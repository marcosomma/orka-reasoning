#!/usr/bin/env python3
"""
OrKa Examples Runner with Namespace Isolation
==============================================

This script iterates through all example YAML files in the examples directory
and runs them using the OrKa CLI with appropriate input text for each workflow.

Key Features:
- Isolated test namespace option to avoid polluting production data
- Automatic cleanup of test namespace after execution
- Unicode encoding support for OrKa emoji output
- Comprehensive reporting and filtering options

Usage:
    python run_all_examples.py [--dry-run] [--verbose] [--filter PATTERN] [--test-namespace]

Options:
    --dry-run           Show what would be executed without actually running
    --verbose           Show detailed output from each execution
    --filter PATTERN    Only run examples matching the given pattern (case-insensitive)
    --test-namespace    Run in isolated test namespace and cleanup afterward
    --namespace NAME    Custom test namespace name (default: orka_test_runner)
    --skip-cleanup      Don't cleanup test namespace (useful for debugging)
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Tuple

import yaml


# Color codes for output formatting
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def get_workflow_input_mapping() -> Dict[str, str]:
    """
    Returns a mapping of workflow patterns to appropriate input text.
    This mapping is based on the analysis of each workflow's purpose.
    """
    return {
        # General classification and routing workflows
        "example.yml": "Who is Elon Musk and what companies does he run?",
        "complex_flow.yml": "How has the definition of artificial intelligence changed over time?",
        "fork_join.yaml": "What is quantum computing and how does it work?",
        # Memory-related workflows
        "basic_memory.yml": "What is the capital of France and its population?",
        "memory_category_test.yml": "What are the key characteristics of machine learning?",
        "memory_decay_example.yml": "What is the history of the internet?",
        "test_memory_types.yml": "What are the different types of neural networks?",
        "routing_memory_writers.yml": "25",
        "enhanced_memory_validation_example.yml": "What are the main components of a computer processor?",
        # Validation and structuring workflows
        "validation_and_structuring_orchestrator.yml": "What is the height of Mount Everest?",
        # Local LLM comparison workflows
        "local_llm.yml": "Machine learning techniques for natural language processing and their applications",
        # Failover and reliability workflows
        "failover.yml": "What are the main causes of climate change?",
        # Base examples
        "base/example.yml": "What is the difference between Python and JavaScript?",
        "base/test.py": "This is a test input for the Python test file",
    }


def get_input_for_workflow(filename: str, default_inputs: Dict[str, str]) -> str:
    """
    Determines the appropriate input text for a given workflow file.
    """
    # First check for exact filename match
    if filename in default_inputs:
        return default_inputs[filename]

    # Then check for pattern matches
    filename_lower = filename.lower()

    if "memory" in filename_lower:
        return "What is the importance of data structures in computer science?"
    elif "validation" in filename_lower or "structuring" in filename_lower:
        return "What are the key principles of software architecture?"
    elif "local_llm" in filename_lower or "llm" in filename_lower:
        return "Artificial intelligence and machine learning research methodologies"
    elif "failover" in filename_lower or "reliability" in filename_lower:
        return "What are the best practices for system reliability?"
    elif "fork" in filename_lower or "join" in filename_lower:
        return "What are the benefits of parallel processing in computing?"
    elif "routing" in filename_lower or "router" in filename_lower:
        return "How do computer networks handle data routing?"
    elif "classification" in filename_lower:
        return "What are the different types of machine learning algorithms?"
    else:
        # Default general-purpose input
        return "What are the key innovations in modern technology?"


def find_example_files(examples_dir: str) -> List[str]:
    """
    Finds all YAML example files in the examples directory and subdirectories.
    """
    yaml_patterns = ["*.yml", "*.yaml"]
    example_files = []

    for pattern in yaml_patterns:
        # Search in examples directory
        pattern_path = os.path.join(examples_dir, pattern)
        example_files.extend(glob.glob(pattern_path))

        # Search in subdirectories
        subdir_pattern = os.path.join(examples_dir, "**", pattern)
        example_files.extend(glob.glob(subdir_pattern, recursive=True))

    # Remove duplicates and sort
    example_files = sorted(list(set(example_files)))

    # Filter out non-example files if any
    filtered_files = []
    for file in example_files:
        # Skip if it's not in examples directory or subdirectories
        rel_path = os.path.relpath(file, examples_dir)
        if not rel_path.startswith(".."):
            filtered_files.append(file)

    return filtered_files


def modify_yaml_namespace(yaml_file_path: str, test_namespace: str, temp_dir: str) -> str:
    """
    Modify a YAML file to use the test namespace and save to temp directory.
    Returns the path to the modified file.
    """
    try:
        with open(yaml_file_path, encoding="utf-8") as f:
            yaml_content = yaml.safe_load(f)

        # Track if any modifications were made
        modified = False

        # Recursively search for namespace fields in agents
        def modify_namespaces(obj, path=""):
            nonlocal modified
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "namespace":
                        old_namespace = value
                        obj[key] = test_namespace
                        modified = True
                        print_colored(
                            f"    └─ Modified namespace: {old_namespace} → {test_namespace}",
                            Colors.OKCYAN,
                        )
                    else:
                        modify_namespaces(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    modify_namespaces(item, f"{path}[{i}]")

        # Apply namespace modifications
        modify_namespaces(yaml_content)

        # Create temp file path
        rel_path = os.path.relpath(yaml_file_path, "examples")
        temp_file_path = os.path.join(temp_dir, rel_path)

        # Ensure temp subdirectories exist
        os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

        # Save modified YAML
        with open(temp_file_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)

        if modified:
            print_colored(f"    ✓ Created test version: {temp_file_path}", Colors.OKGREEN)
        else:
            print_colored("    → No namespaces found, using original", Colors.WARNING)

        return temp_file_path

    except Exception as e:
        print_colored(f"    ✗ Error modifying YAML: {e!s}", Colors.FAIL)
        return yaml_file_path  # Return original on error


def cleanup_test_namespace(test_namespace: str, verbose: bool = False) -> Dict[str, any]:
    """
    Clean up all memory data for the test namespace.
    """
    try:
        print_colored(f"\n🧹 Cleaning up test namespace: {test_namespace}", Colors.WARNING)

        # Import the memory cleanup functionality
        sys.path.insert(0, "orka")
        from orka.memory_logger import create_memory_logger

        cleanup_stats = {
            "namespace": test_namespace,
            "total_cleaned": 0,
            "backend_results": [],
            "errors": [],
        }

        # Try different backends for comprehensive cleanup
        backends = ["redisstack", "redis"]
        redis_urls = {
            "redisstack": "redis://localhost:6380/0",
            "redis": "redis://localhost:6379/0",
        }

        for backend in backends:
            try:
                print_colored(f"  🔧 Cleaning {backend} backend...", Colors.OKBLUE)

                memory_logger = create_memory_logger(
                    backend=backend,
                    redis_url=redis_urls[backend],
                )

                # Get all memory keys for this namespace
                if hasattr(memory_logger, "redis_client"):
                    client = memory_logger.redis_client
                elif hasattr(memory_logger, "client"):
                    client = memory_logger.client
                else:
                    print_colored(f"    ⚠️ No Redis client found for {backend}", Colors.WARNING)
                    continue

                # Find all memory keys
                pattern = "orka_memory:*"
                keys = client.keys(pattern)

                namespace_keys = []
                for key in keys:
                    try:
                        # Get memory data to check namespace
                        memory_data = client.hgetall(key)
                        if memory_data:
                            # Handle both bytes and string keys
                            namespace_field = memory_data.get(b"namespace") or memory_data.get(
                                "namespace",
                            )
                            if namespace_field:
                                if isinstance(namespace_field, bytes):
                                    namespace_value = namespace_field.decode()
                                else:
                                    namespace_value = namespace_field

                                if namespace_value == test_namespace:
                                    namespace_keys.append(key)
                    except Exception as e:
                        if verbose:
                            print_colored(f"    ⚠️ Error checking key {key}: {e}", Colors.WARNING)

                # Delete namespace-specific keys
                if namespace_keys:
                    deleted_count = client.delete(*namespace_keys)
                    cleanup_stats["total_cleaned"] += deleted_count
                    cleanup_stats["backend_results"].append(
                        {
                            "backend": backend,
                            "keys_found": len(namespace_keys),
                            "keys_deleted": deleted_count,
                        },
                    )
                    print_colored(
                        f"    ✓ Deleted {deleted_count} keys from {backend}",
                        Colors.OKGREEN,
                    )
                else:
                    print_colored(
                        f"    → No keys found in {backend} for namespace {test_namespace}",
                        Colors.OKCYAN,
                    )
                    cleanup_stats["backend_results"].append(
                        {
                            "backend": backend,
                            "keys_found": 0,
                            "keys_deleted": 0,
                        },
                    )

                # Close the logger
                if hasattr(memory_logger, "close"):
                    memory_logger.close()

            except ImportError as e:
                print_colored(f"    ⚠️ {backend} backend not available: {e}", Colors.WARNING)
                cleanup_stats["errors"].append(f"{backend}: {e}")
            except Exception as e:
                print_colored(f"    ✗ Error cleaning {backend}: {e}", Colors.FAIL)
                cleanup_stats["errors"].append(f"{backend}: {e}")

        total_cleaned = cleanup_stats["total_cleaned"]
        if total_cleaned > 0:
            print_colored(
                f"🎉 Cleanup complete! Removed {total_cleaned} memory entries",
                Colors.OKGREEN,
            )
        else:
            print_colored("✨ Namespace was clean (no entries found)", Colors.OKCYAN)

        return cleanup_stats

    except Exception as e:
        error_msg = f"Failed to cleanup namespace {test_namespace}: {e}"
        print_colored(f"✗ {error_msg}", Colors.FAIL)
        return {
            "namespace": test_namespace,
            "total_cleaned": 0,
            "backend_results": [],
            "errors": [error_msg],
        }


def run_orka_workflow(
    example_file: str,
    input_text: str,
    verbose: bool = False,
) -> Tuple[bool, str, str]:
    """
    Runs a single OrKa workflow and returns success status, stdout, and stderr.
    """
    command = [
        sys.executable,
        "-m",
        "orka.orka_cli",
        "run",
        example_file,
        input_text,
    ]

    try:
        # Set environment to handle Unicode properly
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Replace problematic characters instead of failing
            timeout=300,  # 5 minute timeout
            env=env,
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return False, "", "Execution timed out after 5 minutes"
    except UnicodeDecodeError as e:
        return False, "", f"Unicode encoding error: {e!s}"
    except Exception as e:
        return False, "", f"Execution failed: {e!s}"


def print_colored(text: str, color: str = Colors.ENDC) -> None:
    """Prints colored text to stdout."""
    print(f"{color}{text}{Colors.ENDC}")


def print_separator(title: str = "") -> None:
    """Prints a separator line with optional title."""
    if title:
        print_colored(f"\n{'=' * 60}", Colors.HEADER)
        print_colored(f"  {title}", Colors.HEADER)
        print_colored(f"{'=' * 60}", Colors.HEADER)
    else:
        print_colored(f"{'=' * 60}", Colors.HEADER)


def main():
    parser = argparse.ArgumentParser(
        description="Run all OrKa example workflows with appropriate input text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without actually running",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output from each execution",
    )

    parser.add_argument(
        "--filter",
        type=str,
        help="Only run examples matching the given pattern (case-insensitive)",
    )

    parser.add_argument(
        "--examples-dir",
        type=str,
        default="examples",
        help="Path to examples directory (default: examples)",
    )

    parser.add_argument(
        "--test-namespace",
        action="store_true",
        help="Run examples in isolated test namespace and cleanup afterward",
    )

    parser.add_argument(
        "--namespace",
        type=str,
        default="orka_test_runner",
        help="Custom test namespace name (default: orka_test_runner)",
    )

    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Don't cleanup test namespace after execution (useful for debugging)",
    )

    args = parser.parse_args()

    # Check if examples directory exists
    if not os.path.exists(args.examples_dir):
        print_colored(f"Error: Examples directory '{args.examples_dir}' not found!", Colors.FAIL)
        sys.exit(1)

    # Find all example files
    example_files = find_example_files(args.examples_dir)

    if not example_files:
        print_colored(f"No example files found in '{args.examples_dir}'", Colors.WARNING)
        sys.exit(1)

    # Apply filter if specified
    if args.filter:
        example_files = [f for f in example_files if args.filter.lower() in f.lower()]
        if not example_files:
            print_colored(f"No example files match filter '{args.filter}'", Colors.WARNING)
            sys.exit(1)

    # Get input mappings
    input_mappings = get_workflow_input_mapping()

    print_separator("OrKa Examples Runner with Namespace Isolation")
    print_colored(f"Found {len(example_files)} example files to process", Colors.OKBLUE)

    if args.test_namespace:
        print_colored(f"🔒 Test namespace mode: {args.namespace}", Colors.OKCYAN)
        if not args.skip_cleanup:
            print_colored("🧹 Cleanup will be performed after execution", Colors.OKCYAN)
        else:
            print_colored("⚠️ Cleanup skipped (debug mode)", Colors.WARNING)

    if args.dry_run:
        print_colored("DRY RUN MODE - No actual execution", Colors.WARNING)

    # Setup temporary directory for modified YAML files
    temp_dir = None
    modified_files = {}

    if args.test_namespace and not args.dry_run:
        temp_dir = tempfile.mkdtemp(prefix="orka_test_")
        print_colored(f"📁 Created temporary directory: {temp_dir}", Colors.OKBLUE)

        # Modify YAML files to use test namespace
        print_colored("\n🔧 Modifying workflows for test namespace...", Colors.HEADER)
        for example_file in example_files:
            rel_path = os.path.relpath(example_file, args.examples_dir)
            print_colored(f"  📝 Processing: {rel_path}", Colors.OKBLUE)

            modified_path = modify_yaml_namespace(example_file, args.namespace, temp_dir)
            modified_files[example_file] = modified_path

    # Results tracking
    results = {
        "total": len(example_files),
        "successful": 0,
        "failed": 0,
        "test_namespace": args.namespace if args.test_namespace else None,
        "temp_dir": temp_dir,
        "details": [],
    }

    try:
        # Process each example file
        for i, example_file in enumerate(example_files, 1):
            # Get relative path for display
            rel_path = os.path.relpath(example_file, args.examples_dir)

            # Use modified file if in test namespace mode
            actual_file = (
                modified_files.get(example_file, example_file)
                if args.test_namespace
                else example_file
            )

            # Get appropriate input text
            input_text = get_input_for_workflow(rel_path, input_mappings)

            print_separator(f"Example {i}/{len(example_files)}: {rel_path}")
            print_colored(f"Input: {input_text}", Colors.OKCYAN)

            if args.test_namespace:
                print_colored(f"Namespace: {args.namespace}", Colors.OKCYAN)

            if args.dry_run:
                command = f'python -m orka.orka_cli run {actual_file} "{input_text}"'
                print_colored(f"Would execute: {command}", Colors.WARNING)
                continue

            # Run the workflow
            print_colored("Executing...", Colors.OKBLUE)
            start_time = time.time()

            success, stdout, stderr = run_orka_workflow(actual_file, input_text, args.verbose)

            execution_time = time.time() - start_time

            # Record result
            result_detail = {
                "file": rel_path,
                "input": input_text,
                "success": success,
                "execution_time": execution_time,
                "stdout": stdout,
                "stderr": stderr,
                "test_namespace": args.namespace if args.test_namespace else None,
            }
            results["details"].append(result_detail)

            if success:
                results["successful"] += 1
                print_colored(f"✓ SUCCESS (took {execution_time:.2f}s)", Colors.OKGREEN)
                if args.verbose and stdout:
                    print_colored("Output:", Colors.OKBLUE)
                    print(stdout)
            else:
                results["failed"] += 1
                print_colored(f"✗ FAILED (took {execution_time:.2f}s)", Colors.FAIL)
                if stderr:
                    print_colored("Error:", Colors.FAIL)
                    print(stderr)
                if args.verbose and stdout:
                    print_colored("Output:", Colors.WARNING)
                    print(stdout)

        # Print summary
        if not args.dry_run:
            print_separator("EXECUTION SUMMARY")
            print_colored(f"Total workflows: {results['total']}", Colors.OKBLUE)
            print_colored(f"Successful: {results['successful']}", Colors.OKGREEN)
            print_colored(
                f"Failed: {results['failed']}",
                Colors.FAIL if results["failed"] > 0 else Colors.OKBLUE,
            )

            success_rate = (results["successful"] / results["total"]) * 100
            print_colored(
                f"Success rate: {success_rate:.1f}%",
                Colors.OKGREEN if success_rate >= 80 else Colors.WARNING,
            )

            # Show failed workflows
            if results["failed"] > 0:
                print_colored("\nFailed workflows:", Colors.FAIL)
                for detail in results["details"]:
                    if not detail["success"]:
                        print_colored(
                            f"  - {detail['file']}: {detail['stderr'][:100]}...",
                            Colors.FAIL,
                        )

            # Perform namespace cleanup if requested
            if args.test_namespace and not args.skip_cleanup:
                cleanup_stats = cleanup_test_namespace(args.namespace, args.verbose)
                results["cleanup_stats"] = cleanup_stats

            # Save detailed results to JSON file
            results_file = "orka_examples_results.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            print_colored(f"\nDetailed results saved to: {results_file}", Colors.OKBLUE)

    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print_colored(f"🗑️ Cleaned up temporary directory: {temp_dir}", Colors.OKBLUE)
            except Exception as e:
                print_colored(f"⚠️ Failed to cleanup temp directory: {e}", Colors.WARNING)


if __name__ == "__main__":
    main()
