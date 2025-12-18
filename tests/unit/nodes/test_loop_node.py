"""Unit tests for orka.nodes.loop_node."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.nodes.loop_node import LoopNode, PastLoopMetadata

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestLoopNode:
    """Test suite for LoopNode class."""

    def test_init(self):
        """Test LoopNode initialization."""
        mock_memory = Mock()
        
        node = LoopNode(
            node_id="loop_node",
            memory_logger=mock_memory,
            max_loops=5,
            score_threshold=0.8
        )
        
        assert node.node_id == "loop_node"
        assert node.max_loops == 5
        assert node.score_threshold == 0.8

    def test_init_without_memory_logger(self):
        """Test LoopNode initialization without memory logger."""
        node = LoopNode(
            node_id="loop_node",
            max_loops=3
        )
        
        assert node.memory_logger is None

    @pytest.mark.asyncio
    async def test_run_impl(self):
        """Test _run_impl method."""
        mock_memory = Mock()
        
        node = LoopNode(
            node_id="loop_node",
            memory_logger=mock_memory,
            max_loops=2,
            score_threshold=0.9
        )
        
        with patch.object(node, '_execute_internal_workflow') as mock_execute, \
             patch.object(node, '_extract_score') as mock_extract:
            
            mock_execute.return_value = {"result": "test", "score": 0.95}
            mock_extract.return_value = 0.95
            
            context = {
                "input": "test input",
                "formatted_prompt": "test input"
            }
            
            result = await node._run_impl(context)
            
            assert isinstance(result, dict)

    def test_is_valid_value(self):
        """Test _is_valid_value method."""
        mock_memory = Mock()
        node = LoopNode(node_id="loop_node", memory_logger=mock_memory)
        
        assert node._is_valid_value("0.8") is True
        assert node._is_valid_value(123) is True
        assert node._is_valid_value(0.5) is True
        assert node._is_valid_value(None) is False
        assert node._is_valid_value([]) is False
        assert node._is_valid_value("test") is False

    def test_try_boolean_scoring(self):
        """Test _try_boolean_scoring method."""
        mock_memory = Mock()
        
        with patch('orka.nodes.loop_node.BooleanScoreCalculator') as mock_calc:
            mock_calc_instance = Mock()
            mock_calc_instance.calculate.return_value = {"score": 0.85, "passed_count": 2, "total_criteria": 2}
            mock_calc.return_value = mock_calc_instance

            node = LoopNode(
                node_id="loop_node",
                memory_logger=mock_memory,
                scoring={"preset": "moderate"}
            )
            
            result = {
                "some_agent": {
                    "boolean_evaluations": {
                        "completeness": {"has_all_required_steps": True},
                        "coherence": {"logical_agent_sequence": True}
                    }
                }
            }
            
            score = node._try_boolean_scoring(result)
            
            assert score == 0.85

        def test_try_boolean_scoring_ignores_sparse_evals(self):
            """Sparse boolean_evaluations (too few criteria) should be ignored."""
            mock_memory = Mock()

            node = LoopNode(
                node_id="loop_node",
                memory_logger=mock_memory,
                scoring={"preset": "moderate"}
            )

            # Provide only two criteria out of many expected -> should be ignored
            result = {
                "agreement_moderator": {
                    "boolean_evaluations": {
                        "completeness": {"has_all_required_steps": True},
                        "efficiency": {"minimizes_redundant_calls": True},
                    }
                }
            }

            score = node._try_boolean_scoring(result)

            assert score is None

    def test_is_valid_boolean_structure(self):
        """Test _is_valid_boolean_structure method."""
        mock_memory = Mock()
        node = LoopNode(node_id="loop_node", memory_logger=mock_memory)
        
        valid_structure = {
            "completeness": {"has_all_required_steps": True},
            "coherence": {"logical_sequence": True}
        }
        assert node._is_valid_boolean_structure(valid_structure) is True
        
        invalid_structure_1 = {"not_scoring": {}}
        assert node._is_valid_boolean_structure(invalid_structure_1) is False

        invalid_structure_2 = {
            "completeness": {"has_all_required_steps": True}
        }
        assert node._is_valid_boolean_structure(invalid_structure_2) is False

    def test_extract_boolean_from_text(self):
        """Test _extract_boolean_from_text method."""
        mock_memory = Mock()
        node = LoopNode(node_id="loop_node", memory_logger=mock_memory)
        
        text = """
        scoring:
          completeness:
            has_all_required_steps: true
        """
        
        result = node._extract_boolean_from_text(text)
        
        assert isinstance(result, dict) or result is None

    @pytest.mark.asyncio
    async def test_extract_score(self):
        """Test _extract_score method."""
        mock_memory = Mock()
        node = LoopNode(
            node_id="loop_node",
            memory_logger=mock_memory,
            score_extraction_config={
                "strategies": [
                    {"type": "direct_key", "key": "score"}
                ]
            }
        )
        
        result = {"score": 0.85}
        score = await node._extract_score(result)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_extract_direct_key(self):
        """Test _extract_direct_key method."""
        mock_memory = Mock()
        node = LoopNode(node_id="loop_node", memory_logger=mock_memory)
        
        result = {"score": 0.85, "nested": {"value": 0.9}}
        
        score1 = node._extract_direct_key(result, "score")
        assert score1 == 0.85
        
        score2 = node._extract_direct_key(result, "nonexistent")
        assert score2 is None

    def test_extract_nested_path(self):
        """Test _extract_nested_path method."""
        mock_memory = Mock()
        node = LoopNode(node_id="loop_node", memory_logger=mock_memory)
        
        result = {
            "level1": {
                "level2": {
                    "value": 0.85
                }
            }
        }
        
        score = node._extract_nested_path(result, "level1.level2.value")
        assert score == 0.85
        
        score2 = node._extract_nested_path(result, "level1.nonexistent")
        assert score2 is None

    def test_extract_pattern(self):
        """Test _extract_pattern method."""
        mock_memory = Mock()
        node = LoopNode(node_id="loop_node", memory_logger=mock_memory)
        
        result = {
            "output": "The quality score is 0.85",
            "text": "Score: 0.9"
        }
        
        patterns = [
            r"quality score is ([0-9.]+)",
            r"Score:\s*([0-9.]+)"
        ]
        
        score = node._extract_pattern(result, patterns)
        assert score is not None
        assert isinstance(score, float)

