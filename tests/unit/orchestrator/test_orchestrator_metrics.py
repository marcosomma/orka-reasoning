"""Unit tests for orka.orchestrator.metrics."""

import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest

from orka.orchestrator.metrics import MetricsCollector

# Mark all tests in this module for unit testing
pytestmark = [pytest.mark.unit]


class TestMetricsCollector:
    """Test suite for MetricsCollector class."""

    def create_collector(self):
        """Helper to create a MetricsCollector instance."""
        collector = MetricsCollector()
        collector.run_id = "test-run-123"
        return collector

    def test_extract_llm_metrics_from_result_dict(self):
        """Test _extract_llm_metrics extracts metrics from result dict."""
        collector = self.create_collector()
        
        result = {
            "_metrics": {
                "model": "gpt-4",
                "tokens": 100,
                "cost_usd": 0.01
            }
        }
        agent = Mock()
        
        metrics = collector._extract_llm_metrics(agent, result)
        
        assert metrics is not None
        assert metrics["model"] == "gpt-4"
        assert metrics["tokens"] == 100
        assert metrics["cost_usd"] == 0.01

    def test_extract_llm_metrics_from_agent_last_metrics(self):
        """Test _extract_llm_metrics extracts metrics from agent._last_metrics."""
        collector = self.create_collector()
        
        agent = Mock()
        agent._last_metrics = {
            "model": "gpt-3.5-turbo",
            "tokens": 50,
            "cost_usd": 0.005
        }
        result = {}
        
        metrics = collector._extract_llm_metrics(agent, result)
        
        assert metrics is not None
        assert metrics["model"] == "gpt-3.5-turbo"
        assert metrics["tokens"] == 50

    def test_extract_llm_metrics_no_metrics(self):
        """Test _extract_llm_metrics returns None when no metrics found."""
        collector = self.create_collector()
        
        agent = Mock()
        agent._last_metrics = None
        result = {}
        
        metrics = collector._extract_llm_metrics(agent, result)
        
        assert metrics is None

    def test_extract_llm_metrics_result_dict_priority(self):
        """Test _extract_llm_metrics prioritizes result dict over agent metrics."""
        collector = self.create_collector()
        
        agent = Mock()
        agent._last_metrics = {"model": "gpt-3.5-turbo", "tokens": 50}
        result = {
            "_metrics": {"model": "gpt-4", "tokens": 100}
        }
        
        metrics = collector._extract_llm_metrics(agent, result)
        
        # Should use result dict metrics
        assert metrics["model"] == "gpt-4"
        assert metrics["tokens"] == 100

    @patch('orka.orchestrator.metrics.platform')
    @patch('orka.orchestrator.metrics.subprocess')
    def test_get_runtime_environment(self, mock_subprocess, mock_platform):
        """Test _get_runtime_environment collects environment info."""
        collector = self.create_collector()
        
        mock_platform.platform.return_value = "Windows-10"
        mock_platform.python_version.return_value = "3.12.0"
        mock_subprocess.check_output.return_value = b"abc123def456"
        
        env_info = collector._get_runtime_environment()
        
        assert env_info["platform"] == "Windows-10"
        assert env_info["python_version"] == "3.12.0"
        assert env_info["git_sha"] == "abc123def456"
        assert "timestamp" in env_info
        assert env_info["pricing_version"] == "2025-01"

    @patch('orka.orchestrator.metrics.platform')
    @patch('orka.orchestrator.metrics.subprocess')
    def test_get_runtime_environment_git_failure(self, mock_subprocess, mock_platform):
        """Test _get_runtime_environment handles git command failure."""
        collector = self.create_collector()
        
        mock_platform.platform.return_value = "Linux"
        mock_platform.python_version.return_value = "3.11.0"
        mock_subprocess.check_output.side_effect = Exception("Git not found")
        
        env_info = collector._get_runtime_environment()
        
        assert env_info["git_sha"] == "unknown"
        assert env_info["platform"] == "Linux"

    @patch('orka.orchestrator.metrics.os.path.exists')
    @patch('orka.orchestrator.metrics.os.environ')
    def test_get_runtime_environment_docker_detection(self, mock_environ, mock_exists):
        """Test _get_runtime_environment detects Docker environment."""
        collector = self.create_collector()
        
        mock_exists.return_value = True  # /.dockerenv exists
        mock_environ.get.return_value = "my-docker-image:latest"
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            
            env_info = collector._get_runtime_environment()
            
            assert env_info["docker_image"] == "my-docker-image:latest"

    def test_get_runtime_environment_gpu_detection(self):
        """Test _get_runtime_environment detects GPU (structure verification)."""
        collector = self.create_collector()
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            
            env_info = collector._get_runtime_environment()
            
            # Just verify structure is correct - GPU detection depends on environment
            assert "gpu_type" in env_info
            assert isinstance(env_info["gpu_type"], str)

    def test_get_runtime_environment_multiple_gpus(self):
        """Test _get_runtime_environment structure (GPU detection varies by environment)."""
        collector = self.create_collector()
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            
            env_info = collector._get_runtime_environment()
            
            # Just verify structure is correct
            assert "gpu_type" in env_info
            assert isinstance(env_info["gpu_type"], str)

    def test_get_runtime_environment_no_gpu(self):
        """Test _get_runtime_environment when no GPU available (structure verification)."""
        collector = self.create_collector()
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess, \
             patch('orka.orchestrator.metrics.shutil.which') as mock_which:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            mock_which.return_value = None  # nvidia-smi not found
            
            env_info = collector._get_runtime_environment()
            
            assert "gpu_type" in env_info
            assert env_info["gpu_type"] == "none"

    def test_get_runtime_environment_gpu_detection_with_nvidia_smi(self):
        """Test _get_runtime_environment detects GPU using nvidia-smi."""
        collector = self.create_collector()
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess, \
             patch('orka.orchestrator.metrics.shutil.which') as mock_which:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            mock_which.return_value = "/usr/bin/nvidia-smi"  # nvidia-smi found
            
            # Mock nvidia-smi output
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "NVIDIA GeForce RTX 4090\n"
            mock_subprocess.run.return_value = mock_result
            
            env_info = collector._get_runtime_environment()
            
            assert "gpu_type" in env_info
            assert "NVIDIA GeForce RTX 4090" in env_info["gpu_type"]
            assert "1 GPU" in env_info["gpu_type"]

    def test_get_runtime_environment_multiple_gpus_nvidia_smi(self):
        """Test _get_runtime_environment detects multiple GPUs using nvidia-smi."""
        collector = self.create_collector()
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess, \
             patch('orka.orchestrator.metrics.shutil.which') as mock_which:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            mock_which.return_value = "/usr/bin/nvidia-smi"
            
            # Mock nvidia-smi output with multiple GPUs
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "NVIDIA GeForce RTX 4090\nNVIDIA GeForce RTX 4090\n"
            mock_subprocess.run.return_value = mock_result
            
            env_info = collector._get_runtime_environment()
            
            assert "gpu_type" in env_info
            assert "NVIDIA GeForce RTX 4090" in env_info["gpu_type"]
            assert "2 GPUs" in env_info["gpu_type"]

    def test_get_runtime_environment_nvidia_smi_error(self):
        """Test _get_runtime_environment handles nvidia-smi errors gracefully."""
        collector = self.create_collector()
        
        with patch('orka.orchestrator.metrics.platform') as mock_platform, \
             patch('orka.orchestrator.metrics.subprocess') as mock_subprocess, \
             patch('orka.orchestrator.metrics.shutil.which') as mock_which:
            mock_platform.platform.return_value = "Linux"
            mock_platform.python_version.return_value = "3.12.0"
            mock_subprocess.check_output.side_effect = Exception()
            mock_which.return_value = "/usr/bin/nvidia-smi"
            
            # Mock nvidia-smi error
            mock_result = Mock()
            mock_result.returncode = 1  # Error code
            mock_result.stdout = ""
            mock_subprocess.run.return_value = mock_result
            
            env_info = collector._get_runtime_environment()
            
            assert "gpu_type" in env_info
            assert env_info["gpu_type"] == "none"

    def test_generate_meta_report_empty_logs(self):
        """Test _generate_meta_report with empty logs."""
        collector = self.create_collector()
        
        logs = []
        
        report = collector._generate_meta_report(logs)
        
        assert report["total_duration"] == 0.0
        assert report["total_llm_calls"] == 0
        assert report["total_tokens"] == 0
        assert report["total_cost_usd"] == 0.0
        assert report["avg_latency_ms"] == 0
        assert report["execution_stats"]["total_agents_executed"] == 0
        assert report["execution_stats"]["run_id"] == "test-run-123"

    def test_generate_meta_report_with_llm_metrics(self):
        """Test _generate_meta_report aggregates LLM metrics."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.5,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.01,
                    "latency_ms": 500
                }
            },
            {
                "agent_id": "agent2",
                "duration": 2.0,
                "llm_metrics": {
                    "model": "gpt-3.5-turbo",
                    "tokens": 50,
                    "cost_usd": 0.005,
                    "latency_ms": 300
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert report["total_duration"] == 3.5
        assert report["total_llm_calls"] == 2
        assert report["total_tokens"] == 150
        assert report["total_cost_usd"] == 0.015
        assert report["avg_latency_ms"] == 400.0
        assert report["execution_stats"]["total_agents_executed"] == 2

    def test_generate_meta_report_with_nested_metrics(self):
        """Test _generate_meta_report extracts nested _metrics from payload."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result": "test",
                    "_metrics": {
                        "model": "gpt-4",
                        "tokens": 100,
                        "cost_usd": 0.01,
                        "latency_ms": 500
                    }
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 100

    def test_generate_meta_report_deduplicates_metrics(self):
        """Test _generate_meta_report deduplicates identical metrics."""
        collector = self.create_collector()
        
        # Same metrics object appears multiple times
        same_metrics = {
            "model": "gpt-4",
            "tokens": 100,
            "prompt_tokens": 50,
            "completion_tokens": 50,
            "latency_ms": 500,
            "cost_usd": 0.01
        }
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "result": {"_metrics": same_metrics},
                    "nested": {"_metrics": same_metrics}  # Duplicate
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        # Should only count once
        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 100

    def test_generate_meta_report_null_cost(self):
        """Test _generate_meta_report handles null cost."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "local-llm",
                    "tokens": 100,
                    "cost_usd": None,  # Null cost
                    "latency_ms": 500
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert report["total_cost_usd"] == 0.0  # Null costs excluded
        assert report["total_llm_calls"] == 1

    def test_generate_meta_report_null_cost_policy_fail(self):
        """Test _generate_meta_report raises error with null_fail policy."""
        collector = self.create_collector()
        
        with patch.dict(os.environ, {"ORKA_LOCAL_COST_POLICY": "null_fail"}):
            logs = [
                {
                    "agent_id": "agent1",
                    "duration": 1.0,
                    "llm_metrics": {
                        "model": "local-llm",
                        "tokens": 100,
                        "cost_usd": None,
                        "latency_ms": 500
                    }
                }
            ]
            
            with pytest.raises(ValueError, match="Pipeline failed due to null cost"):
                collector._generate_meta_report(logs)

    def test_generate_meta_report_per_agent_metrics(self):
        """Test _generate_meta_report tracks per-agent metrics."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.01,
                    "latency_ms": 500
                }
            },
            {
                "agent_id": "agent1",
                "duration": 1.5,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 50,
                    "cost_usd": 0.005,
                    "latency_ms": 300
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert "agent1" in report["agent_breakdown"]
        agent_metrics = report["agent_breakdown"]["agent1"]
        assert agent_metrics["calls"] == 2
        assert agent_metrics["tokens"] == 150
        assert agent_metrics["cost_usd"] == 0.015
        assert agent_metrics["avg_latency_ms"] == 400.0

    def test_generate_meta_report_per_model_usage(self):
        """Test _generate_meta_report tracks per-model usage."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.01,
                    "latency_ms": 500
                }
            },
            {
                "agent_id": "agent2",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-3.5-turbo",
                    "tokens": 50,
                    "cost_usd": 0.005,
                    "latency_ms": 300
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert "gpt-4" in report["model_usage"]
        assert "gpt-3.5-turbo" in report["model_usage"]
        assert report["model_usage"]["gpt-4"]["calls"] == 1
        assert report["model_usage"]["gpt-4"]["tokens"] == 100
        assert report["model_usage"]["gpt-3.5-turbo"]["calls"] == 1

    def test_generate_meta_report_zero_latency_excluded(self):
        """Test _generate_meta_report excludes zero latencies from average."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 100,
                    "cost_usd": 0.01,
                    "latency_ms": 0  # Zero latency
                }
            },
            {
                "agent_id": "agent2",
                "duration": 1.0,
                "llm_metrics": {
                    "model": "gpt-4",
                    "tokens": 50,
                    "cost_usd": 0.005,
                    "latency_ms": 500
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert report["avg_latency_ms"] == 500.0  # Only non-zero latency counted

    def test_generate_meta_report_runtime_environment(self):
        """Test _generate_meta_report includes runtime environment."""
        collector = self.create_collector()
        
        with patch.object(collector, '_get_runtime_environment') as mock_get_env:
            mock_get_env.return_value = {"platform": "Linux", "python_version": "3.12.0"}
            
            logs = []
            report = collector._generate_meta_report(logs)
            
            assert "runtime_environment" in report
            assert report["runtime_environment"]["platform"] == "Linux"

    def test_build_previous_outputs_regular_agent(self):
        """Test build_previous_outputs with regular agent output."""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {
                    "result": "output1"
                }
            }
        ]
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert outputs["agent1"] == "output1"

    def test_build_previous_outputs_join_node_merged(self):
        """Test build_previous_outputs with JoinNode merged dict."""
        logs = [
            {
                "agent_id": "join_agent",
                "payload": {
                    "result": {
                        "merged": {
                            "agent1": "output1",
                            "agent2": "output2"
                        }
                    }
                }
            }
        ]
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert outputs["agent1"] == "output1"
        assert outputs["agent2"] == "output2"
        assert outputs["join_agent"] == {"merged": {"agent1": "output1", "agent2": "output2"}}

    def test_build_previous_outputs_response_format(self):
        """Test build_previous_outputs with response format."""
        logs = [
            {
                "agent_id": "response_agent",
                "payload": {
                    "response": "Test response",
                    "confidence": "0.9",
                    "internal_reasoning": "Reasoning text",
                    "_metrics": {"tokens": 100},
                    "formatted_prompt": "Prompt text"
                }
            }
        ]
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert "response_agent" in outputs
        assert outputs["response_agent"]["response"] == "Test response"
        assert outputs["response_agent"]["confidence"] == "0.9"
        assert outputs["response_agent"]["internal_reasoning"] == "Reasoning text"
        assert outputs["response_agent"]["_metrics"] == {"tokens": 100}

    def test_build_previous_outputs_memory_format(self):
        """Test build_previous_outputs with memory format."""
        logs = [
            {
                "agent_id": "memory_agent",
                "payload": {
                    "memories": [{"key": "value"}],
                    "query": "test query",
                    "backend": "redis",
                    "search_type": "similarity",
                    "num_results": 5
                }
            }
        ]
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert "memory_agent" in outputs
        assert outputs["memory_agent"]["memories"] == [{"key": "value"}]
        assert outputs["memory_agent"]["query"] == "test query"
        assert outputs["memory_agent"]["backend"] == "redis"
        assert outputs["memory_agent"]["search_type"] == "similarity"
        assert outputs["memory_agent"]["num_results"] == 5

    def test_build_previous_outputs_multiple_agents(self):
        """Test build_previous_outputs with multiple agents."""
        logs = [
            {
                "agent_id": "agent1",
                "payload": {"result": "output1"}
            },
            {
                "agent_id": "agent2",
                "payload": {"result": "output2"}
            }
        ]
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert len(outputs) == 2
        assert outputs["agent1"] == "output1"
        assert outputs["agent2"] == "output2"

    def test_build_previous_outputs_empty_logs(self):
        """Test build_previous_outputs with empty logs."""
        logs = []
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert outputs == {}

    def test_build_previous_outputs_missing_payload(self):
        """Test build_previous_outputs handles missing payload."""
        logs = [
            {
                "agent_id": "agent1"
                # No payload
            }
        ]
        
        outputs = MetricsCollector.build_previous_outputs(logs)
        
        assert outputs == {}

    def test_generate_meta_report_deeply_nested_metrics(self):
        """Test _generate_meta_report finds metrics in deeply nested structures."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "level1": {
                        "level2": {
                            "level3": {
                                "_metrics": {
                                    "model": "gpt-4",
                                    "tokens": 100,
                                    "cost_usd": 0.01,
                                    "latency_ms": 500
                                }
                            }
                        }
                    }
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert report["total_llm_calls"] == 1
        assert report["total_tokens"] == 100

    def test_generate_meta_report_list_nested_metrics(self):
        """Test _generate_meta_report finds metrics in lists."""
        collector = self.create_collector()
        
        logs = [
            {
                "agent_id": "agent1",
                "duration": 1.0,
                "payload": {
                    "items": [
                        {"_metrics": {"model": "gpt-4", "tokens": 50, "cost_usd": 0.005, "latency_ms": 250}},
                        {"_metrics": {"model": "gpt-4", "tokens": 60, "cost_usd": 0.006, "latency_ms": 300}}  # Different values to avoid deduplication
                    ]
                }
            }
        ]
        
        report = collector._generate_meta_report(logs)
        
        assert report["total_llm_calls"] == 2
        assert report["total_tokens"] == 110
