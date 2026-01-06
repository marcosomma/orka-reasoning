import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from orka.orchestrator.metrics import MetricsCollector


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def test_build_previous_outputs_handles_multiple_payload_shapes():
    logs = [
        {"agent_id": "a1", "payload": {"result": "plain"}},
        {
            "agent_id": "join",
            "payload": {"result": {"merged": {"k": "v"}}},
        },
        {
            "agent_id": "llm",
            "payload": {"response": "hello", "confidence": "0.9", "internal_reasoning": "x"},
        },
        {
            "agent_id": "mem",
            "payload": {"memories": ["m1"], "query": "q", "backend": "b", "search_type": "s"},
        },
    ]

    outputs = MetricsCollector.build_previous_outputs(logs)

    assert outputs["a1"] == "plain"
    assert outputs["k"] == "v"
    assert outputs["llm"]["response"] == "hello"
    assert outputs["mem"]["memories"] == ["m1"]


def test_get_runtime_environment_no_git_no_gpu(monkeypatch):
    collector = MetricsCollector()

    with patch("orka.orchestrator.metrics.platform.platform", return_value="Linux-5.4.0"):
        with patch("orka.orchestrator.metrics.subprocess.check_output", side_effect=Exception("no git")):
            with patch("orka.orchestrator.metrics.shutil.which", return_value=None):
                env = collector._get_runtime_environment()

    assert env["git_sha"] == "unknown"
    assert env["gpu_type"] == "none"
    assert env["docker_image"] is None


def test_get_runtime_environment_with_git_and_gpu():
    collector = MetricsCollector()

    fake_run = SimpleNamespace(returncode=0, stdout="RTX 4090\n")

    with patch("orka.orchestrator.metrics.platform.platform", return_value="Linux-5.4.0"):
        with patch("orka.orchestrator.metrics.subprocess.check_output", return_value=b"abcdef1234567890"):
            with patch("orka.orchestrator.metrics.shutil.which", return_value="nvidia-smi"):
                with patch("orka.orchestrator.metrics.subprocess.run", return_value=fake_run):
                    env = collector._get_runtime_environment()

    assert env["git_sha"] == "abcdef123456"  # short SHA
    assert "RTX 4090" in env["gpu_type"]


def test_generate_meta_report_aggregates_and_dedupes_nested_metrics(monkeypatch):
    collector = MetricsCollector()
    collector.run_id = "run-1"

    metrics = {
        "model": "m",
        "tokens": 10,
        "prompt_tokens": 3,
        "completion_tokens": 7,
        "latency_ms": 100,
        "cost_usd": 0.001,
    }

    logs = [
        {"agent_id": "a1", "duration": 1.0, "payload": {"data": {"_metrics": metrics}}},
        # duplicate metrics object should be deduped by seen_metrics
        {"agent_id": "a1", "duration": 2.0, "payload": {"data": {"_metrics": dict(metrics)}}},
    ]

    # Avoid subprocess calls in runtime env collection
    with patch.object(collector, "_get_runtime_environment", return_value={"git_sha": "x"}):
        report = collector._generate_meta_report(logs)

    assert report["execution_stats"]["run_id"] == "run-1"
    assert report["total_duration"] == 3.0
    assert report["total_llm_calls"] == 1
    assert report["total_tokens"] == 10
    assert report["total_cost_usd"] == 0.001
    assert report["agent_breakdown"]["a1"]["calls"] == 1


def test_generate_meta_report_null_cost_respects_policy(monkeypatch):
    collector = MetricsCollector()
    collector.run_id = "run-2"

    logs = [
        {
            "agent_id": "a1",
            "duration": 0.1,
            "payload": {
                "_metrics": {
                    "model": "m",
                    "tokens": 5,
                    "prompt_tokens": 1,
                    "completion_tokens": 4,
                    "latency_ms": 10,
                    "cost_usd": None,
                }
            },
        }
    ]

    with patch.object(collector, "_get_runtime_environment", return_value={}):
        monkeypatch.setenv("ORKA_LOCAL_COST_POLICY", "null_fail")
        with pytest.raises(ValueError):
            collector._generate_meta_report(logs)

        monkeypatch.setenv("ORKA_LOCAL_COST_POLICY", "null_ignore")
        report = collector._generate_meta_report(logs)
        assert report["total_llm_calls"] == 1
        assert report["total_cost_usd"] == 0.0


def test_generate_meta_report_extracts_graphscout_decision_trace_metrics():
    """Test that GraphScout decision_trace candidate metrics are extracted."""
    collector = MetricsCollector()
    collector.run_id = "run-gs"

    # GraphScout trace structure with nested candidate metrics
    logs = [
        {
            "agent_id": "graph_scout",
            "duration": 0.5,
            "payload": {
                "result": {
                    "decision_trace": {
                        "candidates": [
                            {
                                "node_id": "path_a",
                                "score": 0.85,
                                "evaluation_result": {
                                    "_metrics": {
                                        "model": "local-eval",
                                        "tokens": 50,
                                        "prompt_tokens": 30,
                                        "completion_tokens": 20,
                                        "latency_ms": 100,
                                        "cost_usd": 0.0,
                                    }
                                },
                            },
                            {
                                "node_id": "path_b",
                                "score": 0.7,
                                "evaluation_result": {
                                    "_metrics": {
                                        "model": "local-eval",
                                        "tokens": 40,
                                        "prompt_tokens": 25,
                                        "completion_tokens": 15,
                                        "latency_ms": 80,
                                        "cost_usd": 0.0,
                                    }
                                },
                            },
                        ]
                    }
                }
            },
        }
    ]

    with patch.object(collector, "_get_runtime_environment", return_value={}):
        report = collector._generate_meta_report(logs)

    # Should aggregate both candidate metrics
    assert report["total_llm_calls"] == 2
    assert report["total_tokens"] == 90  # 50 + 40
    assert report["agent_breakdown"]["graph_scout"]["calls"] == 2
    assert report["agent_breakdown"]["graph_scout"]["tokens"] == 90
