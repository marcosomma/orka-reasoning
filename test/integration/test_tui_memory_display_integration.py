"""
Integration tests for TUI memory display functionality.
"""


class TestTUIMemoryDisplayIntegration:
    """Integration tests for memory display in TUI."""

    def test_full_memory_selection_flow(self):
        """Test complete flow from memory data to display."""
        # Mock memory data with realistic structure
        memory_data = {
            "content": "This is test memory content",
            "metadata": {
                "source": "test_agent",
                "category": "stored",
                "importance_score": 0.85,
                "nested": {
                    "sub_field": "sub_value",
                },
            },
            "node_id": "test_node_123",
            "memory_type": "short_term",
            "importance_score": 0.85,
            "timestamp": 1641024000,
            "memory_key": "test_memory_key_abc123",
        }

        # Test DataManager metadata extraction
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Test metadata extraction
        metadata = data_manager._get_metadata(memory_data)
        assert metadata["source"] == "test_agent"
        assert metadata["nested"]["sub_field"] == "sub_value"

        # Test metadata formatting
        formatted = data_manager._format_metadata_for_display(memory_data)
        assert "[cyan]source:[/cyan] test_agent" in formatted
        assert "[cyan]nested:[/cyan]" in formatted
        assert "  [dim]sub_field:[/dim] sub_value" in formatted

    def test_bytes_metadata_handling(self):
        """Test handling of bytes metadata from Redis."""
        import json

        metadata_dict = {
            "source": "redis_test",
            "category": "stored",
            "score": 0.9,
        }
        memory_data = {
            "content": "Test content",
            "metadata": json.dumps(metadata_dict).encode("utf-8"),
        }

        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Test bytes metadata extraction
        metadata = data_manager._get_metadata(memory_data)
        assert isinstance(metadata, dict)
        assert metadata["source"] == "redis_test"
        assert metadata["score"] == 0.9

        # Test formatting
        formatted = data_manager._format_metadata_for_display(memory_data)
        assert "[cyan]source:[/cyan] redis_test" in formatted

    def test_empty_and_missing_metadata(self):
        """Test handling of empty or missing metadata."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Test empty metadata
        memory_empty = {"content": "test", "metadata": {}}
        formatted_empty = data_manager._format_metadata_for_display(memory_empty)
        assert formatted_empty == "[dim]No metadata available[/dim]"

        # Test missing metadata
        memory_missing = {"content": "test"}
        formatted_missing = data_manager._format_metadata_for_display(memory_missing)
        assert formatted_missing == "[dim]No metadata available[/dim]"

    def test_complex_nested_metadata_formatting(self):
        """Test complex nested metadata structures."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        memory_data = {
            "content": "Test content",
            "metadata": {
                "agent_info": {
                    "name": "TestAgent",
                    "version": "1.0.0",
                    "config": {
                        "max_tokens": 1000,
                        "temperature": 0.7,
                    },
                },
                "processing": {
                    "steps": ["validate", "process", "store"],
                    "duration": 1.23,
                },
                "tags": ["important", "test"],
                "score": 0.95,
            },
        }

        formatted = data_manager._format_metadata_for_display(memory_data)

        # Check top-level fields
        assert "[cyan]score:[/cyan] 0.95" in formatted
        assert "[cyan]tags:[/cyan] ['important', 'test']" in formatted

        # Check nested structures
        assert "[cyan]agent_info:[/cyan]" in formatted
        assert "  [dim]name:[/dim] TestAgent" in formatted
        assert "  [dim]version:[/dim] 1.0.0" in formatted
        assert "  [dim]config:[/dim] {'max_tokens': 1000, 'temperature': 0.7}" in formatted

        assert "[cyan]processing:[/cyan]" in formatted
        assert "  [dim]steps:[/dim] ['validate', 'process', 'store']" in formatted
        assert "  [dim]duration:[/dim] 1.23" in formatted

    def test_mixed_data_types_in_metadata(self):
        """Test metadata with mixed data types."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        memory_data = {
            "content": "Test content",
            "metadata": {
                "string_field": "text_value",
                "int_field": 42,
                "float_field": 3.14,
                "bool_field": True,
                "none_field": None,
                "bytes_field": b"bytes_value",
                "list_field": [1, 2, 3],
                "dict_field": {"key": "value"},
            },
        }

        formatted = data_manager._format_metadata_for_display(memory_data)

        # Check various data types are handled
        assert "[cyan]string_field:[/cyan] text_value" in formatted
        assert "[cyan]int_field:[/cyan] 42" in formatted
        assert "[cyan]float_field:[/cyan] 3.14" in formatted
        assert "[cyan]bool_field:[/cyan] True" in formatted
        assert "[cyan]none_field:[/cyan] None" in formatted
        assert "[cyan]bytes_field:[/cyan] bytes_value" in formatted
        assert "[cyan]list_field:[/cyan] [1, 2, 3]" in formatted
        assert "[cyan]dict_field:[/cyan]" in formatted
        assert "  [dim]key:[/dim] value" in formatted

    def test_error_handling_in_metadata_processing(self):
        """Test error handling in metadata processing."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Test with malformed JSON bytes
        memory_data = {
            "content": "Test content",
            "metadata": b"not valid json",
        }

        # Should not raise exception and return empty dict
        metadata = data_manager._get_metadata(memory_data)
        assert metadata == {}

        # Should display "No metadata available"
        formatted = data_manager._format_metadata_for_display(memory_data)
        assert formatted == "[dim]No metadata available[/dim]"

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in metadata."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        memory_data = {
            "content": "Test content with unicode: 🚀",
            "metadata": {
                "unicode_field": "Unicode text: 🌟 中文 العربية",
                "special_chars": "Special: !@#$%^&*()_+{}[]|\\:;\"'<>?,./",
                "emoji": "🎉🎊🎈",
            },
        }

        formatted = data_manager._format_metadata_for_display(memory_data)

        # Check unicode handling
        assert "[cyan]unicode_field:[/cyan] Unicode text: 🌟 中文 العربية" in formatted
        assert "[cyan]special_chars:[/cyan] Special: !@#$%^&*()_+{}[]|\\:;\"'<>?,./" in formatted
        assert "[cyan]emoji:[/cyan] 🎉🎊🎈" in formatted

    def test_large_metadata_handling(self):
        """Test handling of large metadata structures."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Create large metadata structure
        large_metadata = {}
        for i in range(50):
            large_metadata[f"field_{i}"] = f"value_{i}"

        # Add nested structure
        large_metadata["nested"] = {}
        for i in range(20):
            large_metadata["nested"][f"sub_field_{i}"] = f"sub_value_{i}"

        memory_data = {
            "content": "Test content",
            "metadata": large_metadata,
        }

        formatted = data_manager._format_metadata_for_display(memory_data)

        # Check that it handles large structures without crashing
        assert isinstance(formatted, str)
        assert len(formatted) > 100  # Should be substantial text

        # Check some expected fields are present
        assert "[cyan]field_0:[/cyan] value_0" in formatted
        assert "[cyan]field_10:[/cyan] value_10" in formatted
        assert "[cyan]nested:[/cyan]" in formatted
        assert "  [dim]sub_field_0:[/dim] sub_value_0" in formatted

    def test_edge_case_metadata_values(self):
        """Test edge cases in metadata values."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        memory_data = {
            "content": "Test content",
            "metadata": {
                "empty_string": "",
                "zero": 0,
                "false": False,
                "empty_list": [],
                "empty_dict": {},
                "whitespace": "   ",
                "newlines": "line1\nline2\nline3",
            },
        }

        formatted = data_manager._format_metadata_for_display(memory_data)

        # Check edge cases are handled
        assert "[cyan]empty_string:[/cyan] " in formatted
        assert "[cyan]zero:[/cyan] 0" in formatted
        assert "[cyan]false:[/cyan] False" in formatted
        assert "[cyan]empty_list:[/cyan] []" in formatted
        assert "[cyan]empty_dict:[/cyan]" in formatted
        assert "[cyan]whitespace:[/cyan]    " in formatted
        assert "[cyan]newlines:[/cyan] line1\nline2\nline3" in formatted

    def test_integration_with_real_redis_data_structure(self):
        """Test integration with realistic Redis data structure."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Simulate data as it would come from Redis
        redis_memory_data = {
            "content": b"This is content from Redis",
            "metadata": b'{"source": "redis_agent", "timestamp": 1641024000, "processing": {"steps": ["validate", "store"], "success": true}}',
            "node_id": b"node_redis_123",
            "memory_type": b"long_term",
            "importance_score": b"0.9",
            "memory_key": b"redis:memory:abc123def456",
        }

        # Test metadata extraction from bytes
        metadata = data_manager._get_metadata(redis_memory_data)
        assert metadata["source"] == "redis_agent"
        assert metadata["timestamp"] == 1641024000
        assert metadata["processing"]["success"] is True

        # Test formatting
        formatted = data_manager._format_metadata_for_display(redis_memory_data)
        assert "[cyan]source:[/cyan] redis_agent" in formatted
        assert "[cyan]processing:[/cyan]" in formatted
        assert "  [dim]steps:[/dim] ['validate', 'store']" in formatted
        assert "  [dim]success:[/dim] True" in formatted

    def test_very_large_metadata_scrollable_display(self):
        """Test that very large metadata is fully displayable and scrollable."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Create extremely large metadata structure
        very_large_metadata = {
            "description": "A" * 1000,  # Very long description
            "large_list": [f"item_{i}" for i in range(100)],  # Large list
            "nested_structure": {},
        }

        # Add many nested fields
        for i in range(50):
            very_large_metadata["nested_structure"][f"field_{i}"] = {
                "data": "B" * 100,
                "sub_data": [f"sub_{j}" for j in range(10)],
            }

        memory_data = {
            "content": "Test content with large metadata",
            "metadata": very_large_metadata,
        }

        # Test that all metadata is formatted without truncation
        formatted = data_manager._format_metadata_for_display(memory_data)

        # Verify large content is included
        assert "A" * 1000 in formatted  # Long description should be fully present
        assert "item_0" in formatted and "item_99" in formatted  # List items present
        assert "field_0" in formatted and "field_49" in formatted  # All nested fields present

        # Verify structure is maintained
        assert "[cyan]description:[/cyan]" in formatted
        assert "[cyan]large_list:[/cyan]" in formatted
        assert "[cyan]nested_structure:[/cyan]" in formatted

        # Verify no truncation occurred
        assert "..." not in formatted or "[dim]...[/dim]" not in formatted

        # The formatted output should be very large but complete
        assert len(formatted) > 5000  # Should be substantial
