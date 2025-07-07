"""
Tests for TUI DataManager metadata functionality.
"""

import json

from orka.tui.data_manager import DataManager


class TestDataManagerMetadata:
    """Test metadata extraction and formatting in DataManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.data_manager = DataManager()

    def test_get_metadata_with_dict(self):
        """Test metadata extraction from memory with dict metadata."""
        memory = {
            "metadata": {
                "key": "value",
                "nested": {"sub": "data"},
                "source": "test",
            },
        }

        result = self.data_manager._get_metadata(memory)

        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["nested"]["sub"] == "data"
        assert result["source"] == "test"

    def test_get_metadata_with_bytes(self):
        """Test metadata extraction from memory with bytes metadata."""
        metadata_dict = {"key": "value", "number": 42}
        metadata_bytes = json.dumps(metadata_dict).encode("utf-8")
        memory = {"metadata": metadata_bytes}

        result = self.data_manager._get_metadata(memory)

        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_get_metadata_with_invalid_bytes(self):
        """Test metadata extraction with invalid JSON bytes."""
        memory = {"metadata": b"invalid json"}

        result = self.data_manager._get_metadata(memory)

        assert result == {}

    def test_get_metadata_empty(self):
        """Test metadata extraction with empty metadata."""
        memory = {"metadata": {}}

        result = self.data_manager._get_metadata(memory)

        assert result == {}

    def test_get_metadata_missing(self):
        """Test metadata extraction with missing metadata field."""
        memory = {"content": "some content"}

        result = self.data_manager._get_metadata(memory)

        assert result == {}

    def test_format_metadata_for_display_empty(self):
        """Test metadata formatting with empty metadata."""
        memory = {"metadata": {}}

        result = self.data_manager._format_metadata_for_display(memory)

        assert result == "[dim]No metadata available[/dim]"

    def test_format_metadata_for_display_simple(self):
        """Test metadata formatting with simple key-value pairs."""
        memory = {
            "metadata": {
                "source": "test",
                "importance": 0.8,
                "category": "stored",
            },
        }

        result = self.data_manager._format_metadata_for_display(memory)

        assert "[cyan]source:[/cyan] test" in result
        assert "[cyan]importance:[/cyan] 0.8" in result
        assert "[cyan]category:[/cyan] stored" in result

    def test_format_metadata_for_display_nested(self):
        """Test metadata formatting with nested structures."""
        memory = {
            "metadata": {
                "simple": "value",
                "nested": {
                    "sub_key": "sub_value",
                    "another": "data",
                },
            },
        }

        result = self.data_manager._format_metadata_for_display(memory)

        assert "[cyan]simple:[/cyan] value" in result
        assert "[cyan]nested:[/cyan]" in result
        assert "  [dim]sub_key:[/dim] sub_value" in result
        assert "  [dim]another:[/dim] data" in result

    def test_format_metadata_for_display_with_bytes_values(self):
        """Test metadata formatting with bytes values."""
        memory = {
            "metadata": {
                "text_field": b"bytes value",
                "normal_field": "string value",
            },
        }

        result = self.data_manager._format_metadata_for_display(memory)

        assert "[cyan]text_field:[/cyan] bytes value" in result
        assert "[cyan]normal_field:[/cyan] string value" in result

    def test_format_metadata_for_display_missing_metadata(self):
        """Test metadata formatting with missing metadata field."""
        memory = {"content": "some content"}

        result = self.data_manager._format_metadata_for_display(memory)

        assert result == "[dim]No metadata available[/dim]"

    def test_format_metadata_for_display_complex_nested(self):
        """Test metadata formatting with complex nested structures."""
        memory = {
            "metadata": {
                "agent": "test_agent",
                "processing": {
                    "steps": ["step1", "step2"],
                    "timing": {
                        "start": "2024-01-01",
                        "end": "2024-01-02",
                    },
                },
                "score": 0.95,
            },
        }

        result = self.data_manager._format_metadata_for_display(memory)

        assert "[cyan]agent:[/cyan] test_agent" in result
        assert "[cyan]processing:[/cyan]" in result
        assert "  [dim]steps:[/dim] ['step1', 'step2']" in result
        assert "  [dim]timing:[/dim] {'start': '2024-01-01', 'end': '2024-01-02'}" in result
        assert "[cyan]score:[/cyan] 0.95" in result

    def test_format_metadata_for_display_with_none_values(self):
        """Test metadata formatting with None values."""
        memory = {
            "metadata": {
                "valid_field": "valid_value",
                "none_field": None,
                "empty_field": "",
            },
        }

        result = self.data_manager._format_metadata_for_display(memory)

        assert "[cyan]valid_field:[/cyan] valid_value" in result
        assert "[cyan]none_field:[/cyan] None" in result
        assert "[cyan]empty_field:[/cyan] " in result

    def test_get_metadata_with_json_exception(self):
        """Test metadata extraction handles JSON decoding exceptions gracefully."""
        # Create bytes that will cause JSON decoding to fail
        memory = {"metadata": b"\x80\x81\x82"}  # Invalid UTF-8 bytes

        result = self.data_manager._get_metadata(memory)

        assert result == {}

    def test_format_metadata_for_display_bytes_decoding_error(self):
        """Test metadata formatting handles bytes decoding errors gracefully."""
        memory = {
            "metadata": {
                "good_field": "value",
                "bad_bytes": b"\x80\x81\x82",  # Invalid UTF-8 bytes
            },
        }

        result = self.data_manager._format_metadata_for_display(memory)

        assert "[cyan]good_field:[/cyan] value" in result
        # Should handle the bad bytes gracefully and display something
        assert "[cyan]bad_bytes:[/cyan]" in result
