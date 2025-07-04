"""Test Orchestrator Metrics Comprehensive."""

import os
import platform
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from orka.orchestrator.metrics import MetricsCollector


class TestMetricsCollector:
    """Test cases for MetricsCollector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector()
        self.collector.run_id = "test_run_123"

    def test_extract_llm_metrics_from_dict_result(self):
        """Test _extract_llm_metrics with dict result containing _metrics."""
        agent = MagicMock()
        result = {
            "content": "test response",
            "_metrics": {
                "model": "gpt-4",
                "tokens": 100,
                "cost_usd": 0.05,
            },
        }

        metrics = self.collector._extract_llm_metrics(agent, result)

        assert metrics == {
            "model": "gpt-4",
            "tokens": 100,
            "cost_usd": 0.05,
        }

    def test_extract_llm_metrics_from_agent_last_metrics(self):
        """Test _extract_llm_metrics from agent's _last_metrics."""
        agent = MagicMock()
        agent._last_metrics = {
            "model": "claude-3",
            "tokens": 200,
            "latency_ms": 500,
        }
        result = "simple string result"

        metrics = self.collector._extract_llm_metrics(agent, result)

        assert metrics == {
            "model": "claude-3",
            "tokens": 200,
            "latency_ms": 500,
        }

    def test_extract_llm_metrics_none_when_not_found(self):
        """Test _extract_llm_metrics returns None when no metrics found."""
        agent = MagicMock()
        # Remove _last_metrics attribute
        del agent._last_metrics
        result = "simple string result"

        metrics = self.collector._extract_llm_metrics(agent, result)

        assert metrics is None

    def test_extract_llm_metrics_none_when_agent_metrics_empty(self):
        """Test _extract_llm_metrics returns None when agent metrics are empty."""
        agent = MagicMock()
        agent._last_metrics = None
        result = {"content": "test"}  # No _metrics key

        metrics = self.collector._extract_llm_metrics(agent, result)

        assert metrics is None

    @patch("subprocess.check_output")
    @patch("os.path.exists")
    @patch("os.environ.get")
    def test_get_runtime_environment_full_info(self, mock_env_get, mock_exists, mock_subprocess):
        """Test _get_runtime_environment with all available info."""
        # Mock git subprocess
        mock_subprocess.return_value = b"abcd1234567890abcdef\n"

        # Mock Docker environment
        mock_exists.return_value = True
        mock_env_get.side_effect = lambda key, default=None: {
            "DOCKER_CONTAINER": "true",
            "DOCKER_IMAGE": "orka:latest",
        }.get(key, default)

        # Mock GPUtil module
        mock_gputil = MagicMock()
        mock_gpu = MagicMock()
        mock_gpu.name = "NVIDIA RTX 4090"
        mock_gputil.getGPUs.return_value = [mock_gpu]

        with patch.dict("sys.modules", {"GPUtil": mock_gputil}):
            result = self.collector._get_runtime_environment()

        assert result["platform"] == platform.platform()
        assert result["python_version"] == platform.python_version()
        assert result["git_sha"] == "abcd1234567890abcdef"[:12]
        assert result["docker_image"] == "orka:latest"
        assert result["gpu_type"] == "NVIDIA RTX 4090 (1 GPU)"
        assert result["pricing_version"] == "2025-01"
        assert "timestamp" in result

    @patch("subprocess.check_output")
    def test_get_runtime_environment_git_error(self, mock_subprocess):
        """Test _get_runtime_environment when git command fails."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        result = self.collector._get_runtime_environment()

        assert result["git_sha"] == "unknown"

    @patch("os.path.exists")
    @patch("os.environ.get")
    def test_get_runtime_environment_no_docker(self, mock_env_get, mock_exists):
        """Test _get_runtime_environment when not in Docker."""
        mock_exists.return_value = False
        mock_env_get.return_value = None

        result = self.collector._get_runtime_environment()

        assert result["docker_image"] is None

    def test_get_runtime_environment_no_gpu_available(self):
        """Test _get_runtime_environment when no GPUs available."""
        # Mock GPUtil module
        mock_gputil = MagicMock()
        mock_gputil.getGPUs.return_value = []

        with patch.dict("sys.modules", {"GPUtil": mock_gputil}):
            result = self.collector._get_runtime_environment()

        assert result["gpu_type"] == "none"

    def test_get_runtime_environment_multiple_gpus(self):
        """Test _get_runtime_environment with multiple GPUs."""
        # Mock GPUtil module
        mock_gputil = MagicMock()
        mock_gpu1 = MagicMock()
        mock_gpu1.name = "NVIDIA RTX 4090"
        mock_gpu2 = MagicMock()
        mock_gpu2.name = "NVIDIA RTX 4080"
        mock_gputil.getGPUs.return_value = [mock_gpu1, mock_gpu2]

        with patch.dict("sys.modules", {"GPUtil": mock_gputil}):
            result = self.collector._get_runtime_environment()

        assert result["gpu_type"] == "NVIDIA RTX 4090 (2 GPUs)"

    def test_get_runtime_environment_gpu_import_error(self):
        """Test _get_runtime_environment when GPUtil import fails."""
        with patch.dict("sys.modules", {"GPUtil": None}):
            result = self.collector._get_runtime_environment()

        assert result["gpu_type"] == "unknown"

    def test_generate_meta_report_basic(self):
        """Test _generate_meta_report with basic log entries."""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.5,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "prompt_tokens": 60,
                    "completion_tokens": 40,
                    "cost_usd": 0.05,
                    "latency_ms": 500,
                },
            },
            {
                "agent_id": "agent2",
                "duration": 2.0,
                "llm_metrics": {
                    "model": "gpt-3.5-turbo",
                    "tokens": 80,
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                    "cost_usd": 0.02,
                    "latency_ms": 300,
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        assert result["total_duration"] == 3.5
        assert result["total_llm_calls"] == 2
        assert result["total_tokens"] == 180
        assert result["total_cost_usd"] == 0.07
        assert result["avg_latency_ms"] == 400.0

        # Check agent breakdown
        assert "agent1" in result["agent_breakdown"]
        assert "agent2" in result["agent_breakdown"]
        assert result["agent_breakdown"]["agent1"]["calls"] == 1
        assert result["agent_breakdown"]["agent1"]["tokens"] == 100
        assert result["agent_breakdown"]["agent1"]["cost_usd"] == 0.05

        # Check model usage
        assert "gpt-4" in result["model_usage"]
        assert "gpt-3.5-turbo" in result["model_usage"]
        assert result["model_usage"]["gpt-4"]["calls"] == 1
        assert result["model_usage"]["gpt-4"]["tokens"] == 100

    def test_generate_meta_report_with_payload_metrics(self):
        """Test _generate_meta_report with metrics in payload."""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result": {
                        "content": "response",
                        "_metrics": {
                            "model": "claude-3",
                            "tokens": 150,
                            "cost_usd": 0.08,
                            "latency_ms": 600,
                        },
                    },
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        assert result["total_llm_calls"] == 1
        assert result["total_tokens"] == 150
        assert result["total_cost_usd"] == 0.08
        assert result["avg_latency_ms"] == 600.0

    def test_generate_meta_report_nested_metrics(self):
        """Test _generate_meta_report with deeply nested metrics."""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result": {
                        "steps": [
                            {
                                "step1": {
                                    "_metrics": {
                                        "model": "gpt-4",
                                        "tokens": 50,
                                        "cost_usd": 0.03,
                                        "latency_ms": 200,
                                    },
                                },
                            },
                            {
                                "step2": {
                                    "_metrics": {
                                        "model": "gpt-4",
                                        "tokens": 75,
                                        "cost_usd": 0.04,
                                        "latency_ms": 300,
                                    },
                                },
                            },
                        ],
                    },
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        assert result["total_llm_calls"] == 2
        assert result["total_tokens"] == 125
        assert result["total_cost_usd"] == 0.07
        assert result["avg_latency_ms"] == 250.0

    def test_generate_meta_report_duplicate_metrics_avoided(self):
        """Test _generate_meta_report avoids counting duplicate metrics."""
        # Same metrics object referenced multiple times
        metrics_obj = {
            "model": "gpt-4",
            "tokens": 100,
            "prompt_tokens": 60,
            "completion_tokens": 40,
            "cost_usd": 0.05,
            "latency_ms": 500,
        }

        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result": {
                        "response1": {"_metrics": metrics_obj},
                        "response2": {"_metrics": metrics_obj},  # Same object
                    },
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        # Should only count once due to deduplication
        assert result["total_llm_calls"] == 1
        assert result["total_tokens"] == 100
        assert result["total_cost_usd"] == 0.05

    def test_generate_meta_report_null_cost_handling(self):
        """Test _generate_meta_report handles null costs correctly."""
        logs = [
            {
                "agent_id": "local_agent",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "local-llama",
                    "tokens": 100,
                    "cost_usd": None,  # Null cost from local model
                    "latency_ms": 500,
                },
            },
            {
                "agent_id": "cloud_agent",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 80,
                    "cost_usd": 0.05,
                    "latency_ms": 300,
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        # Should only include non-null costs in total
        assert result["total_cost_usd"] == 0.05
        assert result["total_llm_calls"] == 2
        assert result["total_tokens"] == 180

        # Check agent breakdown doesn't include null cost
        assert result["agent_breakdown"]["local_agent"]["cost_usd"] == 0
        assert result["agent_breakdown"]["cloud_agent"]["cost_usd"] == 0.05

    def test_generate_meta_report_null_cost_fail_policy(self):
        """Test _generate_meta_report fails with null cost when policy set."""
        logs = [
            {
                "agent_id": "local_agent",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "local-llama",
                    "tokens": 100,
                    "cost_usd": None,
                    "latency_ms": 500,
                },
            },
        ]

        with patch.dict(os.environ, {"ORKA_LOCAL_COST_POLICY": "null_fail"}):
            with pytest.raises(ValueError, match="Pipeline failed due to null cost"):
                self.collector._generate_meta_report(logs)

    def test_generate_meta_report_no_metrics(self):
        """Test _generate_meta_report with logs containing no metrics."""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {"result": "simple result"},
            },
            {
                "agent_id": "agent2",
                "duration": 2.0,
                # No llm_metrics or payload with _metrics
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        assert result["total_duration"] == 3.0
        assert result["total_llm_calls"] == 0
        assert result["total_tokens"] == 0
        assert result["total_cost_usd"] == 0.0
        assert result["avg_latency_ms"] == 0.0
        assert result["agent_breakdown"] == {}
        assert result["model_usage"] == {}

    def test_generate_meta_report_zero_latency_ignored(self):
        """Test _generate_meta_report ignores zero latency values."""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.05,
                    "latency_ms": 0,  # Zero latency should be ignored
                },
            },
            {
                "agent_id": "agent2",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 80,
                    "cost_usd": 0.03,
                    "latency_ms": 400,
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        # Average should only consider non-zero latencies
        assert result["avg_latency_ms"] == 400.0

        # Agent with zero latency should have avg_latency_ms of 0
        assert result["agent_breakdown"]["agent1"]["avg_latency_ms"] == 0.0
        assert result["agent_breakdown"]["agent2"]["avg_latency_ms"] == 400.0

    def test_generate_meta_report_execution_stats(self):
        """Test _generate_meta_report includes execution stats."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        exec_stats = result["execution_stats"]
        assert exec_stats["total_agents_executed"] == 1
        assert exec_stats["run_id"] == "test_run_123"
        assert "generated_at" in exec_stats

    def test_build_previous_outputs_regular_agents(self):
        """Test build_previous_outputs with regular agent outputs."""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {"result": "response from agent1"},
            },
            {
                "agent_id": "agent2",
                "payload": {"result": {"content": "structured response"}},
            },
        ]

        result = MetricsCollector.build_previous_outputs(logs)

        assert result["agent1"] == "response from agent1"
        assert result["agent2"] == {"content": "structured response"}

    def test_build_previous_outputs_join_node(self):
        """Test build_previous_outputs with JoinNode merged outputs."""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {"result": "regular output"},
            },
            {
                "agent_id": "join_node",
                "payload": {
                    "result": {
                        "status": "done",
                        "merged": {
                            "parallel_agent1": "result1",
                            "parallel_agent2": "result2",
                        },
                    },
                },
            },
        ]

        result = MetricsCollector.build_previous_outputs(logs)

        assert result["agent1"] == "regular output"
        assert result["parallel_agent1"] == "result1"
        assert result["parallel_agent2"] == "result2"

    def test_build_previous_outputs_no_result(self):
        """Test build_previous_outputs with logs missing result."""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {"status": "processing"},  # No result key
            },
            {
                "agent_id": "agent2",
                # No payload
            },
        ]

        result = MetricsCollector.build_previous_outputs(logs)

        assert result == {}

    def test_build_previous_outputs_non_dict_merged(self):
        """Test build_previous_outputs with non-dict merged value."""
        logs = [
            {
                "agent_id": "join_node",
                "payload": {
                    "result": {
                        "status": "done",
                        "merged": "not a dict",  # Non-dict merged value
                    },
                },
            },
        ]

        result = MetricsCollector.build_previous_outputs(logs)

        # Should include the whole result since merged is not a dict
        expected_result = {
            "status": "done",
            "merged": "not a dict",
        }
        assert result["join_node"] == expected_result

    def test_build_previous_outputs_empty_logs(self):
        """Test build_previous_outputs with empty logs."""
        result = MetricsCollector.build_previous_outputs([])

        assert result == {}

    def test_generate_meta_report_unknown_model(self):
        """Test _generate_meta_report handles unknown model correctly."""
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    # No model specified
                    "tokens": 100,
                    "cost_usd": 0.05,
                    "latency_ms": 500,
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        # Should use "unknown" as model name
        assert "unknown" in result["model_usage"]
        assert result["model_usage"]["unknown"]["calls"] == 1

    def test_generate_meta_report_missing_agent_id(self):
        """Test _generate_meta_report handles missing agent_id."""
        logs = [
            {
                # No agent_id specified
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.05,
                },
            },
        ]

        with patch.object(self.collector, "_get_runtime_environment") as mock_env:
            mock_env.return_value = {"test": "env"}

            result = self.collector._generate_meta_report(logs)

        # Should use "unknown" as agent_id
        assert "unknown" in result["agent_breakdown"]
