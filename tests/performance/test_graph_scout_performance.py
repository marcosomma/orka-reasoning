"""
Performance tests for GraphScout agent to measure execution time, memory usage, and scalability.
"""

import asyncio
import time
import tracemalloc
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.nodes.graph_scout_agent import GraphScoutAgent, GraphScoutConfig


class TestGraphScoutPerformance:
    """Performance tests for GraphScout agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = GraphScoutConfig(
            k_beam=5,
            max_depth=3,
            commit_margin=0.15,
            cost_budget_tokens=1000,
            latency_budget_ms=2000,
            safety_threshold=0.8,
        )
        self.agent = GraphScoutAgent(
            node_id="perf_scout", prompt="Performance test prompt", queue=[], config=self.config
        )

    @pytest.mark.asyncio
    async def test_initialization_performance(self):
        """Test GraphScout initialization performance."""
        # Measure initialization time
        start_time = time.perf_counter()

        # Create multiple agents
        agents = []
        for i in range(100):
            agent = GraphScoutAgent(
                node_id=f"scout_{i}", prompt=f"Test prompt {i}", queue=[], config=self.config
            )
            agents.append(agent)

        end_time = time.perf_counter()
        initialization_time = end_time - start_time

        # Should initialize 100 agents in under 1 second
        assert (
            initialization_time < 1.0
        ), f"Initialization took {initialization_time:.3f}s, expected < 1.0s"
        assert len(agents) == 100

        print(f"✅ Initialized 100 GraphScout agents in {initialization_time:.3f}s")

    @pytest.mark.asyncio
    async def test_small_graph_performance(self):
        """Test performance with small graph (5-10 nodes)."""
        tracemalloc.start()
        start_time = time.perf_counter()

        # Mock orchestrator with small graph
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_graph_state.return_value = self._create_mock_graph_state(num_nodes=8)

        context = {
            "orchestrator": mock_orchestrator,
            "input": "What is the weather like today?",
            "formatted_prompt": "Weather query: What is the weather like today?",
        }

        with patch.multiple(
            self.agent,
            _extract_question=MagicMock(return_value="What is the weather like today?"),
        ):
            # Mock component behavior for performance test
            mock_introspector = AsyncMock()
            mock_introspector.discover_paths.return_value = self._create_mock_candidates(8)

            mock_evaluator = AsyncMock()
            mock_evaluator.simulate_candidates.return_value = (
                self._create_mock_evaluated_candidates(8)
            )

            mock_scorer = AsyncMock()
            mock_scorer.score_candidates.return_value = self._create_mock_scored_candidates(8)

            mock_decision_engine = AsyncMock()
            mock_decision_engine.make_decision.return_value = {
                "decision_type": "commit_next",
                "target": "agent_1",
                "confidence": 0.9,
                "reasoning": "High confidence selection",
            }

            # Set mocked components
            self.agent.graph_introspector = mock_introspector
            self.agent.smart_path_evaluator = mock_evaluator
            self.agent.path_scorer = mock_scorer
            self.agent.decision_engine = mock_decision_engine
            self.agent.budget_controller = AsyncMock()
            self.agent.safety_controller = AsyncMock()

            # Execute
            result = await self.agent.run(context)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Performance assertions
        assert (
            execution_time < 0.5
        ), f"Small graph execution took {execution_time:.3f}s, expected < 0.5s"
        assert (
            peak < 50 * 1024 * 1024
        ), f"Peak memory usage {peak / 1024 / 1024:.1f}MB, expected < 50MB"
        assert result is not None

        print(
            f"✅ Small graph (8 nodes) processed in {execution_time:.3f}s, peak memory: {peak / 1024 / 1024:.1f}MB"
        )

    @pytest.mark.asyncio
    async def test_medium_graph_performance(self):
        """Test performance with medium graph (50-100 nodes)."""
        tracemalloc.start()
        start_time = time.perf_counter()

        # Mock orchestrator with medium graph
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_graph_state.return_value = self._create_mock_graph_state(num_nodes=75)

        context = {
            "orchestrator": mock_orchestrator,
            "input": "Analyze this complex data and provide insights",
            "formatted_prompt": "Complex analysis: Analyze this complex data and provide insights",
        }

        with patch.multiple(
            self.agent,
            _extract_question=MagicMock(
                return_value="Analyze this complex data and provide insights"
            ),
        ):
            # Mock component behavior for performance test
            mock_introspector = AsyncMock()
            mock_introspector.discover_paths.return_value = self._create_mock_candidates(75)

            mock_evaluator = AsyncMock()
            mock_evaluator.simulate_candidates.return_value = (
                self._create_mock_evaluated_candidates(75)
            )

            mock_scorer = AsyncMock()
            mock_scorer.score_candidates.return_value = self._create_mock_scored_candidates(75)

            mock_decision_engine = AsyncMock()
            mock_decision_engine.make_decision.return_value = {
                "decision_type": "shortlist",
                "target": [
                    {"node_id": "agent_1", "path": ["agent_1"]},
                    {"node_id": "agent_2", "path": ["agent_2"]},
                    {"node_id": "agent_3", "path": ["agent_3"]},
                ],
                "confidence": 0.8,
                "reasoning": "Multiple viable paths identified",
            }

            # Set mocked components
            self.agent.graph_introspector = mock_introspector
            self.agent.smart_path_evaluator = mock_evaluator
            self.agent.path_scorer = mock_scorer
            self.agent.decision_engine = mock_decision_engine
            self.agent.budget_controller = AsyncMock()
            self.agent.safety_controller = AsyncMock()

            # Execute
            result = await self.agent.run(context)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Performance assertions
        assert (
            execution_time < 2.0
        ), f"Medium graph execution took {execution_time:.3f}s, expected < 2.0s"
        assert (
            peak < 200 * 1024 * 1024
        ), f"Peak memory usage {peak / 1024 / 1024:.1f}MB, expected < 200MB"
        assert result is not None

        print(
            f"✅ Medium graph (75 nodes) processed in {execution_time:.3f}s, peak memory: {peak / 1024 / 1024:.1f}MB"
        )

    @pytest.mark.asyncio
    async def test_large_graph_performance(self):
        """Test performance with large graph (200+ nodes)."""
        tracemalloc.start()
        start_time = time.perf_counter()

        # Mock orchestrator with large graph
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_graph_state.return_value = self._create_mock_graph_state(
            num_nodes=250
        )

        context = {
            "orchestrator": mock_orchestrator,
            "input": "Process this enterprise-scale workflow with multiple dependencies",
            "formatted_prompt": "Enterprise workflow: Process this enterprise-scale workflow with multiple dependencies",
        }

        with patch.multiple(
            self.agent,
            _extract_question=MagicMock(
                return_value="Process this enterprise-scale workflow with multiple dependencies"
            ),
        ):
            # Mock component behavior for performance test
            mock_introspector = AsyncMock()
            mock_introspector.discover_paths.return_value = self._create_mock_candidates(250)

            mock_evaluator = AsyncMock()
            mock_evaluator.simulate_candidates.return_value = (
                self._create_mock_evaluated_candidates(250)
            )

            mock_scorer = AsyncMock()
            mock_scorer.score_candidates.return_value = self._create_mock_scored_candidates(250)

            mock_decision_engine = AsyncMock()
            mock_decision_engine.make_decision.return_value = {
                "decision_type": "commit_path",
                "target": ["agent_1", "agent_5", "agent_12", "response_builder"],
                "confidence": 0.85,
                "reasoning": "Optimal multi-hop path identified",
            }

            # Set mocked components
            self.agent.graph_introspector = mock_introspector
            self.agent.smart_path_evaluator = mock_evaluator
            self.agent.path_scorer = mock_scorer
            self.agent.decision_engine = mock_decision_engine
            self.agent.budget_controller = AsyncMock()
            self.agent.safety_controller = AsyncMock()

            # Execute
            result = await self.agent.run(context)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Performance assertions
        assert (
            execution_time < 5.0
        ), f"Large graph execution took {execution_time:.3f}s, expected < 5.0s"
        assert (
            peak < 500 * 1024 * 1024
        ), f"Peak memory usage {peak / 1024 / 1024:.1f}MB, expected < 500MB"
        assert result is not None

        print(
            f"✅ Large graph (250 nodes) processed in {execution_time:.3f}s, peak memory: {peak / 1024 / 1024:.1f}MB"
        )

    @pytest.mark.asyncio
    async def test_concurrent_execution_performance(self):
        """Test performance with concurrent GraphScout executions."""
        start_time = time.perf_counter()

        # Create multiple agents
        agents = []
        for i in range(10):
            agent = GraphScoutAgent(
                node_id=f"concurrent_scout_{i}",
                prompt=f"Concurrent test prompt {i}",
                queue=[],
                config=self.config,
            )
            agents.append(agent)

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_graph_state.return_value = self._create_mock_graph_state(num_nodes=20)

        # Create concurrent tasks
        tasks = []
        for i, agent in enumerate(agents):
            context = {
                "orchestrator": mock_orchestrator,
                "input": f"Concurrent query {i}",
                "formatted_prompt": f"Concurrent: Concurrent query {i}",
            }

            with patch.multiple(
                agent,
                _extract_question=MagicMock(return_value=f"Concurrent query {i}"),
            ):
                # Mock components for each agent
                agent.graph_introspector = AsyncMock()
                agent.graph_introspector.discover_paths.return_value = self._create_mock_candidates(
                    20
                )

                agent.smart_path_evaluator = AsyncMock()
                agent.smart_path_evaluator.simulate_candidates.return_value = (
                    self._create_mock_evaluated_candidates(20)
                )

                agent.path_scorer = AsyncMock()
                agent.path_scorer.score_candidates.return_value = (
                    self._create_mock_scored_candidates(20)
                )

                agent.decision_engine = AsyncMock()
                agent.decision_engine.make_decision.return_value = {
                    "decision_type": "commit_next",
                    "target": f"agent_{i}",
                    "confidence": 0.9,
                    "reasoning": f"Selected for concurrent task {i}",
                }

                agent.budget_controller = AsyncMock()
                agent.safety_controller = AsyncMock()

                task = agent.run(context)
                tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Performance assertions
        assert (
            execution_time < 3.0
        ), f"Concurrent execution took {execution_time:.3f}s, expected < 3.0s"
        assert len(results) == 10
        assert all(result is not None for result in results)

        print(f"✅ 10 concurrent GraphScout executions completed in {execution_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency during repeated executions."""
        tracemalloc.start()

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_graph_state.return_value = self._create_mock_graph_state(num_nodes=50)

        memory_measurements = []

        # Run multiple iterations
        for i in range(20):
            context = {
                "orchestrator": mock_orchestrator,
                "input": f"Memory test query {i}",
                "formatted_prompt": f"Memory test: Memory test query {i}",
            }

            with patch.multiple(
                self.agent,
                _extract_question=MagicMock(return_value=f"Memory test query {i}"),
            ):
                # Mock components
                self.agent.graph_introspector = AsyncMock()
                self.agent.graph_introspector.discover_paths.return_value = (
                    self._create_mock_candidates(50)
                )

                self.agent.smart_path_evaluator = AsyncMock()
                self.agent.smart_path_evaluator.simulate_candidates.return_value = (
                    self._create_mock_evaluated_candidates(50)
                )

                self.agent.path_scorer = AsyncMock()
                self.agent.path_scorer.score_candidates.return_value = (
                    self._create_mock_scored_candidates(50)
                )

                self.agent.decision_engine = AsyncMock()
                self.agent.decision_engine.make_decision.return_value = {
                    "decision_type": "commit_next",
                    "target": f"agent_{i % 5}",
                    "confidence": 0.9,
                    "reasoning": f"Memory test iteration {i}",
                }

                self.agent.budget_controller = AsyncMock()
                self.agent.safety_controller = AsyncMock()

                # Execute
                result = await self.agent.run(context)
                assert result is not None

                # Measure memory
                current, peak = tracemalloc.get_traced_memory()
                memory_measurements.append(current)

        tracemalloc.stop()

        # Check for memory leaks (memory should not grow significantly)
        initial_memory = memory_measurements[0]
        final_memory = memory_measurements[-1]
        memory_growth = final_memory - initial_memory

        # Memory growth should be less than 50MB over 20 iterations
        assert (
            memory_growth < 50 * 1024 * 1024
        ), f"Memory grew by {memory_growth / 1024 / 1024:.1f}MB, expected < 50MB"

        print(
            f"✅ Memory efficiency test: grew by {memory_growth / 1024 / 1024:.1f}MB over 20 iterations"
        )

    def _create_mock_graph_state(self, num_nodes: int) -> MagicMock:
        """Create a mock graph state with specified number of nodes."""
        mock_graph_state = MagicMock()
        mock_graph_state.nodes = {f"agent_{i}": MagicMock() for i in range(num_nodes)}
        mock_graph_state.edges = {
            f"agent_{i}": [f"agent_{(i+1) % num_nodes}", f"agent_{(i+2) % num_nodes}"]
            for i in range(num_nodes)
        }
        mock_graph_state.current_node = "perf_scout"
        return mock_graph_state

    def _create_mock_candidates(self, num_candidates: int) -> List[Dict[str, Any]]:
        """Create mock candidates for testing."""
        return [
            {
                "node_id": f"agent_{i}",
                "path": [f"agent_{i}"],
                "depth": 1,
                "feasible": True,
                "constraints_met": True,
            }
            for i in range(min(num_candidates, 50))  # Limit to reasonable number
        ]

    def _create_mock_evaluated_candidates(self, num_candidates: int) -> List[Dict[str, Any]]:
        """Create mock evaluated candidates."""
        candidates = self._create_mock_candidates(num_candidates)
        for i, candidate in enumerate(candidates):
            candidate.update(
                {
                    "estimated_cost": 0.01 + (i * 0.001),
                    "estimated_latency": 100 + (i * 10),
                    "llm_evaluation": {
                        "final_scores": {
                            "relevance": 0.8 + (i * 0.01),
                            "efficiency": 0.7 + (i * 0.01),
                            "confidence": 0.9 - (i * 0.01),
                        }
                    },
                }
            )
        return candidates

    def _create_mock_scored_candidates(self, num_candidates: int) -> List[Dict[str, Any]]:
        """Create mock scored candidates."""
        candidates = self._create_mock_evaluated_candidates(num_candidates)
        for i, candidate in enumerate(candidates):
            candidate.update(
                {
                    "score": 0.8 - (i * 0.01),
                    "confidence": 0.9 - (i * 0.01),
                    "components": {"llm": 0.8 - (i * 0.01), "heuristics": 0.7 - (i * 0.01)},
                }
            )
        # Sort by score descending
        return sorted(candidates, key=lambda x: x["score"], reverse=True)


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
