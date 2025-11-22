"""
Unit tests for VintageMessageRenderer class.
"""

import json
import pytest
from orka.tui.message_renderer import (
    VintageMessageRenderer,
    render_agent_response,
    render_memory_content,
)


class TestVintageMessageRenderer:
    """Test suite for VintageMessageRenderer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = VintageMessageRenderer(theme="default")
    
    def test_initialization(self):
        """Test renderer initialization."""
        assert self.renderer.theme == "default"
        assert self.renderer.STATUS_ICONS["success"] == "✓"
        assert self.renderer.STATUS_ICONS["error"] == "✗"
    
    def test_get_status_icon(self):
        """Test status icon retrieval."""
        assert self.renderer._get_status_icon("success") == "✓"
        assert self.renderer._get_status_icon("error") == "✗"
        assert self.renderer._get_status_icon("pending") == "⋯"
        assert self.renderer._get_status_icon("running") == "▸"
        assert self.renderer._get_status_icon("unknown") == "?"
        assert self.renderer._get_status_icon("invalid") == "?"
    
    def test_format_status(self):
        """Test status formatting with colors."""
        result = self.renderer._format_status("success")
        assert "SUCCESS" in result
        assert "green" in result
        
        result = self.renderer._format_status("error")
        assert "ERROR" in result
        assert "red" in result
    
    def test_detect_content_type_json(self):
        """Test JSON content type detection."""
        json_content = '{"key": "value", "number": 123}'
        assert self.renderer._detect_content_type(json_content) == "json"
        
        json_array = '[1, 2, 3]'
        assert self.renderer._detect_content_type(json_array) == "json"
    
    def test_detect_content_type_markdown(self):
        """Test markdown content type detection."""
        markdown_content = "# Header\n\nSome text with [link](url)"
        assert self.renderer._detect_content_type(markdown_content) == "markdown"
        
        markdown_list = "* Item 1\n* Item 2"
        assert self.renderer._detect_content_type(markdown_list) == "markdown"
    
    def test_detect_content_type_yaml(self):
        """Test YAML content type detection."""
        yaml_content = "key: value\nother_key: other_value"
        assert self.renderer._detect_content_type(yaml_content) == "yaml"
    
    def test_detect_content_type_plain(self):
        """Test plain text detection."""
        plain_text = "This is just plain text without special formatting"
        assert self.renderer._detect_content_type(plain_text) == "plain"
    
    def test_render_json(self):
        """Test JSON rendering."""
        json_data = '{"name": "test", "value": 42}'
        result = self.renderer._render_json(json_data)
        assert "test" in result
        assert "42" in result
    
    def test_render_json_invalid(self):
        """Test JSON rendering with invalid JSON."""
        invalid_json = "{invalid json"
        result = self.renderer._render_json(invalid_json)
        assert "invalid json" in result
    
    def test_render_markdown(self):
        """Test markdown rendering."""
        markdown = "# Header\n**bold** text"
        result = self.renderer._render_markdown(markdown)
        assert "bold" in result
    
    def test_render_plain_text(self):
        """Test plain text rendering."""
        text = "Line 1\nLine 2\nLine 3"
        result = self.renderer._render_plain_text(text)
        assert ">" in result  # Should have prompt symbol
        assert "Line 1" in result
        assert "Line 2" in result
    
    def test_format_content_none(self):
        """Test content formatting with None."""
        result = self.renderer._format_content(None)
        assert "No content" in result
    
    def test_format_content_truncation(self):
        """Test content truncation for long content."""
        long_content = "x" * 3000
        result = self.renderer._format_content(long_content, max_content_length=2000)
        assert "truncated" in result.lower()
        assert len(result) < 2500  # Should be truncated
    
    def test_render_metadata_box(self):
        """Test metadata box rendering."""
        metadata = {
            "model": "gpt-4",
            "temperature": 0.7,
            "nested": {"key": "value"}
        }
        result = self.renderer._render_metadata_box(metadata)
        assert "┌" in result  # Box characters
        assert "└" in result
        assert "model" in result
        assert "gpt-4" in result
    
    def test_format_metadata(self):
        """Test metadata inline formatting."""
        metadata = {
            "key1": "value1",
            "key2": "value2"
        }
        result = self.renderer._format_metadata(metadata)
        assert "key1" in result
        assert "value1" in result
    
    def test_render_agent_response(self):
        """Test complete agent response rendering."""
        response = {
            "agent_id": "test_agent",
            "status": "success",
            "output": "Test output content",
            "metadata": {"model": "test-model"},
            "tokens_used": 100
        }
        
        result = self.renderer.render_agent_response(response)
        assert "test_agent" in result
        assert "✓" in result
        assert "SUCCESS" in result
        assert "Test output content" in result
        assert "100 tokens" in result
    
    def test_render_agent_response_minimal(self):
        """Test agent response with minimal data."""
        response = {
            "agent_id": "minimal_agent",
            "output": "Content"
        }
        
        result = self.renderer.render_agent_response(response)
        assert "minimal_agent" in result
        assert "Content" in result
    
    def test_render_memory_content(self):
        """Test memory content rendering."""
        memory_data = {
            "memory_key": "test_memory_key_12345",
            "content": "Test memory content",
            "metadata": {"category": "test"},
            "memory_type": "short_term",
            "node_id": "node_123",
            "importance_score": 0.85
        }
        
        result = self.renderer.render_memory_content(memory_data)
        assert "Memory:" in result
        assert "CONTENT:" in result
        assert "Test memory content" in result
        assert "METADATA:" in result
        assert "SYSTEM INFO:" in result
        assert "short_term" in result
    
    def test_render_memory_content_long_key(self):
        """Test memory rendering with truncated key."""
        long_key = "a" * 100
        memory_data = {
            "memory_key": long_key,
            "content": "Content",
            "metadata": {},
            "memory_type": "long_term"
        }
        
        result = self.renderer.render_memory_content(memory_data, show_full_key=False)
        assert "Memory:" in result
        # Should show truncated version
        assert len(result) < len(long_key) + 1000
    
    def test_render_memory_content_full_key(self):
        """Test memory rendering with full key."""
        long_key = "a" * 100
        memory_data = {
            "memory_key": long_key,
            "content": "Content",
            "metadata": {},
            "memory_type": "long_term"
        }
        
        result = self.renderer.render_memory_content(memory_data, show_full_key=True)
        assert long_key in result
    
    def test_convenience_function_render_agent_response(self):
        """Test convenience function for agent response."""
        response = {
            "agent_id": "test",
            "output": "output"
        }
        
        result = render_agent_response(response, theme="vintage")
        assert "test" in result
        assert "output" in result
    
    def test_convenience_function_render_memory_content(self):
        """Test convenience function for memory content."""
        memory_data = {
            "memory_key": "key",
            "content": "content",
            "metadata": {}
        }
        
        result = render_memory_content(memory_data, theme="dark")
        assert "key" in result
        assert "content" in result
    
    def test_render_json_with_special_characters(self):
        """Test JSON rendering with special characters."""
        json_data = '{"text": "Hello\\nWorld", "symbol": "™"}'
        result = self.renderer._render_json(json_data)
        assert "Hello" in result
        assert "World" in result
    
    def test_render_yaml_multiline(self):
        """Test YAML rendering with multiple lines."""
        yaml_content = "key1: value1\nkey2: value2\nkey3: value3"
        result = self.renderer._render_yaml(yaml_content)
        assert "key1" in result
        assert "key2" in result
        assert "value1" in result
    
    def test_theme_variants(self):
        """Test renderer with different themes."""
        themes = ["default", "vintage", "dark"]
        
        for theme in themes:
            renderer = VintageMessageRenderer(theme=theme)
            assert renderer.theme == theme
            
            response = {"agent_id": "test", "output": "test"}
            result = renderer.render_agent_response(response)
            assert "test" in result


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_response(self):
        """Test handling of empty response."""
        renderer = VintageMessageRenderer()
        response = {}
        
        result = renderer.render_agent_response(response)
        assert "Unknown" in result  # Default agent_id
    
    def test_none_metadata(self):
        """Test handling of None metadata."""
        renderer = VintageMessageRenderer()
        response = {
            "agent_id": "test",
            "output": "content",
            "metadata": None
        }
        
        result = renderer.render_agent_response(response)
        assert "test" in result
    
    def test_nested_metadata(self):
        """Test deeply nested metadata."""
        renderer = VintageMessageRenderer()
        metadata = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            }
        }
        
        result = renderer._render_metadata_box(metadata)
        assert "level1" in result
    
    def test_unicode_content(self):
        """Test Unicode characters in content."""
        renderer = VintageMessageRenderer()
        content = "Hello 世界 🌍"
        
        result = renderer._format_content(content)
        assert "Hello" in result
