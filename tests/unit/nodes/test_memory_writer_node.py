"""Unit tests for orka.nodes.memory_writer_node."""

from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import pytest

from orka.nodes.memory_writer_node import MemoryWriterNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestMemoryWriterNode:
    """Test suite for MemoryWriterNode class."""

    def test_init(self):
        """Test MemoryWriterNode initialization."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            namespace="test_namespace"
        )
        
        assert node.node_id == "memory_writer"
        assert node.namespace == "test_namespace"

    def test_init_without_memory_logger(self):
        """Test MemoryWriterNode initialization without memory logger."""
        with patch('orka.nodes.memory_writer_node.create_memory_logger') as mock_create:
            mock_memory = Mock()
            mock_create.return_value = mock_memory
            
            node = MemoryWriterNode(
                node_id="memory_writer",
                prompt="Test prompt",
                queue=[],
                namespace="test"
            )
            
            # Verify create_memory_logger was called
            mock_create.assert_called_once()

    def test_init_with_decay_config(self):
        """Test initialization with decay config."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            decay_config={"default_long_term": True, "long_term_hours": 72.0}
        )
        
        assert node.decay_config["default_long_term"] is True
        assert node.decay_config["long_term_hours"] == 72.0

    def test_init_with_yaml_metadata(self):
        """Test initialization with YAML metadata."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            metadata={"source": "test", "category": "user_input"}
        )
        
        assert node.yaml_metadata == {"source": "test", "category": "user_input"}

    def test_init_with_key_template(self):
        """Test initialization with key template."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            key_template="user_{{ session_id }}_memory"
        )
        
        assert node.key_template == "user_{{ session_id }}_memory"

    @pytest.mark.asyncio
    async def test_run_impl(self):
        """Test _run_impl method."""
        mock_memory = Mock()
        mock_memory.log_memory = Mock(return_value="memory_key_123")
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            namespace="test"
        )
        
        context = {
            "input": "Test content to store",
            "formatted_prompt": "Test content to store"
        }
        
        result = await node._run_impl(context)
        
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "memory_key" in result
        assert mock_memory.log_memory.called

    @pytest.mark.asyncio
    async def test_run_impl_with_no_content(self):
        """Test _run_impl with no content."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {}
        
        result = await node._run_impl(context)
        
        assert result["status"] == "error"
        assert "No memory content" in result["error"]

    @pytest.mark.asyncio
    async def test_run_impl_with_key_template(self):
        """Test _run_impl with key template rendering."""
        mock_memory = Mock()
        mock_memory.log_memory = Mock(return_value="memory_key_456")
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            key_template="user_{{ session_id }}_{{ timestamp }}"
        )
        
        context = {
            "input": "Test content",
            "formatted_prompt": "Test content",
            "session_id": "test_session",
            "timestamp": "2025-01-01T00:00:00"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "success"
        assert "memory_key_template" in result["stored_metadata"]

    @pytest.mark.asyncio
    async def test_run_impl_with_key_template_error(self):
        """Test _run_impl with key template rendering error."""
        mock_memory = Mock()
        mock_memory.log_memory = Mock(return_value="memory_key_789")
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            key_template="user_{{ missing_var }}"
        )
        
        context = {
            "input": "Test content",
            "formatted_prompt": "Test content"
        }
        
        result = await node._run_impl(context)
        
        # Should handle error gracefully
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_run_impl_with_loop_context(self):
        """Test _run_impl with loop number in context."""
        mock_memory = Mock()
        mock_memory.log_memory = Mock(return_value="memory_key_loop")
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "input": {
                "input": "Test content",
                "loop_number": 5
            },
            "formatted_prompt": "Test content"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_run_impl_exception_handling(self):
        """Test _run_impl exception handling."""
        mock_memory = Mock()
        mock_memory.log_memory = Mock(side_effect=Exception("Storage error"))
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "input": "Test content",
            "formatted_prompt": "Test content"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "error"
        assert "Storage error" in result["error"]

    def test_merge_metadata(self):
        """Test _merge_metadata method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory,
            metadata={"source": "test"}
        )
        
        context = {
            "metadata": {"additional": "data"}
        }
        
        merged = node._merge_metadata(context)
        
        assert isinstance(merged, dict)
        assert "source" in merged
        assert merged["additional"] == "data"

    def test_merge_metadata_with_guardian(self):
        """Test _merge_metadata with guardian outputs."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            metadata={"source": "test"}
        )
        
        context = {
            "previous_outputs": {
                "true_validation_guardian": {
                    "result": {"validation_status": "valid"},
                    "metadata": {"confidence": 0.95}
                }
            }
        }
        
        merged = node._merge_metadata(context)
        
        assert "confidence" in merged
        assert merged["confidence"] == 0.95

    def test_merge_metadata_exception_handling(self):
        """Test _merge_metadata exception handling."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            metadata={"key": "value"}
        )
        
        # Invalid context that might cause errors
        context = {"metadata": None}
        
        merged = node._merge_metadata(context)
        
        # Should return yaml metadata as fallback
        assert isinstance(merged, dict)

    def test_render_metadata_templates(self):
        """Test _render_metadata_templates method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metadata = {
            "session": "{{ session_id }}",
            "timestamp": "{{ now() }}"
        }
        
        context = {
            "session_id": "test_session_123",
            "timestamp": "2025-01-01T00:00:00"
        }
        
        rendered = node._render_metadata_templates(metadata, context)
        
        assert rendered["session"] == "test_session_123"
        assert rendered["timestamp"] == "2025-01-01T00:00:00"

    def test_render_metadata_templates_with_nested_dict(self):
        """Test template rendering with nested dictionaries."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metadata = {
            "nested": {
                "key": "{{ input }}"
            }
        }
        
        context = {"input": "test_value"}
        
        rendered = node._render_metadata_templates(metadata, context)
        
        assert "nested" in rendered

    def test_render_metadata_templates_with_list(self):
        """Test template rendering with list values."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metadata = {
            "tags": ["{{ input }}", "static_tag"]
        }
        
        context = {"input": "dynamic_tag"}
        
        rendered = node._render_metadata_templates(metadata, context)
        
        assert "tags" in rendered

    def test_render_metadata_templates_with_empty_result(self):
        """Test template rendering with empty result."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metadata = {
            "optional": "{{ missing_var }}"
        }
        
        context = {}
        
        rendered = node._render_metadata_templates(metadata, context)
        
        # Should handle empty result gracefully
        assert "optional" in rendered

    def test_render_metadata_templates_with_default(self):
        """Test template rendering with default() function."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metadata = {
            "with_default": "{{ missing | default('fallback') }}"
        }
        
        context = {}
        
        rendered = node._render_metadata_templates(metadata, context)
        
        assert "with_default" in rendered

    def test_render_metadata_templates_exception(self):
        """Test template rendering exception handling."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        metadata = {
            "bad_template": "{{ invalid syntax }}"
        }
        
        context = {}
        
        rendered = node._render_metadata_templates(metadata, context)
        
        # Should fallback to original value
        assert isinstance(rendered, dict)

    def test_extract_guardian_metadata(self):
        """Test _extract_guardian_metadata method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "previous_outputs": {
                "true_validation_guardian": {
                    "result": {"validation_status": "valid"},
                    "metadata": {"confidence": 0.9}
                }
            }
        }
        
        guardian_meta = node._extract_guardian_metadata(context)
        
        assert "confidence" in guardian_meta
        assert guardian_meta["validation_guardian"] == "true_validation_guardian"

    def test_extract_guardian_metadata_false_guardian(self):
        """Test extracting metadata from false validation guardian."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "previous_outputs": {
                "false_validation_guardian": {
                    "result": {"validation_status": "invalid"},
                    "metadata": {"reason": "failed_check"}
                }
            }
        }
        
        guardian_meta = node._extract_guardian_metadata(context)
        
        assert "reason" in guardian_meta

    def test_extract_guardian_metadata_no_guardian(self):
        """Test extracting metadata when no guardian present."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {}
        
        guardian_meta = node._extract_guardian_metadata(context)
        
        assert guardian_meta == {}

    def test_extract_guardian_metadata_exception(self):
        """Test exception handling in guardian metadata extraction."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {"previous_outputs": None}
        
        guardian_meta = node._extract_guardian_metadata(context)
        
        assert guardian_meta == {}

    def test_extract_memory_object_metadata(self):
        """Test _extract_memory_object_metadata method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "previous_outputs": {
                "validator": {
                    "memory_object": {
                        "category": "fact",
                        "importance": "high"
                    }
                }
            }
        }
        
        memory_meta = node._extract_memory_object_metadata(context)
        
        assert isinstance(memory_meta, dict)

    def test_extract_memory_content(self):
        """Test _extract_memory_content method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "input": "Test content",
            "formatted_prompt": "Test content"
        }
        
        content = node._extract_memory_content(context)
        
        assert isinstance(content, str)
        assert len(content) > 0

    def test_extract_memory_content_from_formatted_prompt(self):
        """Test extracting content from formatted_prompt."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "formatted_prompt": "Formatted prompt content"
        }
        
        content = node._extract_memory_content(context)
        
        assert content == "Formatted prompt content"

    def test_extract_memory_content_from_memory_object(self):
        """Test extracting content from structured memory object."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "previous_outputs": {
                "validator": {
                    "memory_object": {
                        "content": "Memory object content"
                    }
                }
            }
        }
        
        content = node._extract_memory_content(context)
        
        assert isinstance(content, str)

    def test_extract_memory_content_empty(self):
        """Test extracting content when no content available."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {}
        
        content = node._extract_memory_content(context)
        
        assert content == ""

    def test_memory_object_to_text(self):
        """Test _memory_object_to_text conversion."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        memory_obj = {
            "content": "Test content",
            "category": "fact"
        }
        
        text = node._memory_object_to_text(memory_obj, "original input")
        
        assert isinstance(text, str)
        assert len(text) > 0

    def test_calculate_importance_score(self):
        """Test _calculate_importance_score method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        score = node._calculate_importance_score(
            "Test content",
            {"event_type": "write"}
        )
        
        assert 0.0 <= score <= 1.0

    def test_calculate_importance_score_with_metadata(self):
        """Test importance calculation with metadata."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        score = node._calculate_importance_score(
            "Important content",
            {"category": "critical", "priority": "high"}
        )
        
        assert 0.0 <= score <= 1.0

    def test_calculate_importance_score_long_content(self):
        """Test importance calculation with long content."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        long_content = "x" * 1000
        score = node._calculate_importance_score(long_content, {})
        
        assert 0.0 <= score <= 1.0

    def test_classify_memory_type(self):
        """Test _classify_memory_type method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        memory_type = node._classify_memory_type(
            {"event_type": "write"},
            0.8
        )
        
        assert memory_type in ["short_term", "long_term"]

    def test_classify_memory_type_high_importance(self):
        """Test classification with high importance and stored category."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        # High importance with category=stored becomes long_term
        memory_type = node._classify_memory_type({"category": "stored"}, 0.9)
        
        assert memory_type == "long_term"

    def test_classify_memory_type_low_importance(self):
        """Test classification with low importance."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        memory_type = node._classify_memory_type({}, 0.3)
        
        assert memory_type == "short_term"

    def test_classify_memory_type_with_default_long_term(self):
        """Test classification with default_long_term config."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            decay_config={"default_long_term": True}
        )
        
        # Even low importance becomes long_term with default_long_term
        memory_type = node._classify_memory_type({}, 0.3)
        
        assert memory_type == "long_term"

    def test_get_expiry_hours(self):
        """Test _get_expiry_hours method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test prompt",
            queue=[],
            memory_logger=mock_memory
        )
        
        hours = node._get_expiry_hours("long_term", 0.8)
        
        assert isinstance(hours, float)
        assert hours > 0

    def test_get_expiry_hours_short_term(self):
        """Test expiry calculation for short term memory."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        hours = node._get_expiry_hours("short_term", 0.3)
        
        assert isinstance(hours, float)
        assert hours > 0

    def test_get_expiry_hours_long_term(self):
        """Test expiry calculation for long term memory."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        hours = node._get_expiry_hours("long_term", 0.9)
        
        assert isinstance(hours, float)
        # Long term should have longer expiry
        assert hours >= 24.0

    def test_get_template_helper_functions(self):
        """Test _get_template_helper_functions method."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {
            "input": "test_input",
            "previous_outputs": {"agent1": "output1"}
        }
        
        helpers = node._get_template_helper_functions(context)
        
        assert isinstance(helpers, dict)
        assert "get_input" in helpers
        assert callable(helpers["get_input"])

    def test_template_helper_get_input(self):
        """Test get_input helper function."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {"input": "test_value"}
        helpers = node._get_template_helper_functions(context)
        
        result = helpers["get_input"]()
        assert result == "test_value"

    def test_template_helper_get_loop_number(self):
        """Test get_loop_number helper function."""
        mock_memory = Mock()
        
        node = MemoryWriterNode(
            node_id="memory_writer",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        context = {"input": {"loop_number": 5}}
        helpers = node._get_template_helper_functions(context)
        
        result = helpers["get_loop_number"]()
        assert result == 5


