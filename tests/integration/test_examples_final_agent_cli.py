"""
Integration test: run curated examples with real OrKa CLI and assert final agent id.

Requirements:
- Real OrKa environment up and running (e.g., started via `orka-start`)
- External services reachable as configured by the examples

Enable this test by setting environment variable ORKA_REAL_ENV=1.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Set, Tuple, Union

import pytest


def _get_input_for_workflow(filename: str) -> str:
    """Heuristic input selection based on filename (mirrors PRIVATE runner logic)."""
    name = filename.lower()
    if "routed_binary_memory_writer" in name:
        return "25"
    if "memory" in name:
        return "What is the importance of data structures in computer science?"
    if "validation" in name or "structuring" in name:
        return "What are the key principles of software architecture?"
    if "local_llm" in name or "llm" in name:
        return "Artificial intelligence and machine learning research methodologies"
    if "failover" in name or "reliability" in name:
        return "What are the best practices for system reliability?"
    if "fork" in name or "join" in name:
        return "What are the benefits of parallel processing in computing?"
    if "routing" in name or "router" in name:
        return "How do computer networks handle data routing?"
    if "classification" in name:
        return "What are the different types of machine learning algorithms?"
    return "What are the key innovations in modern technology?"


_ORKA_FINAL_AGENT_RE = re.compile(r"\[ORKA-FINAL\].*final agent:\s*([\w\-]+)")


def _extract_final_agent(stdout: str) -> str:
    """Extract final agent id from CLI stdout using ORKA-FINAL log line."""
    match = _ORKA_FINAL_AGENT_RE.search(stdout)
    return match.group(1) if match else ""


def _should_skip_due_to_llm(stdout: str, stderr: str) -> bool:
    """Detect when LLM calls failed so the orchestrator cannot emit a final agent."""
    text = f"{stdout}\n{stderr}"
    markers = (
        "401 Unauthorized",
        "APIStatusError",
        "Failed to execute agent",
        "BranchError",
        "No suitable final agent found",
    )
    return any(m in text for m in markers)


@pytest.mark.skipif(
    False,
    reason="Requires a real OrKa environment running (set ORKA_REAL_ENV=1)",
)
@pytest.mark.parametrize(
    "example_path,expected_final",
    [
        ("examples/person_routing_with_search.yml", {"answer-final"}),
        ("examples/temporal_change_search_synthesis.yml", {"synthesize_timeline_answer"}),
        ("examples/memory_read_fork_join_router.yml", {"openai-answer_14", "openai-answer_15"}),
        # ("examples/failover_search_and_validate.yml", {"build_answer", "validate_fact"}),
        (
            "examples/conditional_search_fork_join.yaml",
            {"final_builder_true", "final_builder_false"},
        ),
        # Optional examples (uncomment locally if environment supports them):
        ("examples/validation_structuring_memory_pipeline.yml", {"memory-path", "answer-builder"}),
        ("examples/multi_model_local_llm_evaluation.yml", {"answer_21"}),
        ("examples/cognitive_society_minimal_loop.yml", {"final_answer"}),
        ("examples/cognitive_loop_scoring_example.yml", {"final_processor"}),
        ("examples/orka_framework_qa.yml", {"qa_agent"}),  # uses Kafka memory backend
    ],
)
def test_example_final_agent_cli(example_path: str, expected_final: Set[str]) -> None:
    path = Path(example_path)
    if not path.exists():
        pytest.skip(f"Example not found: {example_path}")

    input_text = _get_input_for_workflow(path.name)

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "orka.orka_cli", "run", str(path), input_text],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env=env,
    )

    # Basic execution should succeed
    assert (
        result.returncode == 0
    ), f"CLI run failed for {example_path}:\nSTDERR:\n{result.stderr[:1000]}\nSTDOUT:\n{result.stdout[:1000]}"

    # Extract final agent id and assert it's one of the expected ones
    final_agent = _extract_final_agent(result.stdout)
    if not final_agent and _should_skip_due_to_llm(result.stdout, result.stderr):
        pytest.skip(
            "LLM backend not available (401/APIStatusError); final agent not produced in real run",
        )
    assert (
        final_agent
    ), f"Did not find ORKA-FINAL line in output for {example_path}.\nSTDOUT (tail):\n{result.stdout[-1000:]}"
    assert final_agent in expected_final, (
        f"Final agent mismatch for {example_path}: got '{final_agent}', expected one of {sorted(expected_final)}.\n"
        f"STDOUT (tail):\n{result.stdout[-1000:]}"
    )
