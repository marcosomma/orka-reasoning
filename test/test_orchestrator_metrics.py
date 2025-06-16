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

import os
import platform
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from orka.orchestrator.metrics import MetricsCollector


class TestMetricsCollector:
    """Test suite for MetricsCollector functionality"""

    @pytest.fixture
    def metrics_collector(self):
        """Create a MetricsCollector instance with necessary attributes"""
        collector = MetricsCollector()
        collector.run_id = "test-run-123"
        return collector

    def test_extract_llm_metrics_from_dict_result(self, metrics_collector):
        """Test extracting LLM metrics from dict result with _metrics key"""
        agent = MagicMock()
        result = {
            "content": "test response",
            "_metrics": {
                "model": "gpt-4",
                "tokens": 100,
                "cost_usd": 0.002,
                "latency_ms": 1500,
            },
        }

        metrics = metrics_collector._extract_llm_metrics(agent, result)

        assert metrics is not None
        assert metrics["model"] == "gpt-4"
        assert metrics["tokens"] == 100
        assert metrics["cost_usd"] == 0.002
        assert metrics["latency_ms"] == 1500

    def test_extract_llm_metrics_from_agent_last_metrics(self, metrics_collector):
        """Test extracting LLM metrics from agent's _last_metrics attribute"""
        agent = MagicMock()
        agent._last_metrics = {
            "model": "claude-3",
            "tokens": 150,
            "cost_usd": 0.003,
            "latency_ms": 2000,
        }
        result = "simple string result"

        metrics = metrics_collector._extract_llm_metrics(agent, result)

        assert metrics is not None
        assert metrics["model"] == "claude-3"
        assert metrics["tokens"] == 150

    def test_extract_llm_metrics_no_metrics(self, metrics_collector):
        """Test extracting LLM metrics when no metrics are available"""
        agent = MagicMock()
        # Remove _last_metrics attribute
        del agent._last_metrics
        result = "simple string result"

        metrics = metrics_collector._extract_llm_metrics(agent, result)

        assert metrics is None

    def test_extract_llm_metrics_empty_last_metrics(self, metrics_collector):
        """Test extracting LLM metrics when _last_metrics is empty"""
        agent = MagicMock()
        agent._last_metrics = None
        result = {"content": "test"}

        metrics = metrics_collector._extract_llm_metrics(agent, result)

        assert metrics is None

    @patch("subprocess.check_output")
    def test_get_runtime_environment_with_git(self, mock_subprocess, metrics_collector):
        """Test runtime environment collection with Git available"""
        mock_subprocess.return_value = b"abc123def456\n"

        env_info = metrics_collector._get_runtime_environment()

        assert env_info["platform"] == platform.platform()
        assert env_info["python_version"] == platform.python_version()
        assert env_info["git_sha"] == "abc123def456"
        assert env_info["pricing_version"] == "2025-01"
        assert "timestamp" in env_info

    @patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git"))
    def test_get_runtime_environment_no_git(self, mock_subprocess, metrics_collector):
        """Test runtime environment collection when Git is not available"""
        env_info = metrics_collector._get_runtime_environment()

        assert env_info["git_sha"] == "unknown"

    @patch("os.path.exists")
    @patch.dict(os.environ, {"DOCKER_CONTAINER": "true", "DOCKER_IMAGE": "orka:latest"})
    def test_get_runtime_environment_docker(self, mock_exists, metrics_collector):
        """Test runtime environment collection in Docker environment"""
        mock_exists.return_value = True  # /.dockerenv exists

        env_info = metrics_collector._get_runtime_environment()

        assert env_info["docker_image"] == "orka:latest"

    @patch("os.path.exists", return_value=False)
    @patch.dict(os.environ, {}, clear=True)
    def test_get_runtime_environment_no_docker(self, mock_exists, metrics_collector):
        """Test runtime environment collection outside Docker"""
        env_info = metrics_collector._get_runtime_environment()

        assert env_info["docker_image"] is None

    def test_get_runtime_environment_gpu_available(self, metrics_collector):
        """Test runtime environment collection with GPU available"""
        # Mock GPUtil
        mock_gpu = MagicMock()
        mock_gpu.name = "NVIDIA RTX 4090"

        with patch.dict("sys.modules", {"GPUtil": MagicMock()}):
            import sys

            sys.modules["GPUtil"].getGPUs.return_value = [mock_gpu]

            env_info = metrics_collector._get_runtime_environment()

            assert env_info["gpu_type"] == "NVIDIA RTX 4090 (1 GPU)"

    def test_get_runtime_environment_multiple_gpus(self, metrics_collector):
        """Test runtime environment collection with multiple GPUs"""
        mock_gpu1 = MagicMock()
        mock_gpu1.name = "NVIDIA RTX 4090"
        mock_gpu2 = MagicMock()
        mock_gpu2.name = "NVIDIA RTX 4090"

        with patch.dict("sys.modules", {"GPUtil": MagicMock()}):
            import sys

            sys.modules["GPUtil"].getGPUs.return_value = [mock_gpu1, mock_gpu2]

            env_info = metrics_collector._get_runtime_environment()

            assert env_info["gpu_type"] == "NVIDIA RTX 4090 (2 GPUs)"

    def test_get_runtime_environment_no_gpu(self, metrics_collector):
        """Test runtime environment collection with no GPU"""
        with patch.dict("sys.modules", {"GPUtil": MagicMock()}):
            import sys

            sys.modules["GPUtil"].getGPUs.return_value = []

            env_info = metrics_collector._get_runtime_environment()

            assert env_info["gpu_type"] == "none"

    def test_get_runtime_environment_gpu_error(self, metrics_collector):
        """Test runtime environment collection when GPU detection fails"""
        with patch.dict("sys.modules", {"GPUtil": MagicMock()}):
            import sys

            sys.modules["GPUtil"].getGPUs.side_effect = Exception("GPU error")

            env_info = metrics_collector._get_runtime_environment()

            assert env_info["gpu_type"] == "unknown"

    def test_get_runtime_environment_no_gputil(self, metrics_collector):
        """Test runtime environment collection when GPUtil is not available"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'GPUtil'")):
            env_info = metrics_collector._get_runtime_environment()

            assert env_info["gpu_type"] == "unknown"

    def test_generate_meta_report_basic(self, metrics_collector):
        """Test basic meta report generation"""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.5,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.002,
                    "latency_ms": 1500,
                },
            },
            {
                "agent_id": "agent2",
                "duration": 2.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 150,
                    "cost_usd": 0.003,
                    "latency_ms": 2000,
                },
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        assert report["total_duration"] == 3.5
        assert report["total_llm_calls"] == 2
        assert report["total_tokens"] == 250
        assert report["total_cost_usd"] == 0.005
        assert report["avg_latency_ms"] == 1750.0
        assert len(report["agent_breakdown"]) == 2
        assert "gpt-4" in report["model_usage"]
        assert report["model_usage"]["gpt-4"]["calls"] == 2

    def test_generate_meta_report_nested_metrics(self, metrics_collector):
        """Test meta report generation with nested _metrics in payload"""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result": {
                        "content": "response",
                        "_metrics": {
                            "model": "claude-3",
                            "tokens": 200,
                            "cost_usd": 0.004,
                            "latency_ms": 1000,
                        },
                    },
                },
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 200
        assert report["total_cost_usd"] == 0.004
        assert "claude-3" in report["model_usage"]

    def test_generate_meta_report_duplicate_metrics(self, metrics_collector):
        """Test meta report generation with duplicate metrics"""
        # Create identical metrics that should be deduplicated
        metrics_obj1 = {
            "model": "gpt-4",
            "tokens": 100,
            "prompt_tokens": 50,
            "completion_tokens": 50,
            "cost_usd": 0.002,
            "latency_ms": 1500,
        }

        # Create a second identical metrics object (same values)
        metrics_obj2 = {
            "model": "gpt-4",
            "tokens": 100,
            "prompt_tokens": 50,
            "completion_tokens": 50,
            "cost_usd": 0.002,
            "latency_ms": 1500,
        }

        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result1": {
                        "_metrics": metrics_obj1,
                    },
                    "result2": {
                        "_metrics": metrics_obj2,  # Identical metrics, should be deduplicated
                    },
                },
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        # Should only count once due to deduplication based on metrics values
        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 100
        assert report["total_cost_usd"] == 0.002

    def test_generate_meta_report_null_costs(self, metrics_collector):
        """Test meta report generation with null costs"""
        logs = [
            {
                "agent_id": "local_agent",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "local-llm",
                    "tokens": 100,
                    "cost_usd": None,  # Null cost
                    "latency_ms": 1500,
                },
            },
        ]

        with patch("orka.orchestrator.metrics.logger") as mock_logger:
            report = metrics_collector._generate_meta_report(logs)

            # Should log warning about null cost
            mock_logger.warning.assert_called_once()

        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 100
        assert report["total_cost_usd"] == 0.0  # Null costs excluded

    @patch.dict(os.environ, {"ORKA_LOCAL_COST_POLICY": "null_fail"})
    def test_generate_meta_report_null_costs_fail_policy(self, metrics_collector):
        """Test meta report generation with null costs and fail policy"""
        logs = [
            {
                "agent_id": "local_agent",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "local-llm",
                    "tokens": 100,
                    "cost_usd": None,
                    "latency_ms": 1500,
                },
            },
        ]

        with pytest.raises(ValueError, match="Pipeline failed due to null cost"):
            metrics_collector._generate_meta_report(logs)

    def test_generate_meta_report_no_metrics(self, metrics_collector):
        """Test meta report generation with logs containing no metrics"""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {"result": "simple result"},
            },
            {
                "agent_id": "agent2",
                "duration": 2.0,
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        assert report["total_duration"] == 3.0
        assert report["total_llm_calls"] == 0
        assert report["total_tokens"] == 0
        assert report["total_cost_usd"] == 0.0
        assert report["avg_latency_ms"] == 0.0
        assert len(report["agent_breakdown"]) == 0

    def test_generate_meta_report_zero_latency(self, metrics_collector):
        """Test meta report generation with zero latency metrics"""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.002,
                    "latency_ms": 0,  # Zero latency should be ignored
                },
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        assert report["avg_latency_ms"] == 0.0
        assert report["agent_breakdown"]["agent1"]["avg_latency_ms"] == 0.0

    def test_generate_meta_report_agent_breakdown(self, metrics_collector):
        """Test detailed agent breakdown in meta report"""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.002,
                    "latency_ms": 1000,
                },
            },
            {
                "agent_id": "agent1",  # Same agent, second call
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 50,
                    "cost_usd": 0.001,
                    "latency_ms": 2000,
                },
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        agent_stats = report["agent_breakdown"]["agent1"]
        assert agent_stats["calls"] == 2
        assert agent_stats["tokens"] == 150
        assert agent_stats["cost_usd"] == 0.003
        assert agent_stats["avg_latency_ms"] == 1500.0  # (1000 + 2000) / 2

    def test_build_previous_outputs_basic(self):
        """Test building previous outputs from logs"""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {
                    "result": "output1",
                },
            },
            {
                "agent_id": "agent2",
                "payload": {
                    "result": "output2",
                },
            },
        ]

        outputs = MetricsCollector.build_previous_outputs(logs)

        assert outputs["agent1"] == "output1"
        assert outputs["agent2"] == "output2"

    def test_build_previous_outputs_join_node(self):
        """Test building previous outputs with JoinNode merged results"""
        logs = [
            {
                "agent_id": "join_node",
                "payload": {
                    "result": {
                        "merged": {
                            "agent1": "output1",
                            "agent2": "output2",
                        },
                    },
                },
            },
        ]

        outputs = MetricsCollector.build_previous_outputs(logs)

        assert outputs["agent1"] == "output1"
        assert outputs["agent2"] == "output2"

    def test_build_previous_outputs_no_result(self):
        """Test building previous outputs from logs without results"""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {
                    "status": "completed",
                },
            },
            {
                "agent_id": "agent2",
            },
        ]

        outputs = MetricsCollector.build_previous_outputs(logs)

        assert len(outputs) == 0

    def test_build_previous_outputs_mixed(self):
        """Test building previous outputs with mixed log types"""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {
                    "result": "direct_output",
                },
            },
            {
                "agent_id": "join_node",
                "payload": {
                    "result": {
                        "merged": {
                            "agent2": "merged_output",
                            "agent3": "another_output",
                        },
                    },
                },
            },
            {
                "agent_id": "agent4",
                "payload": {
                    "status": "no_result",
                },
            },
        ]

        outputs = MetricsCollector.build_previous_outputs(logs)

        assert outputs["agent1"] == "direct_output"
        assert outputs["agent2"] == "merged_output"
        assert outputs["agent3"] == "another_output"
        assert "agent4" not in outputs

    def test_generate_meta_report_execution_stats(self, metrics_collector):
        """Test execution stats in meta report"""
        logs = [
            {"agent_id": "agent1", "duration": 1.0},
            {"agent_id": "agent2", "duration": 2.0},
        ]

        report = metrics_collector._generate_meta_report(logs)

        exec_stats = report["execution_stats"]
        assert exec_stats["total_agents_executed"] == 2
        assert exec_stats["run_id"] == "test-run-123"
        assert "generated_at" in exec_stats

    def test_generate_meta_report_deeply_nested_metrics(self, metrics_collector):
        """Test meta report with deeply nested _metrics"""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "level1": {
                        "level2": {
                            "level3": [
                                {
                                    "_metrics": {
                                        "model": "gpt-4",
                                        "tokens": 100,
                                        "cost_usd": 0.002,
                                        "latency_ms": 1500,
                                    },
                                },
                            ],
                        },
                    },
                },
            },
        ]

        report = metrics_collector._generate_meta_report(logs)

        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 100
        assert "gpt-4" in report["model_usage"]
